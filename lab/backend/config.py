"""
Lab 全局配置
"""
import os
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

from pathlib import Path

# 项目根目录（取 lab/ 的父目录）
LAB_DIR = Path(__file__).resolve().parent  # lab/backend/
PROJECT_ROOT = LAB_DIR.parent.parent  # FluxSR/

# 默认实验根目录
EXPERIMENTS_ROOT = os.environ.get(
    "FLUXSR_EXP_ROOT",
    str(PROJECT_ROOT / "experiments")
)

# TensorBoard 日志根目录
TB_LOGGER_ROOT = os.environ.get(
    "FLUXSR_TB_ROOT",
    str(PROJECT_ROOT / "tb_logger")
)

# 数据库
_db_dir = LAB_DIR
_db_dir.mkdir(parents=True, exist_ok=True)
DB_PATH = os.environ.get(
    "FLUXSR_DB_PATH",
    str(_db_dir / "queue.db")
)

# 服务配置
HOST = "0.0.0.0"
PORT = 8899
