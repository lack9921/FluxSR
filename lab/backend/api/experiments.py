"""
实验管理 API
"""
import os
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

from fastapi import APIRouter, Query
from typing import Optional

from backend.core.experiment_reader import (
    scan_experiments, get_exp_config_content, get_exp_log_tail
)
from backend.core.tb_reader import (
    list_scalar_tags, get_scalar_data, list_tb_experiments
)
from backend.config import EXPERIMENTS_ROOT, TB_LOGGER_ROOT

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("")
def list_experiments(root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    tb_exps = set(list_tb_experiments(TB_LOGGER_ROOT))
    for e in exps:
        e["has_tb"] = e["name"] in tb_exps
    return {"experiments": exps, "root": exp_root}


@router.get("/{exp_name}")
def get_experiment(exp_name: str, root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    for e in exps:
        if e["name"] == exp_name:
            # 加上 TB 信息
            e["tb_tags"] = list_scalar_tags(exp_name, TB_LOGGER_ROOT)
            return {"experiment": e}
    return {"experiment": None}


@router.get("/{exp_name}/config")
def get_config(exp_name: str, root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    content = get_exp_config_content(exp_name, exp_root)
    return {"content": content or ""}


@router.get("/{exp_name}/log")
def get_log(exp_name: str, tail: int = 100, root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    content = get_exp_log_tail(exp_name, exp_root, tail)
    return {"log": content or ""}


@router.get("/{exp_name}/metrics")
def get_metrics(exp_name: str, tag: str = "val/psnr"):
    data = get_scalar_data(exp_name, tag, TB_LOGGER_ROOT)
    return {"tag": tag, "data": data}


@router.get("/{exp_name}/tags")
def get_tags(exp_name: str):
    tags = list_scalar_tags(exp_name, TB_LOGGER_ROOT)
    return {"tags": tags}


@router.get("/{exp_name}/image")
def get_image(exp_name: str, path: str, root: Optional[str] = Query(None)):
    """返回实验结果图片"""
    exp_root = root or EXPERIMENTS_ROOT
    from fastapi.responses import FileResponse
    full_path = os.path.normpath(os.path.join(exp_root, exp_name, "visualization", path))
    if not full_path.startswith(os.path.normpath(os.path.join(exp_root, exp_name))):
        raise HTTPException(403, "Forbidden")
    if os.path.isfile(full_path):
        return FileResponse(full_path)
    raise HTTPException(404)


from fastapi import HTTPException
