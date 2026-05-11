#!/usr/bin/env python3
"""Validate a packaged Amber task directory."""

from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path


FILE_FLAGS = {"-i", "-p", "-c", "-ref"}


def parse_submit_steps(script_path: Path) -> list[dict[str, str]]:
    steps: list[dict[str, str]] = []
    for line in script_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "pmemd" not in stripped and "sander" not in stripped:
            continue
        tokens = shlex.split(stripped)
        mapping: dict[str, str] = {"command": stripped}
        for index, token in enumerate(tokens[:-1]):
            if token in FILE_FLAGS or token in {"-o", "-r", "-x"}:
                mapping[token] = tokens[index + 1]
        steps.append(mapping)
    return steps


def parse_in_file(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    params: dict[str, str] = {}
    for key in ("nstlim", "dt", "ntx", "irest"):
        match = re.search(rf"\b{key}\s*=\s*([^,\n/]+)", text)
        if match:
            params[key] = match.group(1).strip()
    return params


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--submit-script", default="run_slurm-4090.sh")
    args = parser.parse_args()

    task_dir = args.task_dir.resolve()
    script_path = task_dir / args.submit_script
    if not script_path.exists():
        print(f"ERROR: submit script not found: {script_path}")
        return 1

    steps = parse_submit_steps(script_path)
    if not steps:
        print(f"ERROR: no Amber run steps found in {script_path.name}")
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    produced = {path.name for path in task_dir.iterdir() if path.is_file()}

    for step in steps:
        for flag in ("-i", "-p", "-c", "-ref"):
            value = step.get(flag)
            if not value:
                continue
            if value not in produced:
                errors.append(f"Missing input referenced by {step['command']}: {value}")
        in_file = step.get("-i")
        if in_file:
            params = parse_in_file(task_dir / in_file)
            ntx = params.get("ntx")
            irest = params.get("irest")
            if irest == "1" and ntx != "5":
                warnings.append(f"{in_file}: irest=1 usually expects ntx=5 (found {ntx})")
        for flag in ("-o", "-r", "-x"):
            value = step.get(flag)
            if value:
                produced.add(value)

    if errors:
        print("Validation failed:")
        for item in errors:
            print(f"- {item}")
        for item in warnings:
            print(f"WARNING: {item}")
        return 1

    print("Validation passed.")
    for item in warnings:
        print(f"WARNING: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
