"""
配置生成 API — 向导式配置编辑器后端
"""
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import json
import yaml
import glob
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from backend.config import PROJECT_ROOT

router = APIRouter(prefix="/api/configs", tags=["configs"])

# ─────────────────── 数据定义 ───────────────────

# 模型类型映射表
MODEL_REGISTRY_MAP = {
    "SRModel": {"label": "基础SR (SRModel)", "archs": ["MSRResNet", "EDSR", "RCAN", "SwinIR", "RRDBNet"]},
    "SwinIRModel": {"label": "SwinIR (SwinIRModel)", "archs": ["SwinIR"]},
    "SRGANModel": {"label": "SRGAN (SRGANModel)", "archs": ["MSRResNet", "RRDBNet"]},
    "ESRGANModel": {"label": "ESRGAN (ESRGANModel)", "archs": ["RRDBNet"]},
    "RealESRGANModel": {"label": "Real-ESRGAN", "archs": ["RRDBNet"]},
    "RealESRNetModel": {"label": "Real-ESRNet", "archs": ["RRDBNet"]},
    "EDVRModel": {"label": "EDVR 视频SR", "archs": ["EDVR"]},
    "VideoBaseModel": {"label": "视频SR基础", "archs": ["BasicVSR"]},
    "VideoRecurrentModel": {"label": "循环视频SR", "archs": ["BasicVSR", "BasicVSRPP"]},
    "VideoRecurrentGANModel": {"label": "循环视频SR+GAN", "archs": ["BasicVSR", "BasicVSRPP"]},
    "HiFaceGANModel": {"label": "人脸增强 HiFaceGAN", "archs": ["HiFaceGAN"]},
    "StyleGAN2Model": {"label": "图像生成 StyleGAN2", "archs": ["StyleGAN2"]},
}

