#!/usr/bin/env python3
"""Generate on-demand Amber analysis bundles."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = SKILL_DIR / "assets" / "templates"


def copy_tree(src: Path, dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def generate_minimal(output_dir: Path, topology: str, trajectory: str, job_name: str) -> None:
    template_dir = ASSETS_DIR / "analysis-minimal"
    analysis_sh = (template_dir / "analysis.sh.template").read_text(encoding="utf-8")
    cpptraj_in = (template_dir / "cpptraj.in.template").read_text(encoding="utf-8")

    replacements = {
        "__TOPOLOGY__": topology,
        "__TRAJECTORY__": trajectory,
        "__JOB_NAME__": job_name,
    }
    for key, value in replacements.items():
        analysis_sh = analysis_sh.replace(key, value)
        cpptraj_in = cpptraj_in.replace(key, value)

    (output_dir / "analysis.sh").write_text(analysis_sh, encoding="utf-8")
    (output_dir / "cpptraj.in").write_text(cpptraj_in, encoding="utf-8")
    (output_dir / "analysis.sh").chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--mode", action="append", choices=["minimal", "contact", "dsspplot"], default=["minimal"])
    parser.add_argument("--analysis-dir", default="analysis")
    parser.add_argument("--topology", default="complex-amber.top")
    parser.add_argument("--trajectory", default="md.trj")
    parser.add_argument("--job-name", default="amber-analysis")
    args = parser.parse_args()

    task_dir = args.task_dir.resolve()
    output_dir = task_dir / args.analysis_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    modes = list(dict.fromkeys(args.mode))
    if "minimal" in modes:
        generate_minimal(output_dir, args.topology, args.trajectory, args.job_name)
    if "contact" in modes:
        copy_tree(ASSETS_DIR / "contact", output_dir / "contact")
    if "dsspplot" in modes:
        copy_tree(ASSETS_DIR / "dsspplot", output_dir / "dsspplot")

    print(output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
