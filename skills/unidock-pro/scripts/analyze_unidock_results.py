#!/usr/bin/env python3
"""Analyze UniDock-Pro output files and export a ranked CSV summary."""

from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

ENERGY_PATTERNS = [
    re.compile(r"REMARK\s+VINA\s+RESULT:\s+(-?\d+(?:\.\d+)?)"),
    re.compile(r"mode\s*\|\s*(-?\d+(?:\.\d+)?)\s*\|", re.IGNORECASE),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="解析 UniDock-Pro 结果目录中的 *_out.pdbqt，并导出排序后的 CSV。"
    )
    parser.add_argument("results_dir", type=Path, help="UniDock-Pro 输出目录")
    parser.add_argument(
        "output_csv",
        nargs="?",
        type=Path,
        help="输出 CSV 路径，默认写到 results_dir/docking_results.csv",
    )
    parser.add_argument("--top-n", type=int, default=50, help="终端打印前 N 个结果，默认 50")
    return parser.parse_args()


def extract_energy(content: str) -> float | None:
    for pattern in ENERGY_PATTERNS:
        match = pattern.search(content)
        if match:
            return float(match.group(1))
    return None


def collect_results(results_dir: Path) -> list[dict[str, object]]:
    if not results_dir.exists():
        raise FileNotFoundError(f"结果目录不存在：{results_dir}")
    if not results_dir.is_dir():
        raise NotADirectoryError(f"输入不是目录：{results_dir}")

    output_files = sorted(results_dir.glob("*_out.pdbqt"))
    if not output_files:
        raise FileNotFoundError(f"没有找到 *_out.pdbqt：{results_dir}")

    rows: list[dict[str, object]] = []
    for file_path in output_files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        energy = extract_energy(content)
        if energy is None:
            continue
        rows.append(
            {
                "ligand": file_path.stem.replace("_out", ""),
                "energy_kcal_mol": energy,
                "file": str(file_path.resolve()),
            }
        )

    if not rows:
        raise RuntimeError("找到结果文件，但没有解析出任何结合能")
    return sorted(rows, key=lambda row: float(row["energy_kcal_mol"]))


def write_csv(rows: list[dict[str, object]], output_csv: Path) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "ligand", "energy_kcal_mol", "file"])
        for index, row in enumerate(rows, start=1):
            writer.writerow([index, row["ligand"], f'{row["energy_kcal_mol"]:.3f}', row["file"]])


def print_top(rows: list[dict[str, object]], top_n: int) -> None:
    limit = min(top_n, len(rows))
    print(f"共解析 {len(rows)} 个结果文件")
    print(f"展示前 {limit} 个最佳结合能结果")
    print(f"{'Rank':<6}{'Ligand':<24}{'Energy (kcal/mol)':<20}")
    print("-" * 50)
    for index, row in enumerate(rows[:limit], start=1):
        print(f"{index:<6}{str(row['ligand']):<24}{float(row['energy_kcal_mol']):<20.3f}")


def main() -> int:
    args = parse_args()
    results_dir = args.results_dir.resolve()
    output_csv = (
        args.output_csv.resolve()
        if args.output_csv
        else results_dir / "docking_results.csv"
    )

    rows = collect_results(results_dir)
    write_csv(rows, output_csv)
    print_top(rows, args.top_n)
    print(f"CSV 已写入：{output_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
