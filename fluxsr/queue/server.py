"""FluxSR Queue Web Server.

Usage:
    python -m fluxsr.queue.server --port 8899 --db queue.db

This starts the FastAPI web server with:
  - REST API for task CRUD
  - Web dashboard at /
  - Background scheduler that auto-pulls and runs queued tasks
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .database import Database
from .models import Task, _new_id, _now_iso
from .scheduler import Scheduler

logger = logging.getLogger("fluxsr.queue.server")

app = FastAPI(title="FluxSR Training Queue")

# ---- Global state (set during startup) ----
_db: Database = None
_scheduler: Scheduler = None


# ===================== Request/Response Models =====================


class CreateTaskRequest(BaseModel):
    name: str
    config_path: str
    override_args: str = ""
    gpu_count: int = 1
    priority: int = 0


class UpdateTaskRequest(BaseModel):
    name: str | None = None
    config_path: str | None = None
    override_args: str | None = None
    gpu_count: int | None = None
    priority: int | None = None


class ReorderRequest(BaseModel):
    order: list[str]


# ===================== REST API =====================


@app.get("/api/tasks")
def list_tasks(status: str = Query(None, regex="^(queued|running|completed|failed|cancelled)?$")):
    tasks = _db.list_tasks(status=status)
    stats = _db.get_stats()
    return {
        "tasks": [t.to_dict() for t in tasks],
        "total": stats.get("total", 0),
        "running": stats.get("running", 0),
        "queued": stats.get("queued", 0),
        "completed": stats.get("completed", 0),
        "failed": stats.get("failed", 0),
    }


@app.post("/api/tasks", status_code=201)
def create_task(req: CreateTaskRequest):
    # Validate config_path exists
    full_path = Path(req.config_path)
    cwd = Path.cwd()
    config_file = cwd / req.config_path if not full_path.is_absolute() else full_path
    if not config_file.exists():
        # Try relative to project root
        config_file = cwd / req.config_path
        if not config_file.exists():
            raise HTTPException(400, f"Config file not found: {req.config_path}")

    task = Task(
        name=req.name,
        config_path=str(config_file),
        override_args=req.override_args,
        gpu_count=req.gpu_count,
        priority=req.priority,
    )
    _db.create_task(task)
    logger.info("Task created: %s (%s)", task.id, task.name)
    return task.to_dict()


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    task = _db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task.to_dict()


@app.patch("/api/tasks/{task_id}")
def update_task(task_id: str, req: UpdateTaskRequest):
    task = _db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    updates = {k: v for k, v in req.model_dump(exclude_none=True).items()}
    if not updates:
        return task.to_dict()

    task = _db.update_task(task_id, **updates)
    return task.to_dict()


@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    ok = _db.delete_task(task_id)
    if not ok:
        raise HTTPException(400, "Task not found or cannot be deleted (running/completed tasks cannot be deleted)")
    return {"ok": True}


@app.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str):
    task = _db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.status not in ("running", "queued"):
        raise HTTPException(400, f"Cannot cancel task with status: {task.status}")

    if task.status == "queued":
        _db.update_task(task_id, status="cancelled", finished_at=_now_iso())
    else:
        # scheduler will pick up the cancellation
        _db.update_task(task_id, status="cancelled")

    return {"ok": True}


@app.post("/api/tasks/{task_id}/retry")
def retry_task(task_id: str):
    task = _db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if task.status not in ("failed", "cancelled"):
        raise HTTPException(400, f"Cannot retry task with status: {task.status}")

    _db.update_task(
        task_id,
        status="queued",
        priority=max(0, task.priority - 1),  # retry gets slightly higher priority
        started_at=None,
        finished_at=None,
        exit_code=None,
        error_msg=None,
    )
    return {"ok": True}


@app.patch("/api/tasks/reorder")
def reorder_tasks(req: ReorderRequest):
    _db.reorder_tasks(req.order)
    return {"ok": True}


@app.get("/api/stats")
def get_stats():
    return _db.get_stats()


@app.get("/api/tasks/{task_id}/log")
def get_task_log(task_id: str):
    task = _db.get_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    if not task.log_path or not os.path.exists(task.log_path):
        return PlainTextResponse("(no log file yet)")

    try:
        with open(task.log_path, "r", errors="replace") as f:
            content = f.read()
        return PlainTextResponse(content or "(empty log)")
    except Exception as e:
        return PlainTextResponse(f"(error reading log: {e})")


# ===================== Web Dashboard =====================


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return HTMLResponse(_DASHBOARD_HTML)


# ===================== Startup / Shutdown =====================


@app.on_event("startup")
async def startup():
    global _scheduler
    if _db is None:
        logger.error("Database not initialized. Use run() to start the server.")
        return
    _scheduler = Scheduler(_db, project_root=str(Path.cwd()))
    await _scheduler.start()


@app.on_event("shutdown")
async def shutdown():
    if _scheduler:
        await _scheduler.stop()


# ===================== Entry Point =====================


def run():
    parser = argparse.ArgumentParser(description="FluxSR Training Queue Server")
    parser.add_argument("--port", type=int, default=8899, help="Server port (default: 8899)")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--db", type=str, default="queue.db", help="SQLite database path (default: queue.db)")
    parser.add_argument("--log-level", type=str, default="info", choices=["debug", "info", "warning", "error"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper()),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    global _db
    _db = Database(args.db)

    logger.info("FluxSR Queue Server starting on http://%s:%d", args.host, args.port)
    uvicorn.run(app, host=args.host, port=args.port, log_level=args.log_level)


if __name__ == "__main__":
    run()

# ===================== Inline Dashboard HTML =====================

_DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="en" data-bs-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FluxSR Queue</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { padding-top: 20px; }
        .task-card { margin-bottom: 8px; }
        .task-card .card-body { padding: 12px 16px; }
        .status-badge { font-size: 0.75rem; }
        .progress-thin { height: 4px; }
        .task-actions .btn { padding: 2px 8px; font-size: 0.8rem; }
        .drag-handle { cursor: grab; color: #6c757d; margin-right: 8px; }
        .drag-handle:active { cursor: grabbing; }
        .section-title { margin-top: 24px; margin-bottom: 12px; }
        .empty-state { color: #6c757d; text-align: center; padding: 40px; }
        #logModal .modal-body { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.8rem; max-height: 60vh; overflow-y: auto; white-space: pre-wrap; background: #1a1a2e; color: #e0e0e0; }
        #queue-status { margin-bottom: 16px; }
        .navbar-brand { font-weight: 700; letter-spacing: -0.5px; }
        .toast-container { position: fixed; top: 20px; right: 20px; z-index: 9999; }
    </style>
</head>
<body>
    <div class="container">
        <nav class="navbar navbar-dark border-bottom mb-4 px-0">
            <span class="navbar-brand mb-0 h1">⚡ FluxSR Queue</span>
            <div>
                <button class="btn btn-primary btn-sm me-2" data-bs-toggle="modal" data-bs-target="#addTaskModal">+ Add Task</button>
                <span id="autoStartIndicator" class="badge bg-success">Auto</span>
            </div>
        </nav>

        <div id="queue-status" class="row text-center g-2">
            <div class="col-3">
                <div class="border rounded p-2">
                    <div class="small text-secondary">Queued</div>
                    <div id="stat-queued" class="fs-5 fw-bold">0</div>
                </div>
            </div>
            <div class="col-3">
                <div class="border rounded p-2 border-primary">
                    <div class="small text-secondary">Running</div>
                    <div id="stat-running" class="fs-5 fw-bold text-primary">0</div>
                </div>
            </div>
            <div class="col-3">
                <div class="border rounded p-2 border-success">
                    <div class="small text-secondary">Done</div>
                    <div id="stat-completed" class="fs-5 fw-bold text-success">0</div>
                </div>
            </div>
            <div class="col-3">
                <div class="border rounded p-2 border-danger">
                    <div class="small text-secondary">Failed</div>
                    <div id="stat-failed" class="fs-5 fw-bold text-danger">0</div>
                </div>
            </div>
        </div>

        <h6 class="section-title">Queue</h6>
        <div id="task-list"></div>
    </div>

    <!-- Add Task Modal -->
    <div class="modal fade" id="addTaskModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Add Training Task</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-3">
                        <label class="form-label">Task Name</label>
                        <input id="task-name" class="form-control" placeholder="e.g. swinir_x4_v2">
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Config Path</label>
                        <input id="task-config" class="form-control" list="config-list" placeholder="options/train/SwinIR/train_SwinIR_SRx4_scratch.yml">
                        <datalist id="config-list"></datalist>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Override Args <small class="text-secondary">(optional)</small></label>
                        <input id="task-override" class="form-control" placeholder="--batch_size 16 --lr 2e-4">
                        <div class="form-text">Flags: <code>--auto_resume</code> | Overrides: <code>--batch_size 16</code></div>
                    </div>
                    <div class="row mb-3">
                        <div class="col">
                            <label class="form-label">GPU Count</label>
                            <input id="task-gpu" class="form-control" type="number" value="1" min="1" max="8">
                        </div>
                        <div class="col">
                            <label class="form-label">Priority</label>
                            <input id="task-priority" class="form-control" type="number" value="0" min="0" max="99">
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button id="btn-add-task" type="button" class="btn btn-primary">Add to Queue</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Log Modal -->
    <div class="modal fade" id="logModal" tabindex="-1">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">Task Log</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body"><pre id="log-content">Loading...</pre></div>
            </div>
        </div>
    </div>

    <!-- Toast -->
    <div class="toast-container">
        <div id="toast" class="toast align-items-center text-bg-success border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body" id="toast-body"></div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        // ====== State ======
        let tasks = [];
        let pollTimer = null;

        // ====== API ======
        async function api(path, opts = {}) {
            const res = await fetch(path, {
                headers: { 'Content-Type': 'application/json', ...opts.headers },
                ...opts
            });
            if (!res.ok) {
                const text = await res.text();
                throw new Error(text);
            }
            return res.json();
        }

        // ====== Render ======
        function renderTasks() {
            const container = document.getElementById('task-list');
            const sorted = [...tasks].sort((a, b) => {
                const order = { running: 0, queued: 1, failed: 2, completed: 3, cancelled: 4 };
                return (order[a.status] || 99) - (order[b.status] || 99) || a.priority - b.priority;
            });

            if (sorted.length === 0) {
                container.innerHTML = '<div class="empty-state"><p class="mb-1 fs-5">🌊 No tasks</p><small>Click "+ Add Task" to start training</small></div>';
                return;
            }

            container.innerHTML = sorted.map(t => {
                const statusColors = {
                    running: 'primary', queued: 'secondary',
                    completed: 'success', failed: 'danger', cancelled: 'dark'
                };
                const sc = statusColors[t.status] || 'secondary';
                const isRunning = t.status === 'running';
                const isQueued = t.status === 'queued';
                const canDelete = isQueued || t.status === 'failed' || t.status === 'cancelled';
                const name = t.name || t.config_path.split('/').pop();
                return `
                <div class="card task-card border-${sc}" data-id="${t.id}" draggable="${isQueued}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div class="d-flex align-items-center flex-grow-1">
                                ${isQueued ? '<span class="drag-handle">⠿</span>' : '<span class="drag-handle" style="opacity:0.3">⠿</span>'}
                                <div>
                                    <div><strong>${esc(name)}</strong> <span class="badge bg-${sc} status-badge">${t.status}</span></div>
                                    <small class="text-secondary">${esc(t.config_path)}${t.override_args ? ' <code>'+esc(t.override_args)+'</code>' : ''}</small>
                                </div>
                            </div>
                            <div class="task-actions text-nowrap">
                                ${t.status === 'running' ? `<button class="btn btn-outline-light btn-sm" onclick="viewLog('${t.id}')">📋 Log</button>` : ''}
                                ${t.status === 'failed' ? `<button class="btn btn-outline-danger btn-sm" onclick="retry('${t.id}')">↻ Retry</button>` : ''}
                                ${t.status === 'running' ? `<button class="btn btn-outline-light btn-sm" onclick="cancel('${t.id}')">⏹ Stop</button>` : ''}
                                ${t.status === 'queued' ? `<button class="btn btn-outline-light btn-sm" onclick="cancel('${t.id}')">✕</button>` : ''}
                                ${canDelete ? `<button class="btn btn-outline-light btn-sm" onclick="del('${t.id}')">🗑</button>` : ''}
                                ${t.status === 'completed' ? `<button class="btn btn-outline-success btn-sm" onclick="viewLog('${t.id}')">📋 Log</button>` : ''}
                                ${t.status === 'failed' ? `<button class="btn btn-outline-danger btn-sm" onclick="viewLog('${t.id}')">📋 Log</button>` : ''}
                            </div>
                        </div>
                        ${isRunning ? '<div class="progress progress-thin mt-2"><div class="progress-bar progress-bar-striped progress-bar-animated" style="width:100%"></div></div>' : ''}
                    </div>
                </div>`;
            }).join('');
        }

        function esc(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

        // ====== Poll ======
        async function poll() {
            try {
                const data = await api('/api/tasks');
                tasks = data.tasks;
                renderTasks();
                document.getElementById('stat-queued').textContent = data.queued || 0;
                document.getElementById('stat-running').textContent = data.running || 0;
                document.getElementById('stat-completed').textContent = data.completed || 0;
                document.getElementById('stat-failed').textContent = data.failed || 0;
            } catch (e) {
                console.error('Poll error:', e);
            }
        }

        // ====== Actions ======
        async function addTask() {
            const name = document.getElementById('task-name').value.trim();
            const config = document.getElementById('task-config').value.trim();
            const override = document.getElementById('task-override').value.trim();
            const gpu = parseInt(document.getElementById('task-gpu').value) || 1;
            const priority = parseInt(document.getElementById('task-priority').value) || 0;

            if (!config) { showToast('Config path is required', 'danger'); return; }

            try {
                await api('/api/tasks', {
                    method: 'POST',
                    body: JSON.stringify({ name, config_path: config, override_args: override, gpu_count: gpu, priority })
                });
                bootstrap.Modal.getInstance(document.getElementById('addTaskModal')).hide();
                document.getElementById('task-name').value = '';
                document.getElementById('task-config').value = '';
                document.getElementById('task-override').value = '';
                showToast('Task added to queue', 'success');
                poll();
            } catch (e) {
                showToast('Error: ' + e.message, 'danger');
            }
        }

        async function cancel(id) {
            try {
                await api('/api/tasks/' + id + '/cancel', { method: 'POST' });
                poll();
            } catch (e) { showToast('Error: ' + e.message, 'danger'); }
        }

        async function retry(id) {
            try {
                await api('/api/tasks/' + id + '/retry', { method: 'POST' });
                showToast('Task requeued', 'success');
                poll();
            } catch (e) { showToast('Error: ' + e.message, 'danger'); }
        }

        async function del(id) {
            if (!confirm('Delete this task?')) return;
            try {
                await api('/api/tasks/' + id, { method: 'DELETE' });
                poll();
            } catch (e) { showToast('Error: ' + e.message, 'danger'); }
        }

        async function viewLog(id) {
            const modal = new bootstrap.Modal(document.getElementById('logModal'));
            document.getElementById('log-content').textContent = 'Loading...';
            modal.show();
            try {
                const res = await fetch('/api/tasks/' + id + '/log');
                const text = await res.text();
                document.getElementById('log-content').textContent = text;
            } catch (e) {
                document.getElementById('log-content').textContent = 'Error loading log: ' + e.message;
            }
        }

        function showToast(msg, type = 'success') {
            const toast = document.getElementById('toast');
            toast.className = 'toast align-items-center text-bg-' + type + ' border-0';
            document.getElementById('toast-body').textContent = msg;
            bootstrap.Toast.getOrCreateInstance(toast).show();
        }

        // ====== Load config options ======
        async function loadConfigs() {
            try {
                const data = await api('/api/tasks');
                // We can't list files via API easily, so just offer a hint
            } catch (e) {}
        }

        // ====== Drag to reorder ======
        let dragSrcId = null;
        document.addEventListener('dragstart', e => {
            if (e.target.closest('[draggable=true]')) {
                dragSrcId = e.target.closest('[data-id]')?.dataset.id;
                e.dataTransfer.effectAllowed = 'move';
            }
        });
        document.addEventListener('dragover', e => {
            if (e.target.closest('[data-id]')) e.preventDefault();
        });
        document.addEventListener('drop', async e => {
            const target = e.target.closest('[data-id]');
            if (!target || !dragSrcId || dragSrcId === target.dataset.id) return;
            // Reorder in the current sorted list
            const ids = [...document.querySelectorAll('#task-list .task-card')].map(el => el.dataset.id);
            const fromIdx = ids.indexOf(dragSrcId);
            const toIdx = ids.indexOf(target.dataset.id);
            if (fromIdx === -1 || toIdx === -1) return;
            ids.splice(fromIdx, 1);
            ids.splice(toIdx, 0, dragSrcId);
            try {
                await api('/api/tasks/reorder', {
                    method: 'PATCH',
                    body: JSON.stringify({ order: ids })
                });
                poll();
            } catch (e) { showToast('Reorder error: ' + e.message, 'danger'); }
        });

        // ====== Init ======
        document.getElementById('btn-add-task').addEventListener('click', addTask);

        // Initial load
        poll();
        pollTimer = setInterval(poll, 3000);

        // Re-poll on modal close
        document.getElementById('addTaskModal').addEventListener('hidden.bs.modal', poll);
    </script>
</body>
</html>"""
