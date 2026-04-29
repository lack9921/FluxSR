"""
训练数据读取器
从训练日志中解析指标数据（loss/pix 曲线 + PSNR/SSIM 验证曲线）
不依赖 TensorBoard
"""
import os
import sys
_lab_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _lab_dir not in sys.path:
    sys.path.insert(0, _lab_dir)

import re
from typing import Optional


def parse_training_log(log_path: str) -> dict:
    """
    从训练日志解析所有指标曲线
    
    支持的日志格式:
    - 训练步: [epoch: X, iter: Y, lr:(lr)] ... l_pix: val
    - 验证步: Validation X ... # psnr: val ... # ssim: val
    
    Returns:
        {
            "metrics": {
                "l_pix": [{"iter": int, "value": float}, ...],
                "psnr": [{"iter": int, "value": float}, ...],
                "ssim": [{"iter": int, "value": float}, ...],
            },
            "info": {
                "total_iters": int,
                "val_dataset": str,
                "num_metrics": int,
            }
        }
    """
    result = {
        "metrics": {},
        "info": {
            "total_iters": 0,
            "val_dataset": "",
            "num_metrics": 0,
        }
    }
    
    if not log_path or not os.path.isfile(log_path):
        return result
    
    l_pix_data = []
    psnr_data = []
    ssim_data = []
    
    # 训练步正则: [epoch: 60, iter: 247,400 ...] l_pix: 7.7327e-03
    train_re = re.compile(
        r'\[epoch:\s*\d+,\s*iter:\s*([\d,]+)'
    )
    l_pix_re = re.compile(r'l_pix:\s*([\d.eE+-]+)')
    
    # 验证正则
    val_re = re.compile(r'Validation\s+(\S+)')
    psnr_re = re.compile(r'#\s*psnr:\s*([\d.]+)')
    ssim_re = re.compile(r'#\s*ssim:\s*([\d.]+)')
    
    try:
        with open(log_path, 'r', errors='replace') as f:
            content = f.read()
        
        # 提取 total_iters 从日志头部
        total_iters_match = re.search(r'total_iter:\s*(\d+)', content)
        if total_iters_match:
            result["info"]["total_iters"] = int(total_iters_match.group(1))
        
        # 提取 val_dataset 名称
        val_match = re.search(r'Validation\s+(\S+)', content)
        if val_match:
            result["info"]["val_dataset"] = val_match.group(1)
        
        lines = content.split('\n')
        for line in lines:
            # 解析训练步 l_pix
            m_train = train_re.search(line)
            m_lpix = l_pix_re.search(line)
            if m_train and m_lpix:
                try:
                    it = int(m_train.group(1).replace(',', ''))
                    val = float(m_lpix.group(1))
                    l_pix_data.append({"iter": it, "value": val})
                except (ValueError, IndexError):
                    pass
            
            # 解析验证 psnr/ssim
            m_val = val_re.search(line)
            m_psnr = psnr_re.search(line)
            m_ssim = ssim_re.search(line)
            
            # 只有在 Validation 行才解析
            if m_val:
                try:
                    # 从当前行找 iter 信息
                    iter_in_line = re.search(r'@\s*([\d,]+)\s*iter', line)
                    if iter_in_line:
                        it = int(iter_in_line.group(1).replace(',', ''))
                    else:
                        # 从行尾 iter 标记找
                        m_iter_in_val = re.search(r'@\s*([\d,]+)', line)
                        if m_iter_in_val:
                            it = int(m_iter_in_val.group(1).replace(',', ''))
                        else:
                            continue
                    
                    if m_psnr:
                        psnr_data.append({"iter": it, "value": float(m_psnr.group(1))})
                    if m_ssim:
                        ssim_data.append({"iter": it, "value": float(m_ssim.group(1))})
                except (ValueError, IndexError):
                    pass
            
            # 同时处理行内可能有的 psnr/ssim（非 Validation 行）
            # 但为了避免重复，确保只有当行包含 "Validation" 时才解析验证指标
        
        # Also handle the case where psnr/ssim appears on a separate line
        # Format:
        # 2026-04-09 20:45:42,808 INFO: Validation Set5_Validation
        #   # psnr: 35.0539   Best: 35.0539 @ 5000 iter
        #   # ssim: 0.9463    Best: 0.9463 @ 5000 iter
        # In this case, psnr/ssim are on the NEXT line(s), not the same line as "Validation"
        
        i = 0
        while i < len(lines):
            line = lines[i]
            m_val = val_re.search(line)
            if m_val:
                iter_val = None
                # Look ahead for psnr/ssim on following lines
                j = i + 1
                while j < len(lines) and j <= i + 3:
                    next_line = lines[j]
                    # Check if this line has @ X iter
                    iter_match = re.search(r'@\s*([\d,]+)\s*iter', next_line)
                    if iter_match:
                        iter_val = int(iter_match.group(1).replace(',', ''))
                    
                    m_psnr = psnr_re.search(next_line)
                    m_ssim = ssim_re.search(next_line)
                    
                    if m_psnr and iter_val:
                        # Avoid duplicates
                        if not any(abs(d["iter"] - iter_val) < 10 and abs(d["value"] - float(m_psnr.group(1))) < 0.001 for d in psnr_data):
                            psnr_data.append({"iter": iter_val, "value": float(m_psnr.group(1))})
                    if m_ssim and iter_val:
                        if not any(abs(d["iter"] - iter_val) < 10 and abs(d["value"] - float(m_ssim.group(1))) < 0.001 for d in ssim_data):
                            ssim_data.append({"iter": iter_val, "value": float(m_ssim.group(1))})
                    
                    # If we hit another Validation or the line doesn't look like metrics, stop
                    if val_re.search(next_line) and j > i:
                        break
                    if not (psnr_re.search(next_line) or ssim_re.search(next_line) or iter_match or next_line.strip().startswith("#")):
                        break
                    j += 1
                i = j
            else:
                i += 1
    
    except Exception as e:
        print(f"Error parsing log: {e}")
    
    # Deduplicate and sort
    for data in [l_pix_data, psnr_data, ssim_data]:
        seen = set()
        deduped = []
        for d in data:
            key = (d["iter"], round(d["value"], 6))
            if key not in seen:
                seen.add(key)
                deduped.append(d)
        data.clear()
        data.extend(deduped)
        data.sort(key=lambda x: x["iter"])
    
    # 采样: 最多 2000 个点
    max_points = 2000
    for name, data in [("l_pix", l_pix_data), ("psnr", psnr_data), ("ssim", ssim_data)]:
        if len(data) > max_points:
            step = len(data) // max_points
            data = data[::step]
        if data:
            result["metrics"][name] = data
    
    result["info"]["num_metrics"] = len(result["metrics"])
    
    return result


def get_metric_columns(log_path: str) -> list[str]:
    """检测日志中有哪些指标列"""
    if not log_path or not os.path.isfile(log_path):
        return []
    
    columns = set()
    try:
        with open(log_path, 'r', errors='replace') as f:
            content = f.read(50000)  # 只看前 50KB
        
        if re.search(r'l_pix:', content):
            columns.add("l_pix")
        if re.search(r'#\s*psnr:', content):
            columns.add("psnr")
        if re.search(r'#\s*ssim:', content):
            columns.add("ssim")
    except Exception:
        pass
    
    return sorted(columns)
