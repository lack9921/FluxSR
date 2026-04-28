"""Background scheduler that picks up queued tasks and runs them."""

import asyncio
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from typing import Optional

from .database import Database
from .models import Task

logger = logging.getLogger("fluxsr.task_queue.scheduler")

POLL_INTERVAL = 5  # seconds


def _generate_experiment_name(task: Task) -> str:
    """Generate a unique experiment name with timestamp."""
    now = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    base = task.name or os.path.splitext(os.path.basename(task.config_path))[0]
    return f"{base}_{now}"


def _build_command(task: Task) -> list[str]:
    """Build the CLI command for a training task."""
    train_script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "train.py",
    )
    cmd = [sys.executable, train_script, "-opt", task.config_path]

    # Parse override_args into --override key=value pairs
    if task.override_args:
        args_list = _parse_override_args(task.override_args)
        cmd.extend(args_list)

    # Add auto-generated experiment name via --override
    # (train.py doesn't have a --name arg; we override the config via --override)
    if "--name" not in task.override_args and "name" not in task.override_args:
        exp_name = _generate_experiment_name(task)
        cmd.append(f"--override=name={exp_name}")

    return cmd


def _parse_override_args(raw: str) -> list[str]:
    """Parse override_args string into --override key=value tokens.

    Supports:
      --batch_size 16         → --override batch_size=16
      --lr 2e-4               → --override lr=2e-4
      --auto_resume           → --auto_resume  (passthrough for known bool flags)
    """
    # Known boolean flags passed through directly
    bool_flags = {"--auto_resume", "--debug"}

    tokens = raw.split()
    result = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in bool_flags:
            result.append(token)
            i += 1
        elif token.startswith("--"):
            flag_name = token[2:]
            if i + 1 < len(tokens) and not tokens[i + 1].startswith("--"):
                # --flag value
                value = tokens[i + 1]
                result.append(f"--override={flag_name}={value}")
                i += 2
            else:
                # --flag  (boolean, passthrough)
                result.append(token)
                i += 1
        else:
            i += 1

    return result


class Scheduler:
    """Async scheduler that monitors the queue and launches training tasks."""

    def __init__(self, db: Database, project_root: str):
        self._db = db
        self._project_root = project_root
        self._running: Optional[asyncio.subprocess.Process] = None
        self._current_task_id: Optional[str] = None
        self._stop_event = asyncio.Event()
        self._task = None  # asyncio.Task

    async def start(self):
        logger.info("Scheduler started (poll interval=%ds)", POLL_INTERVAL)
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        logger.info("Scheduler stopping...")
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._running:
            self._running.terminate()
            try:
                await self._running.wait()
            except Exception:
                pass
            logger.info("Running task terminated")

    @property
    def current_task_id(self) -> Optional[str]:
        return self._current_task_id

    async def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                await self._tick()
            except Exception:
                logger.exception("Scheduler tick error")
            await asyncio.sleep(POLL_INTERVAL)

    async def _tick(self):
        # If a task is running, check if it's done
        if self._running:
            returncode = self._running.returncode
            if returncode is not None:
                # Task finished
                task_id = self._current_task_id
                if returncode == 0:
                    self._db.update_task(
                        task_id,
                        status="completed",
                        finished_at=datetime.now(timezone.utc).isoformat(),
                        exit_code=returncode,
                    )
                    logger.info("Task %s completed successfully", task_id)
                else:
                    # Try to read stderr for error message
                    error_msg = None
                    try:
                        stdout, stderr = await self._running.communicate()
                        if stderr:
                            error_msg = stderr.decode("utf-8", errors="replace")[-500:]
                    except Exception:
                        pass
                    self._db.update_task(
                        task_id,
                        status="failed",
                        finished_at=datetime.now(timezone.utc).isoformat(),
                        exit_code=returncode,
                        error_msg=error_msg or f"Exit code: {returncode}",
                    )
                    logger.warning("Task %s failed with code %d", task_id, returncode)

                self._running = None
                self._current_task_id = None
            return

        # No running task - pick next queued
        task = self._db.next_queued()
        if task is None:
            return

        # Launch task
        cwd = self._project_root
        cmd = _build_command(task)

        log_dir = os.path.join(cwd, "experiments", "queue_logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{task.id}.log")

        logger.info("Launching task %s: %s", task.id, " ".join(cmd))

        self._db.update_task(
            task.id,
            status="running",
            started_at=datetime.now(timezone.utc).isoformat(),
            log_path=log_path,
        )
        self._current_task_id = task.id

        try:
            with open(log_path, "w") as log_f:
                self._running = await asyncio.create_subprocess_exec(
                    *cmd,
                    cwd=cwd,
                    stdout=log_f,
                    stderr=asyncio.subprocess.STDOUT,
                )
        except Exception as e:
            logger.exception("Failed to launch task %s", task.id)
            self._db.update_task(
                task.id,
                status="failed",
                finished_at=datetime.now(timezone.utc).isoformat(),
                error_msg=str(e),
            )
            self._current_task_id = None
            self._running = None
