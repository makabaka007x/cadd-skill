#!/usr/bin/env python3
"""Generate a stable UniDock-Pro ligand index from a directory of PDBQT files."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从配体目录生成 UniDock-Pro 可用的 ligand_index.txt。默认写入绝对路径。"
    )
    parser.add_argument("ligand_dir", type=Path, help="包含 .pdbqt 配体文件的目录")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=Path("ligand_index.txt"),
        help="输出索引文件路径，默认是当前目录下的 ligand_index.txt",
    )
    parser.add_argument(
        "--relative-to-index",
        action="store_true",
        help="把路径写成相对 output 文件所在目录的相对路径；默认写绝对路径",
    )
    return parser.parse_args()


def collect_ligands(ligand_dir: Path) -> list[Path]:
    if not ligand_dir.exists():
        raise FileNotFoundError(f"配体目录不存在：{ligand_dir}")
    if not ligand_dir.is_dir():
        raise NotADirectoryError(f"输入不是目录：{ligand_dir}")

    ligands = sorted(
        (path for path in ligand_dir.iterdir() if path.is_file() and path.suffix == ".pdbqt"),
        key=lambda path: path.name,
    )
    if not ligands:
        raise FileNotFoundError(f"目录中没有找到 .pdbqt 文件：{ligand_dir}")
    return ligands


def render_paths(ligands: list[Path], output_path: Path, relative_to_index: bool) -> list[str]:
    if not relative_to_index:
        return [str(path.resolve()) for path in ligands]

    base_dir = output_path.parent.resolve()
    return [os.path.relpath(path.resolve(), start=base_dir) for path in ligands]


def main() -> int:
    args = parse_args()
    ligand_dir = args.ligand_dir.resolve()
    output_path = args.output.resolve()

    ligands = collect_ligands(ligand_dir)
    lines = render_paths(ligands, output_path, args.relative_to_index)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"已收集 {len(ligands)} 个配体")
    print(f"输入目录：{ligand_dir}")
    print(f"输出文件：{output_path}")
    print(
        "路径模式："
        + ("相对 output 文件目录" if args.relative_to_index else "绝对路径")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
