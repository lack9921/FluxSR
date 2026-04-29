"""
配置生成 API
"""
import os
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from backend.core.tb_reader import get_scalar_data

router = APIRouter(prefix="/api/configs", tags=["configs"])


class ConfigGenerateReq(BaseModel):
    experiment_name: str
    model_type: str
    model_params: dict = {}
    batch_size: int = 16
    lr: float = 2e-4
    total_iter: int = 500000
    fp16: bool = True
    train_root: str = "./datasets/DIV2K"
    val_root: str = "./datasets/Set5"
    gt_size: int = 128
    gpu_ids: str = "0"


@router.post("/generate")
def generate_config(req: ConfigGenerateReq):
    """生成 BasicSR 兼容的 YAML 配置"""
    gpu_list = [int(x.strip()) for x in req.gpu_ids.split(",") if x.strip()] or [0]

    config = {
        "name": req.experiment_name,
        "model_type": "SRModel",
        "scale": req.model_params.get("scale", req.model_params.get("upscale", 4)),
        "num_gpu": len(gpu_list),
        "manual_seed": 0,
        "datasets": {
            "train": {
                "name": "DIV2K",
                "type": "PairedImageDataset",
                "dataroot_gt": f"{req.train_root}/HR",
                "dataroot_lq": f"{req.train_root}/LR",
                "gt_size": req.gt_size,
                "io_backend": {"type": "disk"},
                "use_hflip": True,
                "use_rot": True,
                "num_worker_per_gpu": 4,
                "batch_size_per_gpu": req.batch_size,
                "dataset_enlarge_ratio": 1,
            },
            "val": {
                "name": "Set5",
                "type": "PairedImageDataset",
                "dataroot_gt": f"{req.val_root}/HR",
                "dataroot_lq": f"{req.val_root}/LR",
                "io_backend": {"type": "disk"},
            },
        },
        "path": {
            "experiments_root": f"experiments/{req.experiment_name}",
            "models": f"experiments/{req.experiment_name}/models",
            "training_states": f"experiments/{req.experiment_name}/training_states",
            "log": f"experiments/{req.experiment_name}",
            "visualization": f"experiments/{req.experiment_name}/visualization",
        },
        "network_g": {
            "type": req.model_type,
            **req.model_params,
        },
        "train": {
            "optim_g": {"type": "Adam", "lr": req.lr, "weight_decay": 0, "betas": [0.9, 0.99]},
            "scheduler": {"type": "CosineAnnealingRestartLR", "periods": [req.total_iter],
                          "restart_weights": [1], "eta_min": 1e-7},
            "total_iter": req.total_iter,
            "warmup_iter": 5000,
            "use_amp": not req.fp16,
        },
        "logger": {
            "print_freq": 100,
            "save_checkpoint_freq": 5000,
            "use_tb_logger": True,
        },
        "val": {
            "freq": 5000,
            "save_img": True,
            "metrics": {
                "psnr": {"type": "calculate_psnr", "crop_border": 2, "test_y_channel": True},
                "ssim": {"type": "calculate_ssim", "crop_border": 2, "test_y_channel": True},
            },
        },
        "gpu_ids": gpu_list,
    }

    import yaml
    yaml_str = yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)
    return {"yaml": yaml_str}
