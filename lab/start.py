"""
FluxSR Lab — 一键启动脚本
自动检查前端构建状态，启动后端服务
"""

import os
import sys
import subprocess
import time

LAB_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(LAB_DIR, "frontend")
BACKEND_DIR = os.path.join(LAB_DIR, "backend")
DIST_DIR = os.path.join(FRONTEND_DIR, "dist")
INDEX_HTML = os.path.join(DIST_DIR, "index.html")


def check_node() -> bool:
    """检查 Node.js 是否可用"""
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"  ✅ Node.js {result.stdout.strip()}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    print("  ❌ Node.js 未安装，无法构建前端")
    return False


def check_npm() -> bool:
    """检查 npm 是否可用"""
    try:
        result = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    print("  ❌ npm 未安装")
    return False


def check_frontend_deps() -> bool:
    """检查 node_modules 是否存在"""
    node_modules = os.path.join(FRONTEND_DIR, "node_modules")
    if os.path.isdir(node_modules):
        return True
    print("  ⚠️ node_modules 不存在，正在安装依赖...")
    result = subprocess.run(
        ["npm", "install"],
        cwd=FRONTEND_DIR,
        capture_output=True, text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  ❌ npm install 失败:\n{result.stderr[-500:]}")
        return False
    print("  ✅ 依赖安装完成")
    return True


def build_frontend() -> bool:
    """构建前端"""
    print("  🏗️  正在构建前端...")
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        capture_output=True, text=True,
        timeout=120,
    )
    if result.returncode != 0:
        print(f"  ❌ 构建失败:\n{result.stderr[-500:]}")
        return False
    print("  ✅ 前端构建完成")
    return True


def check_backend_deps() -> bool:
    """检查后端依赖是否安装"""
    try:
        import fastapi
        import uvicorn
        import yaml
        return True
    except ImportError:
        print("  ⚠️ 后端依赖未完全安装，正在安装...")
        req_file = os.path.join(BACKEND_DIR, "requirements.txt")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            capture_output=True, text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  ❌ pip install 失败:\n{result.stderr[-300:]}")
            return False
        print("  ✅ 后端依赖安装完成")
        return True


def start_backend():
    """启动后端"""
    print(f"\n  🚀 启动后端服务...")
    print(f"  📡 访问地址: http://localhost:8899\n")

    # 切换到 backend 目录，确保路径正确
    os.chdir(BACKEND_DIR)

    import uvicorn
    sys.path.insert(0, BACKEND_DIR)
    from backend.main import app

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8899,
        log_level="info",
    )


def main():
    print("""
╔══════════════════════════════╗
║     🧪 FluxSR Lab           ║
║     一键启动脚本             ║
╚══════════════════════════════╝
""")

    # 1. 检查前端
    print("📦 检查前端环境...")
    frontend_ok = True

    if not os.path.isfile(INDEX_HTML):
        print("  ⚠️  前端未构建")
        if not check_node():
            frontend_ok = False
        elif not check_npm():
            frontend_ok = False
        elif not check_frontend_deps():
            frontend_ok = False
        elif not build_frontend():
            frontend_ok = False
    else:
        print(f"  ✅ 前端已构建 ({os.path.getsize(INDEX_HTML)} bytes)")

    if not frontend_ok:
        print("\n  ❌ 前端准备失败，请手动检查")
        sys.exit(1)

    # 2. 检查后端依赖
    print("\n📦 检查后端环境...")
    if not check_backend_deps():
        print("\n  ❌ 后端依赖安装失败")
        sys.exit(1)

    # 3. 启动
    print("\n" + "=" * 46)
    start_backend()


if __name__ == "__main__":
    main()
