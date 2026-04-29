"""
数据模型
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _new_id() -> str:
    return uuid.uuid4().hex[:12]


@dataclass
class Task:
    id: str = field(default_factory=_new_id)
    name: str = ""
    config_path: str = ""
    override_args: str = ""
    gpu_count: int = 1
    status: str = "queued"          # queued | running | completed | failed | cancelled
    priority: int = 0
    created_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    log_path: Optional[str] = None
    exit_code: Optional[int] = None
    error_msg: Optional[str] = None

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Experiment:
    name: str
    path: str
    has_config: bool = False
    has_log: bool = False
    has_tb: bool = False
    checkpoint_count: int = 0
    state_count: int = 0
    image_count: int = 0
    max_iter: int = 0
    latest_mtime: str = ""
    is_running: bool = False
