"""
实验扫描器
扫描 experiments/ 目录，按 BasicSR 产物结构解析
"""
import os
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import re
import glob
from datetime import datetime
from typing import Optional


def scan_experiments(exp_root: str) -> list[dict]:
    """扫描实验目录"""
    if not os.path.isdir(exp_root):
        return []

    experiments = []
    for exp_dir in sorted(glob.glob(os.path.join(exp_root, "*/"))):
        name = os.path.basename(os.path.normpath(exp_dir))

        # 校验是否有效实验
        config_path = os.path.join(exp_dir, f"{name}.yml")
        if not os.path.isfile(config_path):
            config_path = os.path.join(exp_dir, "train.yml")
        has_config = os.path.isfile(config_path)
        has_log = os.path.isfile(os.path.join(exp_dir, "train.log"))
        models_dir = os.path.join(exp_dir, "models")
        vis_dir = os.path.join(exp_dir, "visualization")
        states_dir = os.path.join(exp_dir, "training_states")

        if not has_config and not has_log and not os.path.isdir(models_dir):
            continue

        # 检查点
        checkpoints = []
        if os.path.isdir(models_dir):
            for ckpt in sorted(glob.glob(os.path.join(models_dir, "*.pth"))):
                stat = os.stat(ckpt)
                checkpoints.append({
                    "name": os.path.basename(ckpt),
                    "size_mb": round(stat.st_size / 1024 / 1024, 1),
                    "mtime": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                })

        # 状态文件
        state_files = []
        if os.path.isdir(states_dir):
            for sf in sorted(glob.glob(os.path.join(states_dir, "*.state"))):
                stat = os.stat(sf)
                state_files.append({
                    "name": os.path.basename(sf),
                    "size_mb": round(stat.st_size / 1024 / 1024, 1),
                })

        # 验证结果图
        images = []
        if os.path.isdir(vis_dir):
            for img in sorted(
                glob.glob(os.path.join(vis_dir, "**", "*.png"), recursive=True) +
                glob.glob(os.path.join(vis_dir, "**", "*.jpg"), recursive=True)
            ):
                rel = os.path.relpath(img, vis_dir)
                images.append({"name": rel, "path": img})

        # 日志行数
        log_lines = 0
        if has_log:
            with open(os.path.join(exp_dir, "train.log")) as f:
                log_lines = sum(1 for _ in f)

        # 最大迭代
        max_iter = 0
        for ckpt in checkpoints:
            m = re.search(r'(\d+)', ckpt["name"])
            if m:
                max_iter = max(max_iter, int(m.group(1)))

        # 是否运行中（15分钟内更新过）
        is_running = (datetime.now().timestamp() - os.path.getmtime(exp_dir)) < 900

        experiments.append({
            "name": name,
            "has_config": has_config,
            "has_log": has_log,
            "log_lines": log_lines,
            "max_iter": max_iter,
            "is_running": is_running,
            "mtime": datetime.fromtimestamp(os.path.getmtime(exp_dir)).strftime("%Y-%m-%d %H:%M"),
            "checkpoints": checkpoints,
            "state_files": state_files,
            "images": images,
            "config_path": config_path if has_config else None,
            "log_path": os.path.join(exp_dir, "train.log") if has_log else None,
        })

    return experiments


def get_exp_config_content(exp_name: str, exp_root: str) -> Optional[str]:
    """读取实验的 YAML 配置文件内容"""
    for fname in [f"{exp_name}.yml", "train.yml"]:
        fpath = os.path.join(exp_root, exp_name, fname)
        if os.path.isfile(fpath):
            with open(fpath) as f:
                return f.read()
    return None


def get_exp_log_tail(exp_name: str, exp_root: str, lines: int = 100) -> Optional[str]:
    """读取训练日志尾部"""
    fpath = os.path.join(exp_root, exp_name, "train.log")
    if not os.path.isfile(fpath):
        return None
    with open(fpath) as f:
        all_lines = f.readlines()
    return "".join(all_lines[-lines:])
