#!/usr/bin/env python3
"""Validate a Foundry/RFdiffusion3 environment."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], timeout: int = 120) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            cmd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        return 127, f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s: {' '.join(cmd)}"
    return proc.returncode, proc.stdout.strip()


def status(label: str, ok: bool, detail: str = "") -> bool:
    tag = "OK" if ok else "FAIL"
    print(f"[{tag}] {label}" + (f": {detail}" if detail else ""))
    return ok


def warn(label: str, detail: str = "") -> None:
    print(f"[WARN] {label}" + (f": {detail}" if detail else ""))


def module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def check_torch(require_gpu: bool) -> bool:
    try:
        import torch
    except Exception as exc:  # pragma: no cover - diagnostic script
        return status("import torch", False, repr(exc))

    ok = True
    print(f"[INFO] torch version: {torch.__version__}")
    print(f"[INFO] torch CUDA runtime: {torch.version.cuda}")
    cuda_ok = bool(torch.cuda.is_available())
    ok &= status("torch CUDA available", cuda_ok or not require_gpu, str(cuda_ok))
    if cuda_ok:
        try:
            print(f"[INFO] CUDA device count: {torch.cuda.device_count()}")
            print(f"[INFO] CUDA device 0: {torch.cuda.get_device_name(0)}")
            x = torch.randn(256, 256, device="cuda")
            y = x @ x.T
            ok &= status("GPU tensor smoke test", y.is_cuda, f"shape={tuple(y.shape)}")
        except Exception as exc:  # pragma: no cover - diagnostic script
            ok &= status("GPU tensor smoke test", False, repr(exc))
    elif require_gpu:
        warn("GPU unavailable", "RFD3 can run on CPU, but practical design jobs usually require a compatible CUDA GPU")
    return ok


def ensure_env_bin_on_path() -> None:
    env_bin = Path(sys.executable).resolve().parent
    path_parts = os.environ.get("PATH", "").split(os.pathsep)
    if str(env_bin) not in path_parts:
        os.environ["PATH"] = str(env_bin) + os.pathsep + os.environ.get("PATH", "")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint-dir",
        default=os.environ.get("FOUNDRY_CHECKPOINT_DIRS", "").split(":")[0],
        help="Foundry checkpoint directory to validate.",
    )
    parser.add_argument(
        "--allow-non-312",
        action="store_true",
        help="Do not fail when Python is not 3.12.",
    )
    parser.add_argument(
        "--skip-gpu",
        action="store_true",
        help="Do not require torch.cuda.is_available().",
    )
    parser.add_argument(
        "--no-list-installed",
        action="store_true",
        help="Skip `foundry list-installed`.",
    )
    args = parser.parse_args()

    ensure_env_bin_on_path()

    ok = True
    print(f"[INFO] executable: {sys.executable}")
    print(f"[INFO] python: {sys.version.split()[0]}")
    py312 = sys.version_info[:2] == (3, 12)
    ok &= status("Python 3.12", py312 or args.allow_non_312, sys.version.split()[0])

    code, out = run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total", "--format=csv,noheader"], timeout=20)
    if code == 0:
        print(f"[INFO] nvidia-smi: {out}")
    else:
        warn("nvidia-smi unavailable", out)

    ok &= check_torch(require_gpu=not args.skip_gpu)

    for module in ["foundry", "rfd3", "rf3", "mpnn"]:
        ok &= status(f"importable module {module}", module_exists(module))

    for cli in ["foundry", "rfd3", "rf3", "mpnn"]:
        cli_path = shutil.which(cli)
        ok &= status(f"CLI {cli}", cli_path is not None, cli_path or "not found")

    checkpoint_dir = Path(args.checkpoint_dir).expanduser() if args.checkpoint_dir else None
    if checkpoint_dir:
        os.environ["FOUNDRY_CHECKPOINT_DIRS"] = str(checkpoint_dir)
        ok &= status("checkpoint dir exists", checkpoint_dir.exists(), str(checkpoint_dir))
        if checkpoint_dir.exists() and not any(checkpoint_dir.iterdir()):
            warn("checkpoint dir is empty", str(checkpoint_dir))
    else:
        warn("checkpoint dir not provided", "pass --checkpoint-dir or set FOUNDRY_CHECKPOINT_DIRS")

    if not args.no_list_installed and shutil.which("foundry"):
        code, out = run(["foundry", "list-installed"], timeout=120)
        ok &= status("foundry list-installed", code == 0, out[-1000:] if out else "")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
