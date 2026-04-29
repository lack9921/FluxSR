"""
实验扫描器
扫描 experiments/ 目录，按 BasicSR 产物结构解析
支持 train_<name>_<timestamp>.log 命名格式
"""
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import re
import glob
from datetime import datetime
from typing import Optional


def _find_log_file(exp_dir: str, exp_name: str) -> Optional[str]:
    """查找实验日志文件，支持多种命名格式"""
    patterns = [
        f"train_{exp_name}_*.log",      # train_005_xxx_20260409_201214.log
        "train.log",                     # train.log
        f"{exp_name}.log",              # 005_xxx.log
        "*train*.log",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.join(exp_dir, pattern)))
        if matches:
            return matches[-1]  # 取最新的
    return None


def _find_config_file(exp_dir: str, exp_name: str) -> Optional[str]:
    """查找实验配置文件"""
    patterns = [
        f"{exp_name}.yml",
        f"{exp_name}.yaml",
        "train.yml",
        "train.yaml",
        "*.yml",
        "*.yaml",
    ]
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.join(exp_dir, pattern)))
        if matches:
            return matches[0]
    return None


def scan_experiments(exp_root: str) -> list[dict]:
    """扫描实验目录"""
    if not os.path.isdir(exp_root):
        return []

    experiments = []
    for exp_dir in sorted(glob.glob(os.path.join(exp_root, "*/"))):
        name = os.path.basename(os.path.normpath(exp_dir))

        # 跳过 pretrained_models 等非实验目录
        if name in ("pretrained_models", "__pycache__"):
            continue

        log_path = _find_log_file(exp_dir, name)
        config_path = _find_config_file(exp_dir, name)
        models_dir = os.path.join(exp_dir, "models")
        vis_dir = os.path.join(exp_dir, "visualization")
        states_dir = os.path.join(exp_dir, "training_states")

        has_log = log_path is not None
        has_config = config_path is not None
        has_models = os.path.isdir(models_dir)

        if not has_log and not has_config and not has_models:
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

        # 日志行数和状态
        log_lines = 0
        status = "unknown"
        if has_log:
            try:
                with open(log_path) as f:
                    content = f.read()
                    log_lines = content.count('\n')
                    if "End of training" in content:
                        status = "completed"
                    elif "Saving models and training states" in content:
                        status = "running"
                    elif content.strip():
                        status = "stopped"
            except Exception:
                pass

        # 验证指标（从日志尾部快速扫描）
        has_psnr = has_ssim = False
        if has_log:
            try:
                with open(log_path) as f:
                    for line in f.readlines()[-200:]:
                        if "# psnr:" in line:
                            has_psnr = True
                        if "# ssim:" in line:
                            has_ssim = True
            except Exception:
                pass

        # Val 数据集名称
        val_dataset = ""
        if has_log:
            try:
                with open(log_path) as f:
                    for line in f.readlines()[:100]:
                        m = re.search(r'Validation (\S+)', line)
                        if m:
                            val_dataset = m.group(1)
                            break
            except Exception:
                pass

        experiments.append({
            "name": name,
            "status": status,
            "has_config": has_config,
            "has_log": has_log,
            "log_lines": log_lines,
            "has_psnr": has_psnr,
            "has_ssim": has_ssim,
            "val_dataset": val_dataset,
            "mtime": datetime.fromtimestamp(os.path.getmtime(exp_dir)).strftime("%Y-%m-%d %H:%M"),
            "checkpoints": checkpoints,
            "state_files": state_files,
            "images": images,
            "config_path": config_path if has_config else None,
            "log_path": log_path,
        })

    return experiments


def get_exp_config_content(config_path: str) -> Optional[str]:
    """读取实验的 YAML 配置文件内容"""
    if config_path and os.path.isfile(config_path):
        with open(config_path) as f:
            return f.read()
    return None


def get_exp_log_content(log_path: str, max_lines: int = 0) -> Optional[str]:
    """读取训练日志内容"""
    if not log_path or not os.path.isfile(log_path):
        return None
    with open(log_path) as f:
        if max_lines > 0:
            lines = f.readlines()
            return "".join(lines[-max_lines:])
        return f.read()
