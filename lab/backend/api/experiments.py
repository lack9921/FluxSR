"""
实验管理 API
"""
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import glob

from backend.core.experiment_reader import (
    scan_experiments, get_exp_config_content, get_exp_log_content
)
from backend.core.tb_reader import (
    parse_training_log, get_metric_columns
)
from backend.config import EXPERIMENTS_ROOT

router = APIRouter(prefix="/api/experiments", tags=["experiments"])


@router.get("")
def list_experiments(root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    return {"experiments": exps, "root": exp_root}


@router.get("/{exp_name}")
def get_experiment(exp_name: str, root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    for e in exps:
        if e["name"] == exp_name:
            # 加上可用指标
            if e.get("log_path"):
                e["available_tags"] = get_metric_columns(e["log_path"])
            return {"experiment": e}
    return {"experiment": None}


@router.get("/{exp_name}/config")
def get_config(exp_name: str, root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    for e in exps:
        if e["name"] == exp_name and e.get("config_path"):
            content = get_exp_config_content(e["config_path"])
            if content:
                return {"content": content}
    # Fallback: try to extract config from log header
    for e in exps:
        if e["name"] == exp_name and e.get("log_path"):
            with open(e["log_path"], 'r', errors='replace') as f:
                content = f.read(50000)
            # 日志前 100 行包含 yml 配置信息
            lines = content.split('\n')
            config_lines = []
            in_config = False
            for line in lines[:120]:
                if line.strip().startswith('name:') and not in_config:
                    in_config = True
                if line.strip().startswith('  criterion:') or line.strip().startswith('  phase:'):
                    pass  # keep going
                if in_config:
                    if line.strip().startswith('2026') or line.strip().startswith('Dataset'):
                        break
                    config_lines.append(line)
            if config_lines:
                return {"content": '\n'.join(config_lines), "source": "log_header"}
    return {"content": ""}


@router.get("/{exp_name}/log")
def get_log(exp_name: str, tail: int = 100, root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    for e in exps:
        if e["name"] == exp_name and e.get("log_path"):
            content = get_exp_log_content(e["log_path"], tail if tail > 0 else 0)
            return {"log": content or ""}
    return {"log": ""}


@router.get("/{exp_name}/metrics")
def get_metrics(exp_name: str, tag: str = "l_pix", root: Optional[str] = Query(None)):
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    for e in exps:
        if e["name"] == exp_name and e.get("log_path"):
            data = parse_training_log(e["log_path"])
            all_tags = data.get("metrics", {})
            if tag in all_tags:
                return {"tag": tag, "data": all_tags[tag]}
            # If tag not found but we have metrics, return the first available
            if all_tags:
                first_tag = list(all_tags.keys())[0]
                return {"tag": first_tag, "data": all_tags[first_tag]}
            return {"tag": tag, "data": []}
    return {"tag": tag, "data": []}


@router.get("/{exp_name}/all-metrics")
def get_all_metrics(exp_name: str, root: Optional[str] = Query(None)):
    """一次性返回所有指标曲线"""
    exp_root = root or EXPERIMENTS_ROOT
    exps = scan_experiments(exp_root)
    for e in exps:
        if e["name"] == exp_name and e.get("log_path"):
            data = parse_training_log(e["log_path"])
            return {
                "metrics": data.get("metrics", {}),
                "info": data.get("info", {}),
            }
    return {"metrics": {}, "info": {}}


@router.get("/{exp_name}/image")
def get_image(exp_name: str, path: str, root: Optional[str] = Query(None)):
    """返回实验结果图片"""
    exp_root = root or EXPERIMENTS_ROOT
    full_path = os.path.normpath(os.path.join(exp_root, exp_name, "visualization", path))
    if not full_path.startswith(os.path.normpath(os.path.join(exp_root, exp_name))):
        raise HTTPException(403, "Forbidden")
    if os.path.isfile(full_path):
        from fastapi.responses import FileResponse
        return FileResponse(full_path)
    raise HTTPException(404)


@router.get("/options/list")
def list_options(root: Optional[str] = Query(None)):
    """扫描 options/train/ 目录下的所有 YAML 配置文件"""
    proj_root = root or os.path.dirname(EXPERIMENTS_ROOT)
    options_dir = os.path.join(proj_root, "options", "train")
    if not os.path.isdir(options_dir):
        options_dir = os.path.join(proj_root, "options")
    if not os.path.isdir(options_dir):
        return {"configs": []}

    configs = []
    for f in sorted(glob.glob(os.path.join(options_dir, "**", "*.yml"), recursive=True)):
        rel = os.path.relpath(f, proj_root)
        configs.append({
            "path": f,
            "relative": rel,
            "name": os.path.splitext(os.path.basename(f))[0],
            "mtime": os.path.getmtime(f),
        })
    return {"configs": configs}
