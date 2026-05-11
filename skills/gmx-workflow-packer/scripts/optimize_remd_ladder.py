#!/usr/bin/env python3
"""Generate an initial GROMACS temperature ladder for tREMD."""

from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path

import yaml


def clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def acceptance_scale(target_acceptance: float) -> float:
    """Map a desired exchange acceptance to an empirical spacing scale."""
    target = clamp(target_acceptance, 0.15, 0.40)
    # Higher target acceptance needs a tighter spacing.
    return 1.95 - 2.0 * (target - 0.20)


def estimate_relative_gap(protein_atoms: int, water_molecules: int, target_acceptance: float) -> float:
    effective_size = max(1.0, protein_atoms + 36.0 * water_molecules)
    scale = acceptance_scale(target_acceptance)
    gap = scale / math.sqrt(effective_size)
    return clamp(gap, 0.0015, 0.0200)


def generate_geometric_ladder(tmin: float, tmax: float, relative_gap: float) -> list[float]:
    if tmin <= 0 or tmax <= tmin:
        raise ValueError("温度区间无效，必须满足 tmax > tmin > 0。")

    replicas = math.ceil(math.log(tmax / tmin) / math.log(1.0 + relative_gap)) + 1
    ladder = [tmin]
    if replicas <= 2:
        return [round(tmin, 2), round(tmax, 2)]

    ratio = (tmax / tmin) ** (1.0 / (replicas - 1))
    for index in range(1, replicas - 1):
        ladder.append(tmin * (ratio**index))
    ladder.append(tmax)
    return [round(value, 2) for value in ladder]


def estimate_ladder(
    tmin: float,
    tmax: float,
    protein_atoms: int,
    water_molecules: int,
    target_acceptance: float,
) -> dict[str, object]:
    relative_gap = estimate_relative_gap(protein_atoms, water_molecules, target_acceptance)
    temperatures = generate_geometric_ladder(tmin, tmax, relative_gap)
    deltas = [round(temperatures[idx] - temperatures[idx - 1], 2) for idx in range(1, len(temperatures))]
    ratios = [
        round(temperatures[idx] / temperatures[idx - 1], 6)
        for idx in range(1, len(temperatures))
    ]
    return {
        "tmin": round(tmin, 2),
        "tmax": round(tmax, 2),
        "protein_atoms": protein_atoms,
        "water_molecules": water_molecules,
        "target_acceptance": round(target_acceptance, 3),
        "relative_gap_estimate": round(relative_gap, 6),
        "n_replicas": len(temperatures),
        "temperatures": temperatures,
        "deltas": deltas,
        "ratios": ratios,
        "note": "这是经验初值，建议先短跑后检查交换率与 round-trip。",
    }


def write_outputs(result: dict[str, object], outdir: Path, prefix: str) -> tuple[Path, Path, Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    yaml_path = outdir / f"{prefix}.yaml"
    csv_path = outdir / f"{prefix}.csv"
    summary_path = outdir / f"{prefix}.md"

    yaml_path.write_text(yaml.safe_dump(result, allow_unicode=True, sort_keys=False))

    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["replica", "temperature_k", "delta_from_previous_k", "ratio_from_previous"])
        temperatures = result["temperatures"]
        deltas = [None] + result["deltas"]
        ratios = [None] + result["ratios"]
        for index, temp in enumerate(temperatures):
            writer.writerow([index, temp, deltas[index], ratios[index]])

    summary = [
        "# 温度梯度建议",
        "",
        f"- 温区: {result['tmin']} K -> {result['tmax']} K",
        f"- 估算副本数: {result['n_replicas']}",
        f"- 目标交换率: {result['target_acceptance']}",
        f"- 经验相对温差: {result['relative_gap_estimate']}",
        "- 说明: 这是经验初值，建议先短跑检查实际交换率。",
        "",
        "## 温度列表",
        "",
    ]
    for index, temp in enumerate(result["temperatures"]):
        summary.append(f"- replica_{index:02d}: {temp:.2f} K")
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")

    return yaml_path, csv_path, summary_path


def main() -> int:
    parser = argparse.ArgumentParser(description="估算 GROMACS tREMD 温度梯度。")
    parser.add_argument("--tmin", type=float, required=True)
    parser.add_argument("--tmax", type=float, required=True)
    parser.add_argument("--protein-atoms", type=int, required=True)
    parser.add_argument("--water-molecules", type=int, required=True)
    parser.add_argument("--target-acceptance", type=float, default=0.25)
    parser.add_argument("--outdir", type=Path, default=Path("."))
    parser.add_argument("--prefix", default="temperatures")
    args = parser.parse_args()

    result = estimate_ladder(
        tmin=args.tmin,
        tmax=args.tmax,
        protein_atoms=args.protein_atoms,
        water_molecules=args.water_molecules,
        target_acceptance=args.target_acceptance,
    )
    yaml_path, csv_path, summary_path = write_outputs(result, args.outdir, args.prefix)

    print("已生成温度梯度建议:")
    print(f"- YAML: {yaml_path}")
    print(f"- CSV: {csv_path}")
    print(f"- 简报: {summary_path}")
    print(f"- 副本数: {result['n_replicas']}")
    print(f"- 温度范围: {result['tmin']} -> {result['tmax']} K")
    return 0


if __name__ == "__main__":
    sys.exit(main())
