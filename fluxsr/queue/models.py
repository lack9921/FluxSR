from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


TaskStatus = {
    "queued": "queued",
    "running": "running",
    "completed": "completed",
    "failed": "failed",
    "cancelled": "cancelled",
}
VALID_STATUSES = set(TaskStatus.values())


@dataclass
class Task:
    id: str = field(default_factory=_new_id)
    name: str = ""
    config_path: str = ""
    override_args: str = ""
    gpu_count: int = 1
    status: str = "queued"
    priority: int = 0
    created_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    log_path: Optional[str] = None
    exit_code: Optional[int] = None
    error_msg: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}
