"""
FluxSR Lab — 后端入口
"""
import os
import sys
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# 支持直接 python main.py 运行
_lab_backend = os.path.dirname(os.path.abspath(__file__))
_lab_root = os.path.dirname(_lab_backend)
if _lab_backend not in sys.path:
    sys.path.insert(0, _lab_backend)
if _lab_root not in sys.path:
    sys.path.insert(0, _lab_root)

from backend.config import HOST, PORT, DB_PATH, EXPERIMENTS_ROOT, PROJECT_ROOT
from backend.core.db import Database
from backend.core.scheduler import Scheduler
from backend.api.tasks import router as tasks_router
from backend.api.experiments import router as experiments_router
from backend.api.configs import router as configs_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger("lab")


@asynccontextmanager
async def lifespan(app: FastAPI):
    db = Database(DB_PATH)
    app.state.db = db
    app.state.scheduler = None
    train_script = str(PROJECT_ROOT / "basicsr" / "train.py")
    if not os.path.isfile(train_script):
        train_script = str(PROJECT_ROOT / "fluxsr" / "train.py")
    if os.path.isfile(train_script):
        sched = Scheduler(db, train_script, str(PROJECT_ROOT))
        app.state.scheduler = sched
        await sched.start()
        logger.info("Scheduler started, train_script=%s", train_script)
    else:
        logger.warning("No train.py found")
    yield
    if app.state.scheduler:
        await app.state.scheduler.stop()
    db.close()
    logger.info("Lab shut down")


app = FastAPI(title="FluxSR Lab", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks_router)
app.include_router(experiments_router)
app.include_router(configs_router)


@app.get("/api/health")
def health():
    return {"status": "ok", "exp_root": EXPERIMENTS_ROOT, "db": DB_PATH}


@app.get("/api/info")
def info():
    return {
        "exp_root": EXPERIMENTS_ROOT,
        "tb_root": str(PROJECT_ROOT / "tb_logger"),
        "project_root": str(PROJECT_ROOT),
    }


# ── SPA fallback：前端静态文件 ──
from starlette.types import ASGIApp, Scope, Receive, Send

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
_has_frontend = os.path.isdir(frontend_dist)

if _has_frontend:
    class SPAFallbackMiddleware:
        def __init__(self, app: ASGIApp):
            self.app = app
        async def __call__(self, scope: Scope, receive: Receive, send: Send):
            if scope["type"] == "http" and scope["method"] in ("GET", "HEAD"):
                path = scope["path"]
                # 先交给 FastAPI 路由处理，看有没有匹配
                # 我们通过检查响应来确定——但中间件没法拦截响应
                # 改为：先试着返回静态文件，如果路径是 API 就跳过
                if path.startswith("/api"):
                    await self.app(scope, receive, send)
                    return
                # 尝试静态文件
                file_path = os.path.join(frontend_dist, path.lstrip("/"))
                if os.path.isfile(file_path):
                    resp = FileResponse(file_path)
                    await resp(scope, receive, send)
                    return
                # SPA fallback
                index_path = os.path.join(frontend_dist, "index.html")
                if os.path.isfile(index_path):
                    resp = FileResponse(index_path)
                    await resp(scope, receive, send)
                    return
            await self.app(scope, receive, send)

    app.add_middleware(SPAFallbackMiddleware)
    logger.info("Serving frontend SPA from %s", frontend_dist)


def main():
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")


if __name__ == "__main__":
    main()