# 网络架构参数定义
ARCH_PARAMS = {
    "MSRResNet": {
        "params": [
            {"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_out_ch", "label": "输出通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_feat", "label": "特征通道", "type": "int", "default": 64, "min": 4, "max": 512},
            {"name": "num_block", "label": "残差块数", "type": "int", "default": 16, "min": 1, "max": 64},
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
        ]
    },
    "EDSR": {
        "params": [
            {"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_out_ch", "label": "输出通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_feat", "label": "特征通道", "type": "int", "default": 64, "min": 4, "max": 512},
            {"name": "num_block", "label": "残差块数", "type": "int", "default": 16, "min": 1, "max": 64},
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
            {"name": "res_scale", "label": "残差缩放", "type": "float", "default": 1.0, "min": 0.1, "max": 2.0},
        ]
    },
    "RCAN": {
        "params": [
            {"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_out_ch", "label": "输出通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_feat", "label": "特征通道", "type": "int", "default": 64, "min": 4, "max": 512},
            {"name": "num_block", "label": "残差块(RCAB)数", "type": "int", "default": 20, "min": 1, "max": 50},
            {"name": "num_groups", "label": "组数(RIR)", "type": "int", "default": 10, "min": 1, "max": 20},
            {"name": "reduction", "label": "压缩比", "type": "int", "default": 16, "min": 1, "max": 64},
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
        ]
    },
    "SwinIR": {
        "params": [
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
            {"name": "in_chans", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "img_size", "label": "图块大小", "type": "int", "default": 48, "min": 16, "max": 256},
            {"name": "window_size", "label": "窗口大小", "type": "int", "default": 8, "min": 2, "max": 32},
            {"name": "img_range", "label": "像素范围", "type": "float", "default": 1.0, "min": 0.1, "max": 255},
            {"name": "depths", "label": "每层深度", "type": "list_int", "default": [6, 6, 6, 6, 6, 6], "hint": "逗号分隔，如 6,6,6,6"},
            {"name": "embed_dim", "label": "嵌入维度", "type": "int", "default": 180, "min": 32, "max": 1024},
            {"name": "num_heads", "label": "每层头数", "type": "list_int", "default": [6, 6, 6, 6, 6, 6], "hint": "逗号分隔，需与depths长度一致"},
            {"name": "mlp_ratio", "label": "MLP扩展比", "type": "float", "default": 2.0, "min": 1.0, "max": 8.0},
            {"name": "upsampler", "label": "上采样方式", "type": "select", "default": "pixelshuffle", "options": ["pixelshuffle", "nearest+conv", "pixelshuffledirect"]},
            {"name": "resi_connection", "label": "残差连接", "type": "select", "default": "1conv", "options": ["1conv", "3conv"]},
        ]
    },
    "RRDBNet": {
        "params": [
            {"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_out_ch", "label": "输出通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_feat", "label": "特征通道", "type": "int", "default": 64, "min": 4, "max": 512},
            {"name": "num_block", "label": "RRDB块数", "type": "int", "default": 23, "min": 1, "max": 64},
            {"name": "num_grow_ch", "label": "增长通道", "type": "int", "default": 32, "min": 1, "max": 128},
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
        ]
    },
    "BasicVSR": {
        "params": [
            {"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_out_ch", "label": "输出通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_feat", "label": "特征通道", "type": "int", "default": 64, "min": 4, "max": 512},
            {"name": "num_block", "label": "残差块数", "type": "int", "default": 15, "min": 1, "max": 50},
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
        ]
    },
    "BasicVSRPP": {
        "params": [
            {"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_out_ch", "label": "输出通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_feat", "label": "特征通道", "type": "int", "default": 64, "min": 4, "max": 512},
            {"name": "num_block", "label": "残差块数", "type": "int", "default": 15, "min": 1, "max": 50},
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
        ]
    },
    "EDVR": {
        "params": [
            {"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_out_ch", "label": "输出通道", "type": "int", "default": 3, "min": 1, "max": 64},
            {"name": "num_feat", "label": "特征通道", "type": "int", "default": 64, "min": 4, "max": 512},
            {"name": "num_frame", "label": "输入帧数", "type": "int", "default": 5, "min": 1, "max": 30},
            {"name": "deformable_groups", "label": "可变形分组", "type": "int", "default": 8, "min": 1, "max": 32},
            {"name": "num_blocks_extract", "label": "特征提取块数", "type": "int", "default": 5, "min": 1, "max": 20},
            {"name": "num_blocks_reconstruct", "label": "重建块数", "type": "int", "default": 40, "min": 1, "max": 80},
            {"name": "center_frame_idx", "label": "中心帧索引", "type": "int", "default": 2, "min": 0, "max": 28},
            {"name": "upscale", "label": "放大倍数", "type": "int", "default": 4, "min": 1, "max": 8},
        ]
    },
    "HiFaceGAN": {"params": [{"name": "num_in_ch", "label": "输入通道", "type": "int", "default": 3}]},
    "StyleGAN2": {"params": [{"name": "size", "label": "输出尺寸", "type": "int", "default": 256}, {"name": "style_dim", "label": "风格维度", "type": "int", "default": 512}]},
}

# 损失函数模板
LOSS_TEMPLATES = {
    "L1Loss": {"type": "L1Loss", "loss_weight": 1.0, "reduction": "mean"},
    "L2Loss": {"type": "L2Loss", "loss_weight": 1.0, "reduction": "mean"},
    "CharbonnierLoss": {"type": "CharbonnierLoss", "loss_weight": 1.0, "reduction": "mean"},
}

# 调度器模板
SCHEDULER_TEMPLATES = {
    "MultiStepLR": {"type": "MultiStepLR", "milestones": [250000, 400000, 450000, 475000], "gamma": 0.5},
    "CosineAnnealingRestartLR": {"type": "CosineAnnealingRestartLR", "periods": [500000], "restart_weights": [1], "eta_min": 1e-7},
    "ReduceLROnPlateau": {"type": "ReduceLROnPlateau", "mode": "min", "factor": 0.5, "patience": 5, "threshold": 1e-4},
}

# 数据集元信息
DATASET_META_PATH = Path(__file__).resolve().parent.parent.parent / "fluxsr" / "data" / "meta_info"

# 设置存储路径
SETTINGS_PATH = Path(__file__).resolve().parent / "settings.json"


# ─────────────────── 工具函数 ───────────────────

def _default_settings():
    return {
        "train_root": str(PROJECT_ROOT / "datasets"),
        "val_root": str(PROJECT_ROOT / "datasets"),
    }


def _load_settings():
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    return _default_settings()


def _save_settings(s: dict):
    SETTINGS_PATH.write_text(json.dumps(s, indent=2, ensure_ascii=False))


