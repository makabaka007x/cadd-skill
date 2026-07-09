#!/usr/bin/env python3
"""Run UniDock-Pro cases with mode-aware validation and local environment detection."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_REPO_ROOT = Path("/path/to/UniDock-Pro")
DEFAULT_ENV_PREFIX = Path("/path/to/conda-envs/unidock-pro")
DEFAULT_CONDA_SH = Path.home() / "miniconda3" / "etc" / "profile.d" / "conda.sh"
DEFAULT_CUDA_HOME = Path("/usr/local/cuda")
VALID_SEARCH_MODES = {
    "fast": "fast",
    "balance": "balance",
    "balanced": "balance",
    "detail": "detail",
    "detailed": "detail",
}


class ValidationError(Exception):
    """Raised when the user-supplied run configuration is inconsistent."""


@dataclass
class Launcher:
    name: str
    detail: str
    preview_command: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="运行 UniDock-Pro，并自动选择最稳妥的环境调用方式。"
    )
    parser.add_argument(
        "--mode",
        required=True,
        choices=["docking", "similarity", "hybrid"],
        help="运行模式：纯 docking、相似性搜索或 hybrid",
    )
    parser.add_argument("--receptor", type=Path, help="受体 PDBQT 路径")
    parser.add_argument(
        "--reference-ligand",
        nargs="+",
        type=Path,
        help="参考配体 PDBQT 路径，可传多个文件",
    )
    parser.add_argument("--ligand-index", type=Path, help="ligand_index.txt 路径")
    parser.add_argument("--ligand-dir", type=Path, help="包含 .pdbqt 的配体目录")
    parser.add_argument("--center-x", required=True, type=float, help="搜索框中心 X")
    parser.add_argument("--center-y", required=True, type=float, help="搜索框中心 Y")
    parser.add_argument("--center-z", required=True, type=float, help="搜索框中心 Z")
    parser.add_argument("--size-x", required=True, type=float, help="搜索框尺寸 X")
    parser.add_argument("--size-y", required=True, type=float, help="搜索框尺寸 Y")
    parser.add_argument("--size-z", required=True, type=float, help="搜索框尺寸 Z")
    parser.add_argument(
        "--search-mode",
        required=True,
        choices=sorted(VALID_SEARCH_MODES.keys()),
        help="推荐使用 fast、balance、detail；源码也接受 balanced、detailed",
    )
    parser.add_argument("--output-dir", required=True, type=Path, help="输出目录")
    parser.add_argument("--max-gpu-memory", type=int, help="可选，单位 MB；0 表示尽量使用全部显存")
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT, help="UniDock-Pro 仓库根目录")
    parser.add_argument(
        "--env-prefix",
        type=Path,
        default=DEFAULT_ENV_PREFIX,
        help="回退用的 conda 环境前缀路径",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只打印最终命令和环境选择，不真正执行",
    )
    return parser.parse_args()


def normalize_search_mode(raw_mode: str) -> str:
    key = raw_mode.lower()
    if key not in VALID_SEARCH_MODES:
        raise ValidationError(f"不支持的 search mode：{raw_mode}")
    return VALID_SEARCH_MODES[key]


def ensure_existing_file(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise ValidationError(f"{label} 不存在：{resolved}")
    if not resolved.is_file():
        raise ValidationError(f"{label} 不是文件：{resolved}")
    return resolved


def ensure_existing_dir(path: Path, label: str) -> Path:
    resolved = path.resolve()
    if not resolved.exists():
        raise ValidationError(f"{label} 不存在：{resolved}")
    if not resolved.is_dir():
        raise ValidationError(f"{label} 不是目录：{resolved}")
    return resolved


def validate_inputs(args: argparse.Namespace) -> tuple[Path | None, list[Path], Path | None, Path | None, str]:
    normalized_search_mode = normalize_search_mode(args.search_mode)

    receptor = ensure_existing_file(args.receptor, "受体文件") if args.receptor else None
    reference_ligands = (
        [ensure_existing_file(path, "参考配体文件") for path in args.reference_ligand]
        if args.reference_ligand
        else []
    )

    if args.mode == "docking":
        if receptor is None:
            raise ValidationError("docking 模式必须提供 --receptor")
        if reference_ligands:
            raise ValidationError("docking 模式不能提供 --reference-ligand")
    elif args.mode == "similarity":
        if receptor is not None:
            raise ValidationError("similarity 模式不能提供 --receptor")
        if not reference_ligands:
            raise ValidationError("similarity 模式必须提供 --reference-ligand")
    elif args.mode == "hybrid":
        if receptor is None:
            raise ValidationError("hybrid 模式必须提供 --receptor")
        if not reference_ligands:
            raise ValidationError("hybrid 模式必须提供 --reference-ligand")

    if bool(args.ligand_index) == bool(args.ligand_dir):
        raise ValidationError("必须且只能提供一种配体来源：--ligand-index 或 --ligand-dir")

    ligand_index = ensure_existing_file(args.ligand_index, "配体索引文件") if args.ligand_index else None
    ligand_dir = ensure_existing_dir(args.ligand_dir, "配体目录") if args.ligand_dir else None

    if ligand_index is not None:
        lines = [line.strip() for line in ligand_index.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            raise ValidationError(f"配体索引为空：{ligand_index}")

    if ligand_dir is not None:
        pdbqt_files = sorted(ligand_dir.glob("*.pdbqt"))
        if not pdbqt_files:
            raise ValidationError(f"配体目录里没有 .pdbqt 文件：{ligand_dir}")

    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        print(f"[WARN] 输出目录已经有内容：{output_dir}")
        print("[WARN] 请确认不会把不同任务的结果混在一起。")

    return receptor, reference_ligands, ligand_index, ligand_dir, normalized_search_mode


def quote_command(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


def build_udp_command(
    binary_path: Path,
    receptor: Path | None,
    reference_ligands: list[Path],
    ligand_index: Path | None,
    ligand_dir: Path | None,
    normalized_search_mode: str,
    output_dir: Path,
    args: argparse.Namespace,
) -> list[str]:
    command = [str(binary_path.resolve())]

    if receptor is not None:
        command.extend(["--receptor", str(receptor)])
    if reference_ligands:
        command.append("--reference_ligand")
        command.extend(str(path) for path in reference_ligands)
    if ligand_index is not None:
        command.extend(["--ligand_index", str(ligand_index)])
    if ligand_dir is not None:
        command.extend(["--ligand_dir", str(ligand_dir)])

    command.extend(
        [
            "--center_x",
            f"{args.center_x:g}",
            "--center_y",
            f"{args.center_y:g}",
            "--center_z",
            f"{args.center_z:g}",
            "--size_x",
            f"{args.size_x:g}",
            "--size_y",
            f"{args.size_y:g}",
            "--size_z",
            f"{args.size_z:g}",
            "--search_mode",
            normalized_search_mode,
            "--dir",
            str(output_dir),
        ]
    )

    if args.max_gpu_memory is not None:
        command.extend(["--max_gpu_memory", str(args.max_gpu_memory)])
    return command


def probe_direct(binary_path: Path) -> bool:
    if not binary_path.exists() or not os.access(binary_path, os.X_OK):
        return False
    result = subprocess.run(
        [str(binary_path), "--help"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=20,
    )
    return result.returncode == 0


def probe_conda_name(binary_path: Path) -> bool:
    if not DEFAULT_CONDA_SH.exists() or not binary_path.exists():
        return False
    shell_command = (
        f"source {shlex.quote(str(DEFAULT_CONDA_SH))} "
        f"&& conda activate unidock-pro "
        f"&& {shlex.quote(str(binary_path))} --help >/dev/null 2>&1"
    )
    result = subprocess.run(["bash", "-lc", shell_command], check=False, timeout=20)
    return result.returncode == 0


def build_prefix_env(env_prefix: Path) -> dict[str, str]:
    env = os.environ.copy()
    path_parts = [str(env_prefix / "bin"), env.get("PATH", "")]
    library_parts = [str(env_prefix / "lib"), env.get("LD_LIBRARY_PATH", "")]
    if DEFAULT_CUDA_HOME.exists():
        path_parts.insert(0, str(DEFAULT_CUDA_HOME / "bin"))
        library_parts.insert(0, str(DEFAULT_CUDA_HOME / "lib64"))
        env["CUDA_HOME"] = str(DEFAULT_CUDA_HOME)
    env["PATH"] = ":".join(part for part in path_parts if part)
    env["LD_LIBRARY_PATH"] = ":".join(part for part in library_parts if part)
    return env


def probe_env_prefix(binary_path: Path, env_prefix: Path) -> bool:
    if not binary_path.exists() or not env_prefix.exists():
        return False
    result = subprocess.run(
        [str(binary_path), "--help"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=20,
        env=build_prefix_env(env_prefix),
    )
    return result.returncode == 0


def select_launcher(binary_path: Path, env_prefix: Path) -> Launcher:
    if probe_direct(binary_path):
        return Launcher(
            name="direct_binary",
            detail="直接运行 build/udp",
            preview_command=str(binary_path.resolve()),
        )

    if probe_conda_name(binary_path):
        return Launcher(
            name="conda_activate",
            detail="通过 conda activate unidock-pro 运行",
            preview_command=(
                f"source {shlex.quote(str(DEFAULT_CONDA_SH))} && "
                f"conda activate unidock-pro && {shlex.quote(str(binary_path.resolve()))}"
            ),
        )

    if probe_env_prefix(binary_path, env_prefix):
        return Launcher(
            name="env_prefix",
            detail=f"通过环境前缀 {env_prefix.resolve()} 回退运行",
            preview_command=str(binary_path.resolve()),
        )

    raise ValidationError(
        "没有找到可运行的 UniDock-Pro 调用方式。请先确认 build/udp 存在，"
        "或执行 `conda activate unidock-pro && cmake -B build && cmake --build build -j$(nproc)` 重新构建。"
    )


def write_summary(
    output_dir: Path,
    launcher: Launcher,
    command: list[str],
    args: argparse.Namespace,
    normalized_search_mode: str,
    returncode: int | None,
    started_at: float,
    finished_at: float | None,
) -> None:
    summary = {
        "mode": args.mode,
        "launcher": launcher.name,
        "launcher_detail": launcher.detail,
        "repo_root": str(args.repo_root.resolve()),
        "env_prefix": str(args.env_prefix.resolve()),
        "command": command,
        "quoted_command": quote_command(command),
        "search_mode_input": args.search_mode,
        "search_mode_effective": normalized_search_mode,
        "output_dir": str(output_dir.resolve()),
        "returncode": returncode,
        "started_at_epoch": started_at,
        "finished_at_epoch": finished_at,
        "duration_seconds": None if finished_at is None else round(finished_at - started_at, 3),
    }
    summary_path = output_dir / "run-summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_command(command: list[str], launcher: Launcher, env_prefix: Path) -> int:
    if launcher.name == "direct_binary":
        return subprocess.run(command, check=False).returncode

    if launcher.name == "conda_activate":
        shell_command = (
            f"source {shlex.quote(str(DEFAULT_CONDA_SH))} && "
            f"conda activate unidock-pro && exec {quote_command(command)}"
        )
        return subprocess.run(["bash", "-lc", shell_command], check=False).returncode

    if launcher.name == "env_prefix":
        return subprocess.run(command, env=build_prefix_env(env_prefix), check=False).returncode

    raise RuntimeError(f"未知 launcher：{launcher.name}")


def main() -> int:
    args = parse_args()

    try:
        receptor, reference_ligands, ligand_index, ligand_dir, normalized_search_mode = validate_inputs(args)
    except ValidationError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    binary_path = (args.repo_root / "build" / "udp").resolve()
    if not binary_path.exists():
        print(f"[ERROR] UniDock-Pro 二进制不存在：{binary_path}", file=sys.stderr)
        print("请先在 UniDock-Pro 仓库中构建 `build/udp`。", file=sys.stderr)
        return 2

    try:
        launcher = select_launcher(binary_path, args.env_prefix.resolve())
    except ValidationError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    output_dir = args.output_dir.resolve()
    command = build_udp_command(
        binary_path,
        receptor,
        reference_ligands,
        ligand_index,
        ligand_dir,
        normalized_search_mode,
        output_dir,
        args,
    )

    print("==========================================")
    print("UniDock-Pro 运行计划")
    print("==========================================")
    print(f"模式：{args.mode}")
    print(f"运行方式：{launcher.detail}")
    print(f"仓库：{args.repo_root.resolve()}")
    print(f"输出目录：{output_dir}")
    print(f"search_mode：{args.search_mode} -> {normalized_search_mode}")
    if receptor is not None:
        print(f"受体：{receptor}")
    if reference_ligands:
        print("参考配体：")
        for ref in reference_ligands:
            print(f"  - {ref}")
    if ligand_index is not None:
        print(f"配体索引：{ligand_index}")
    if ligand_dir is not None:
        print(f"配体目录：{ligand_dir}")
    print("最终命令：")
    print(quote_command(command))
    print("==========================================")
    sys.stdout.flush()

    started_at = time.time()
    write_summary(output_dir, launcher, command, args, normalized_search_mode, None, started_at, None)

    if args.dry_run:
        print("[DRY-RUN] 未执行实际 docking。")
        write_summary(output_dir, launcher, command, args, normalized_search_mode, 0, started_at, time.time())
        return 0

    returncode = run_command(command, launcher, args.env_prefix.resolve())
    finished_at = time.time()
    write_summary(
        output_dir,
        launcher,
        command,
        args,
        normalized_search_mode,
        returncode,
        started_at,
        finished_at,
    )

    if returncode != 0:
        print(f"[ERROR] UniDock-Pro 运行失败，返回码：{returncode}", file=sys.stderr)
        return returncode

    print("运行完成。")
    print(f"运行摘要：{output_dir / 'run-summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
