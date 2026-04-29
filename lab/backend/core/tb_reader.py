"""
TensorBoard event 文件读取器
从 tb_logger/[name]/ 目录读取指标数据
"""
import os
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import glob
from typing import Optional


def _get_tb_reader():
    try:
        from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
        return EventAccumulator
    except ImportError:
        return None


def get_tb_dir(exp_name: str, tb_root: str) -> Optional[str]:
    """返回实验对应的 TB 日志目录"""
    d = os.path.join(tb_root, exp_name)
    return d if os.path.isdir(d) else None


def list_scalar_tags(exp_name: str, tb_root: str) -> list[str]:
    """列出某实验可用的 TensorBoard 指标"""
    tb_dir = get_tb_dir(exp_name, tb_root)
    if not tb_dir:
        return []
    Reader = _get_tb_reader()
    if Reader is None:
        return []
    try:
        ea = Reader(tb_dir)
        ea.Reload()
        return ea.Tags().get("scalars", [])
    except Exception:
        return []


def get_scalar_data(exp_name: str, tag: str, tb_root: str) -> list[dict]:
    """读取某个指标的全部数据点"""
    tb_dir = get_tb_dir(exp_name, tb_root)
    if not tb_dir:
        return []
    Reader = _get_tb_reader()
    if Reader is None:
        return []
    try:
        ea = Reader(tb_dir)
        ea.Reload()
        events = ea.Scalars(tag)
        return [{"step": e.step, "value": e.value, "wall_time": e.wall_time} for e in events]
    except Exception:
        return []


def list_tb_experiments(tb_root: str) -> list[str]:
    """列出 tb_logger 下有哪些实验"""
    if not os.path.isdir(tb_root):
        return []
    return sorted([
        d for d in os.listdir(tb_root)
        if os.path.isdir(os.path.join(tb_root, d))
    ])
