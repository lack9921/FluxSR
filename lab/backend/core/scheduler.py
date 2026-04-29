"""
调度器：后台轮询队列，启动训练进程
"""
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from backend.core.db import Database
from backend.core.models import Task

logger = logging.getLogger("lab.scheduler")

POLL_INTERVAL = 5  # 秒


class Scheduler:
    def __init__(self, db: Database, train_script: str, cwd: str):
        self._db = db
        self._train_script = train_script
        self._cwd = cwd
        self._running_process: Optional[asyncio.subprocess.Process] = None
        self._current_task_id: Optional[str] = None
        self._stop_event = asyncio.Event()
        self._task = None

    async def start(self):
        logger.info("Scheduler started")
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self):
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
        if self._running_process:
            self._running_process.terminate()
            try: await self._running_process.wait()
            except: pass

    async def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                await self._tick()
            except Exception:
                logger.exception("tick error")
            await asyncio.sleep(POLL_INTERVAL)

    async def _tick(self):
        """检查正在运行的任务，取下一个排队任务"""
        if self._running_process:
            ret = self._running_process.returncode
            if ret is not None:
                task_id = self._current_task_id
                if ret == 0:
                    self._db.update_task(task_id, status="completed",
                        finished_at=datetime.now(timezone.utc).isoformat(), exit_code=ret)
                    logger.info("Task %s completed", task_id)
                else:
                    err = None
                    try:
                        out, _ = await self._running_process.communicate()
                        err = out.decode("utf-8", errors="replace")[-500:] if out else None
                    except: pass
                    self._db.update_task(task_id, status="failed",
                        finished_at=datetime.now(timezone.utc).isoformat(),
                        exit_code=ret, error_msg=err or f"exit {ret}")
                    logger.warning("Task %s failed code=%d", task_id, ret)
                self._running_process = None
                self._current_task_id = None
            return

        task = self._db.next_queued()
        if not task:
            return

        cmd = [sys.executable, self._train_script, "-opt", task.config_path]
        if task.override_args:
            # 解析额外参数
            tokens = task.override_args.split()
            for t in tokens:
                if "=" in t:
                    k, v = t.split("=", 1)
                    cmd.append(f"--override={k}={v}")
                else:
                    cmd.append(t)

        log_dir = os.path.join(self._cwd, "experiments", "queue_logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"{task.id}.log")

        self._db.update_task(task.id, status="running",
            started_at=datetime.now(timezone.utc).isoformat(), log_path=log_path)

        logger.info("Launching: %s", " ".join(cmd))
        self._current_task_id = task.id

        try:
            with open(log_path, "w") as lf:
                self._running_process = await asyncio.create_subprocess_exec(
                    *cmd, cwd=self._cwd, stdout=lf, stderr=asyncio.subprocess.STDOUT)
        except Exception as e:
            self._db.update_task(task.id, status="failed",
                finished_at=datetime.now(timezone.utc).isoformat(), error_msg=str(e))
            self._current_task_id = None
            self._running_process = None
