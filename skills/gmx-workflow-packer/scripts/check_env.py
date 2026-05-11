#!/usr/bin/env python3
"""Check local dependencies for the GROMACS tREMD/REST2 workflow."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class Dependency:
    name: str
    required_for: tuple[str, ...]
    install_hint: str


DEPENDENCIES = (
    Dependency("gmx", ("all",), "安装 GROMACS 命令行工具，至少保证本地能调用 `gmx`。"),
    Dependency("gmx_mpi", ("bundle", "cluster"), "确认超算模块或本地环境提供 `gmx_mpi`，正式多副本交换默认使用它。"),
    Dependency("perl", ("analysis", "bundle"), "安装 Perl，用于 `demux.pl` 兼容路径。"),
    Dependency("plumed", ("rest2",), "REST2/HREX 默认使用 PLUMED 的 `partial_tempering` 生成缩放拓扑。"),
    Dependency("obabel", ("protein_ligand",), "安装 Open Babel，用于从复合物中拆配体或转换配体格式。"),
    Dependency("acpype", ("protein_ligand",), "安装 ACPYPE，用于配体的 GAFF 参数化。"),
    Dependency("antechamber", ("protein_ligand",), "安装 AmberTools/antechamber，ACPYPE 常依赖它。"),
)


def resolve_required(mode: str) -> set[str]:
    required = {"all", "bundle", "analysis", "cluster"}
    if mode == "protein_ligand":
        required.add("protein_ligand")
    if mode == "rest2":
        required.add("rest2")
    return required


def query_version(executable: str) -> str | None:
    commands: dict[str, list[str]] = {
        "gmx": ["gmx", "--version"],
        "gmx_mpi": ["gmx_mpi", "--version"],
        "plumed": ["plumed", "--version"],
        "obabel": ["obabel", "-V"],
        "acpype": ["acpype", "-h"],
        "antechamber": ["antechamber", "-h"],
        "perl": ["perl", "-v"],
    }
    command = commands.get(executable)
    if command is None:
        return None
    try:
        proc = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None

    text = (proc.stdout or "") + (proc.stderr or "")
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_line or None


def check_dependencies(required_tags: Iterable[str]) -> list[dict[str, object]]:
    active = set(required_tags)
    results: list[dict[str, object]] = []
    for dep in DEPENDENCIES:
        needed = bool(active.intersection(dep.required_for))
        path = shutil.which(dep.name)
        results.append(
            {
                "name": dep.name,
                "needed": needed,
                "found": bool(path),
                "path": path,
                "version": query_version(dep.name) if path else None,
                "install_hint": dep.install_hint,
            }
        )
    return results


def check_hrex_support(gmx_exec: str) -> dict[str, object]:
    try:
        proc = subprocess.run(
            [gmx_exec, "mdrun", "-h"],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "checked": True,
            "ok": False,
            "message": f"无法运行 `{gmx_exec} mdrun -h`: {exc}",
        }

    text = (proc.stdout or "") + (proc.stderr or "")
    has_hrex = "-hrex" in text
    has_plumed = "-plumed" in text
    return {
        "checked": True,
        "ok": bool(has_hrex and has_plumed),
        "has_hrex": has_hrex,
        "has_plumed": has_plumed,
        "message": f"{gmx_exec} mdrun -h: -hrex={has_hrex}, -plumed={has_plumed}",
    }


def render_human(results: list[dict[str, object]], hrex: dict[str, object] | None = None) -> int:
    missing_required = [row for row in results if row["needed"] and not row["found"]]

    print("GROMACS tREMD/REST2 环境检查")
    print("============================")
    for row in results:
        label = "必须" if row["needed"] else "可选"
        status = "已找到" if row["found"] else "缺失"
        print(f"- {row['name']}: {status} ({label})")
        if row["path"]:
            print(f"  路径: {row['path']}")
        if row["version"]:
            print(f"  版本: {row['version']}")
        if row["needed"] and not row["found"]:
            print(f"  建议: {row['install_hint']}")

    hrex_failed = bool(hrex and not hrex.get("ok"))
    if hrex:
        print("\nREST2/HREX 兼容性检查")
        print(f"- {hrex['message']}")
        if hrex_failed:
            print("  建议: 在超算模块中确认 GROMACS 已用 PLUMED patch，且 `mdrun -h` 列出 `-hrex` 与 `-plumed`。")

    if missing_required or hrex_failed:
        print("\n结论: 当前环境还不能完整支持所选路径。")
        return 1

    print("\n结论: 当前环境满足所选路径的必要依赖。")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 gmx-workflow-packer 的本地依赖。")
    parser.add_argument(
        "--mode",
        choices=("standard_protein", "protein_ligand", "rest2"),
        default="standard_protein",
        help="按工作流路径决定是否检查 REST2 或配体参数化依赖。",
    )
    parser.add_argument(
        "--check-hrex",
        action="store_true",
        help="额外运行 `gmx_mpi mdrun -h`，检查当前 GROMACS 是否支持 `-hrex` 与 `-plumed`。",
    )
    parser.add_argument(
        "--gmx-exec",
        default="gmx_mpi",
        help="用于 --check-hrex 的 GROMACS MPI 可执行入口。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 结果，方便脚本消费。",
    )
    args = parser.parse_args()

    required_tags = resolve_required(args.mode)
    results = check_dependencies(required_tags)
    hrex = check_hrex_support(args.gmx_exec) if args.check_hrex else None

    if args.json:
        payload: dict[str, object] = {"dependencies": results}
        if hrex:
            payload["hrex"] = hrex
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        missing = any(row["needed"] and not row["found"] for row in results)
        return 1 if missing or bool(hrex and not hrex.get("ok")) else 0

    return render_human(results, hrex=hrex)


if __name__ == "__main__":
    sys.exit(main())
