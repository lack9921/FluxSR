"""
任务队列 API
"""
import os
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import asyncio
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from backend.core.db import Database
from backend.core.models import Task
from backend.config import PROJECT_ROOT

logger = logging.getLogger("lab.api.tasks")

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class CreateTaskReq(BaseModel):
    name: str
    config_path: str
    override_args: str = ""
    gpu_count: int = 1
    priority: int = 0


class UpdateTaskReq(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None


from fastapi import Depends


def get_db(request: Request) -> Database:
    return request.app.state.db


@router.get("")
def list_tasks(status: Optional[str] = None, db: Database = Depends(get_db)):
    return {"tasks": db.list_tasks(status=status), "stats": db.get_stats()}


@router.post("")
def create_task(req: CreateTaskReq, db: Database = Depends(get_db)):
    if not os.path.isfile(req.config_path):
        raise HTTPException(400, f"Config file not found: {req.config_path}")
    task = Task(name=req.name, config_path=req.config_path,
                override_args=req.override_args, gpu_count=req.gpu_count,
                priority=req.priority)
    db.create_task(task)
    return {"task": task.to_dict()}


@router.get("/{task_id}")
def get_task(task_id: str, db: Database = Depends(get_db)):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {"task": task.to_dict()}


@router.post("/{task_id}/cancel")
def cancel_task(task_id: str, db: Database = Depends(get_db)):
    task = db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.status != "queued":
        raise HTTPException(400, f"Cannot cancel task with status '{task.status}'")
    db.update_task(task_id, status="cancelled")
    return {"ok": True}


@router.delete("/{task_id}")
def delete_task(task_id: str, db: Database = Depends(get_db)):
    ok = db.delete_task(task_id)
    if not ok:
        raise HTTPException(400, "Task cannot be deleted (maybe running)")
    return {"ok": True}


@router.get("/{task_id}/log")
async def stream_log(task_id: str, tail: int = 100, db: Database = Depends(get_db)):
    """返回任务日志尾部"""
    task = db.get_task(task_id)
    if not task or not task.log_path:
        raise HTTPException(404, "No log")
    if not os.path.isfile(task.log_path):
        return {"log": "(file not found)"}
    with open(task.log_path) as f:
        lines = f.readlines()
    return {"log": "".join(lines[-tail:])}