def _scan_datasets():
    """扫描已知的数据集"""
    datasets = []
    if DATASET_META_PATH.is_dir():
        for f in sorted(DATASET_META_PATH.glob("meta_info_*.txt")):
            name = f.stem.replace("meta_info_", "")
            datasets.append(name)
    return datasets


def _list_options_dirs():
    """列出 options/train/ 下的子目录"""
    train_dir = PROJECT_ROOT / "options" / "train"
    if not train_dir.is_dir():
        return []
    return sorted([d.name for d in train_dir.iterdir() if d.is_dir()])


# ─────────────────── API ───────────────────


@router.get("/info")
def config_info():
    """返回配置编辑器所需的所有元信息"""
    return {
        "model_types": MODEL_REGISTRY_MAP,
        "arch_params": ARCH_PARAMS,
        "loss_templates": LOSS_TEMPLATES,
        "scheduler_templates": SCHEDULER_TEMPLATES,
        "datasets": _scan_datasets(),
        "options_dirs": _list_options_dirs(),
        "settings": _load_settings(),
    }


class GenerateReq(BaseModel):
    # 基础
    name: str = "exp_001"
    model_type: str = "SRModel"
    scale: int = 4
    num_gpu: int = 1
    manual_seed: int = 0

    # 网络
    network_type: str = "MSRResNet"
    network_params: dict = {}

    # 数据集
    datasets: dict = {}
    train_root: str = ""
    val_root: str = ""
    gt_size: int = 128
    batch_size_per_gpu: int = 16
    num_worker_per_gpu: int = 4
    dataset_enlarge_ratio: int = 1
    use_hflip: bool = True
    use_rot: bool = True
    train_dataset_name: str = "DIV2K"
    val_dataset_name: str = "Set5"

    # 训练
    optim_type: str = "Adam"
    lr: float = 2e-4
    weight_decay: float = 0
    betas: list = [0.9, 0.99]
    scheduler_type: str = "CosineAnnealingRestartLR"
    scheduler_params: dict = {}
    total_iter: int = 500000
    warmup_iter: int = -1
    ema_decay: float = 0.999
    use_amp: bool = False

    # Loss
    pixel_loss_type: str = "L1Loss"
    pixel_loss_weight: float = 1.0

    # 高级（可选）
    has_perceptual_loss: bool = False
    perceptual_loss_weight: float = 0.1
    has_gan_loss: bool = False
    gan_loss_weight: float = 0.1

    # GAN 特有
    optim_d_params: Optional[dict] = None
    net_d_type: Optional[str] = None
    net_d_params: Optional[dict] = None

    # 其他
    print_freq: int = 100
    save_checkpoint_freq: int = 5000
    val_freq: int = 5000
    save_img: bool = True
    gpu_ids: str = "0"


