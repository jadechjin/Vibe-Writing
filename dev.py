#!/usr/bin/env python3
"""一键启动/停止开发环境。

用法:
  python dev.py          # 启动全部（基础设施 + 后端 + 前端）
  python dev.py stop     # 停止全部
  python dev.py infra    # 仅启动基础设施
  python dev.py backend  # 仅启动后端
  python dev.py frontend # 仅启动前端
"""

import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent
FRONTEND = ROOT / "frontend"
BACKEND = ROOT / "backend"
INFRA = ROOT / "infra" / "docker-compose.yml"
ENV_FILE = FRONTEND / ".env.local"
ENV_EXAMPLE = FRONTEND / ".env.example"

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

_procs: list[subprocess.Popen] = []


def log(msg: str) -> None:
    print(f"\033[36m[dev]\033[0m {msg}", flush=True)


def err(msg: str) -> None:
    print(f"\033[31m[dev]\033[0m {msg}", flush=True)


def ok(msg: str) -> None:
    print(f"\033[32m[dev]\033[0m {msg}", flush=True)


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> int:
    result = subprocess.run(cmd, cwd=cwd)
    if check and result.returncode != 0:
        err(f"命令失败: {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result.returncode


def spawn(cmd: list[str], cwd: Path | None = None, label: str = "") -> subprocess.Popen:
    log(f"启动 {label or ' '.join(cmd[:2])}")
    proc = subprocess.Popen(cmd, cwd=cwd)
    _procs.append(proc)
    return proc


def shutdown(sig=None, frame=None) -> None:
    log("正在停止所有进程...")
    for p in _procs:
        try:
            p.terminate()
        except Exception:
            pass
    for p in _procs:
        try:
            p.wait(timeout=5)
        except Exception:
            p.kill()
    log("已停止。")
    sys.exit(0)


def ensure_env() -> None:
    if not ENV_FILE.exists() and ENV_EXAMPLE.exists():
        shutil.copy(ENV_EXAMPLE, ENV_FILE)
        log(f"已从 .env.example 创建 {ENV_FILE.name}")


def start_infra() -> None:
    log("启动基础设施（PostgreSQL / Redis / MinIO / Temporal）...")
    run(["docker", "compose", "-f", str(INFRA), "up", "-d"])
    log("等待 PostgreSQL 就绪...")
    _wait_for_port("localhost", 5432, timeout=30)
    ok("基础设施已启动")


def _wait_for_port(host: str, port: int, timeout: int = 30) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(1)
    err(f"等待 {host}:{port} 超时（{timeout}s）")
    sys.exit(1)


def run_migrations() -> None:
    log("运行数据库迁移...")
    run(["python", "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=BACKEND)
    ok("迁移完成")


def install_backend() -> None:
    if not (BACKEND / "thesis_workflow_backend.egg-info").exists():
        log("安装后端依赖...")
        run([sys.executable, "-m", "pip", "install", "-e", ".[dev]", "-q"], cwd=BACKEND)


def install_frontend() -> None:
    if not (FRONTEND / "node_modules").exists():
        log("安装前端依赖...")
        npm = shutil.which("npm") or "npm"
        run([npm, "install"], cwd=FRONTEND)


def start_backend() -> subprocess.Popen:
    install_backend()
    run_migrations()
    return spawn(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(BACKEND), "--reload",
         "--host", "0.0.0.0", "--port", "8000"],
        label="后端 FastAPI :8000",
    )


def start_frontend() -> subprocess.Popen:
    install_frontend()
    ensure_env()
    npm = shutil.which("npm") or "npm"
    return spawn([npm, "run", "dev"], cwd=FRONTEND, label="前端 Next.js :3000")


def stop_infra() -> None:
    log("停止基础设施...")
    run(["docker", "compose", "-f", str(INFRA), "down"], check=False)
    ok("基础设施已停止")


def wait_and_print_urls() -> None:
    time.sleep(2)
    ok("服务已启动：")
    print(f"  后端 API  → {BACKEND_URL}/api")
    print(f"  前端      → {FRONTEND_URL}")
    print(f"  API 文档  → {BACKEND_URL}/docs")
    print("\n按 Ctrl+C 停止所有服务\n")


def main() -> None:
    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"

    if cmd == "stop":
        stop_infra()
        return

    if cmd in ("all", "infra"):
        start_infra()

    if cmd == "infra":
        return

    if cmd in ("all", "backend"):
        start_backend()

    if cmd in ("all", "frontend"):
        start_frontend()

    if cmd not in ("all", "backend", "frontend", "infra"):
        err(f"未知命令: {cmd}")
        print(__doc__)
        sys.exit(1)

    wait_and_print_urls()

    # 等待子进程退出
    try:
        for p in _procs:
            p.wait()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
