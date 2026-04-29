"""
SQLite 数据库操作
"""
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import sqlite3
import threading
from typing import Optional
from backend.core.models import Task, _now_iso


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    config_path   TEXT NOT NULL,
    override_args TEXT DEFAULT '',
    gpu_count     INTEGER DEFAULT 1,
    status        TEXT DEFAULT 'queued'
                    CHECK(status IN ('queued','running','completed','failed','cancelled')),
    priority      INTEGER DEFAULT 0,
    created_at    TEXT NOT NULL,
    started_at    TEXT,
    finished_at   TEXT,
    log_path      TEXT,
    exit_code     INTEGER,
    error_msg     TEXT
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority, created_at);
"""


class Database:
    def __init__(self, path: str = "queue.db"):
        self._path = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._init_schema()

    def _init_schema(self):
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.commit()

    def close(self):
        self._conn.close()

    # ── CRUD ──

    def create_task(self, task: Task) -> Task:
        with self._lock:
            self._conn.execute(
                """INSERT INTO tasks
                   (id, name, config_path, override_args, gpu_count,
                    status, priority, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (task.id, task.name, task.config_path, task.override_args,
                 task.gpu_count, task.status, task.priority, task.created_at),
            )
            self._conn.commit()
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM tasks WHERE id = ?", (task_id,)
            ).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self, status: Optional[str] = None, limit: int = 200) -> list[dict]:
        with self._lock:
            if status:
                rows = self._conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY priority ASC, created_at DESC LIMIT ?",
                    (status, limit),
                ).fetchall()
            else:
                rows = self._conn.execute(
                    "SELECT * FROM tasks ORDER BY priority ASC, created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        return [dict(r) for r in rows]

    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        allowed = {
            "name", "config_path", "override_args", "gpu_count",
            "status", "priority", "started_at", "finished_at",
            "log_path", "exit_code", "error_msg",
        }
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return self.get_task(task_id)
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]
        with self._lock:
            self._conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
            self._conn.commit()
        return self.get_task(task_id)

    def delete_task(self, task_id: str) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM tasks WHERE id = ? AND status IN ('queued', 'failed', 'cancelled')",
                (task_id,),
            )
            self._conn.commit()
        return cur.rowcount > 0

    def get_stats(self) -> dict:
        with self._lock:
            rows = self._conn.execute(
                """SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status"""
            ).fetchall()
        stats = {"total": 0}
        for r in rows:
            stats[r["status"]] = r["cnt"]
            stats["total"] += r["cnt"]
        return stats

    def next_queued(self) -> Optional[Task]:
        with self._lock:
            row = self._conn.execute(
                """SELECT * FROM tasks
                   WHERE status = 'queued'
                   ORDER BY priority ASC, created_at ASC
                   LIMIT 1"""
            ).fetchone()
        return self._row_to_task(row) if row else None

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(**dict(row))
