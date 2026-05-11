#!/usr/bin/env python3
"""Summarize Amber stage times from input files."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


STAGE_ORDER = [
    "min1.in",
    "min2.in",
    "min3.in",
    "heat.in",
    "nvt.in",
    "npt1.in",
    "npt2.in",
    "npt3.in",
    "npt4.in",
    "md.in",
]


def parse_params(path: Path) -> dict[str, float]:
    text = path.read_text(encoding="utf-8")
    params: dict[str, float] = {}
    for key in ("nstlim", "dt", "maxcyc", "ncyc"):
        match = re.search(rf"\b{key}\s*=\s*([^,\n/]+)", text)
        if match:
            try:
                params[key] = float(match.group(1).strip())
            except ValueError:
                continue
    return params


def humanize_ps(value_ps: float) -> str:
    if value_ps >= 1_000_000:
        return f"{value_ps / 1_000_000:.2f} us"
    if value_ps >= 1_000:
        return f"{value_ps / 1_000:.2f} ns"
    return f"{value_ps:.2f} ps"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    args = parser.parse_args()

    task_dir = args.task_dir.resolve()
    total_ps = 0.0

    print("Stage\tHuman Time\tAmber Params")
    for name in STAGE_ORDER:
        path = task_dir / name
        if not path.exists():
            continue
        params = parse_params(path)
        if "nstlim" in params and "dt" in params:
            stage_ps = params["nstlim"] * params["dt"]
            total_ps += stage_ps
            amber_view = f"nstlim={int(params['nstlim'])}, dt={params['dt']}"
            print(f"{name}\t{humanize_ps(stage_ps)}\t{amber_view}")
        elif "maxcyc" in params:
            amber_view = f"maxcyc={int(params['maxcyc'])}"
            if "ncyc" in params:
                amber_view += f", ncyc={int(params['ncyc'])}"
            print(f"{name}\tminimization\t{amber_view}")

    if total_ps:
        print(f"TOTAL_MD\t{humanize_ps(total_ps)}\tMD stages only")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