@router.post("/generate")
def generate_config(req: GenerateReq):
    """生成完整 YAML 配置"""
    gpu_list = [int(x.strip()) for x in req.gpu_ids.split(",") if x.strip()] or [0]
    scale = req.scale

    # 路径配置
    exp_path = f"experiments/{req.name}"

    # 基础结构
    config = {
        "name": req.name,
        "model_type": req.model_type,
        "scale": scale,
        "num_gpu": len(gpu_list),
        "manual_seed": req.manual_seed,
        "datasets": {
            "train": {
                "name": req.train_dataset_name,
                "type": "PairedImageDataset",
                "dataroot_gt": f"{req.train_root}/HR",
                "dataroot_lq": f"{req.train_root}/LR_bicubic/X{scale}",
                "meta_info_file": f"fluxsr/data/meta_info/meta_info_{req.train_dataset_name}_GT.txt",
                "filename_tmpl": "{}",
                "io_backend": {"type": "disk"},
                "gt_size": req.gt_size,
                "use_hflip": req.use_hflip,
                "use_rot": req.use_rot,
                "num_worker_per_gpu": req.num_worker_per_gpu,
                "batch_size_per_gpu": req.batch_size_per_gpu,
                "dataset_enlarge_ratio": req.dataset_enlarge_ratio,
                "prefetch_mode": None,
            },
            "val": {
                "name": req.val_dataset_name,
                "type": "PairedImageDataset",
                "dataroot_gt": f"{req.val_root}/GTmod12",
                "dataroot_lq": f"{req.val_root}/LRbicx{scale}",
                "io_backend": {"type": "disk"},
            },
        },
        "network_g": {
            "type": req.network_type,
            **req.network_params,
        },
        "path": {
            "pretrain_network_g": None,
            "strict_load_g": True,
            "resume_state": None,
        },
        "train": {
            "ema_decay": req.ema_decay,
            "optim_g": {
                "type": req.optim_type,
                "lr": req.lr,
                "weight_decay": req.weight_decay,
            },
            "scheduler": {
                "type": req.scheduler_type,
                **req.scheduler_params,
            },
            "total_iter": req.total_iter,
            "warmup_iter": req.warmup_iter,
            "use_amp": req.use_amp,
        },
        "logger": {
            "print_freq": req.print_freq,
            "save_checkpoint_freq": req.save_checkpoint_freq,
            "use_tb_logger": True,
        },
        "val": {
            "freq": req.val_freq,
            "save_img": req.save_img,
        },
        "gpu_ids": gpu_list,
    }

    # Loss
    config["train"]["pixel_opt"] = {
        "type": req.pixel_loss_type,
        "loss_weight": req.pixel_loss_weight,
        "reduction": "mean",
    }

    if req.has_perceptual_loss:
        config["train"]["perceptual_opt"] = {
            "type": "PerceptualLoss",
            "layer_weights": {"conv5_4": 1.0},
            "vgg_type": "vgg19",
            "use_input_norm": True,
            "range_norm": False,
            "perceptual_weight": req.perceptual_loss_weight,
            "criterion": "l1",
        }

    if req.has_gan_loss:
        config["train"]["gan_opt"] = {
            "type": "GANLoss",
            "gan_type": "vanilla",
            "loss_weight": req.gan_loss_weight,
        }

    # GAN 特有优化器和判别器
    if req.optim_d_params:
        config["train"]["optim_d"] = req.optim_d_params
    if req.net_d_type:
        config["network_d"] = {"type": req.net_d_type, **(req.net_d_params or {})}

    # Val 指标（通用）
    config["val"]["metrics"] = {
        "psnr": {"type": "calculate_psnr", "crop_border": 2, "test_y_channel": True},
        "ssim": {"type": "calculate_ssim", "crop_border": 2, "test_y_channel": True},
    }

    yaml_str = yaml.dump(config, default_flow_style=False, allow_unicode=True, sort_keys=False, indent=2)
    return {"yaml": yaml_str}


class SaveReq(BaseModel):
    yaml_content: str
    subdir: str  # options/train/ 下的子目录名
    filename: str  # yaml 文件名（不含扩展名）


@router.post("/save")
def save_config(req: SaveReq):
    """将 YAML 配置保存到文件"""
    if not req.filename.strip():
        raise HTTPException(400, "文件名不能为空")
    if not req.subdir.strip():
        raise HTTPException(400, "子目录不能为空")

    safe_name = req.filename.strip().replace(" ", "_").replace("/", "_").replace("\\", "_")
    if not safe_name.endswith(".yml"):
        safe_name += ".yml"

    save_dir = PROJECT_ROOT / "options" / "train" / req.subdir.strip()
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / safe_name

    save_path.write_text(req.yaml_content, encoding="utf-8")
    return {"path": str(save_path), "ok": True}


@router.get("/options-dirs")
def list_options_dirs():
    """列出 options/train 下的子目录"""
    return {"dirs": _list_options_dirs()}


@router.post("/options-dirs")
def create_options_dir(name: str):
    """新建 options/train 下的子目录"""
    if not name.strip():
        raise HTTPException(400, "目录名不能为空")
    safe = name.strip().replace(" ", "_").replace("/", "_")
    d = PROJECT_ROOT / "options" / "train" / safe
    d.mkdir(parents=True, exist_ok=True)
    return {"path": str(d), "ok": True}


# ── 数据集路径设置 ──


@router.get("/settings")
def get_settings():
    return _load_settings()


class SettingsReq(BaseModel):
    train_root: str = ""
    val_root: str = ""


@router.post("/settings")
def update_settings(req: SettingsReq):
    s = _load_settings()
    if req.train_root:
        s["train_root"] = req.train_root
    if req.val_root:
        s["val_root"] = req.val_root
    _save_settings(s)
    return {"ok": True, "settings": s}
