#!/usr/bin/env python3
"""Create a cluster-ready Amber run directory from bundled templates."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = SKILL_DIR / "assets" / "templates"

TEMPLATE_SPECS = {
    "standard-explicit": {
        "stage": "explicit_gpu",
        "submit_script": "run_slurm-4090.sh",
        "topology_name": "complex-amber.top",
        "coordinates_name": "complex-amber.crd",
        "prep_keep": ["leap.in"],
    },
    "implicit-solvent": {
        "stage": "implicit_gpu",
        "submit_script": "run.sh",
        "topology_name": "complex-amber.top",
        "coordinates_name": "complex-amber.crd",
        "prep_keep": ["leap.in"],
    },
    "remd": {
        "stage": "remd_gpu",
        "submit_script": "01equil_gpu.sh",
        "topology_name": "system.prmtop",
        "coordinates_name": "system.inpcrd",
        "prep_keep": [],
    },
    "membrane": {
        "stage": "membrane_gpu",
        "submit_script": "run_4090.sh",
        "topology_name": "input.parm7",
        "coordinates_name": "input.rst7",
        "prep_keep": [],
    },
}


def copy_tree(src: Path, dst: Path) -> None:
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target)
        else:
            shutil.copy2(item, target)


def build_destination(output_root: Path, project: str, stage: str, overwrite: bool) -> Path:
    destination = output_root / f"{project}_{stage}"
    if destination.exists():
        if not overwrite:
            raise FileExistsError(f"{destination} already exists. Use --overwrite to replace it.")
        shutil.rmtree(destination)
    destination.mkdir(parents=True, exist_ok=True)
    return destination


def render_upload_manifest(
    task_dir: Path,
    submit_script: str,
    remote_user: str,
    remote_host: str,
    remote_path: str,
) -> None:
    task_name = task_dir.name
    remote = f"{remote_user}@{remote_host}:{remote_path.rstrip('/')}/"
    task_remote = f"{remote_user}@{remote_host}:{remote_path.rstrip('/')}/{task_name}/"
    content = f"""# 上传与运行说明

## 推荐上传方式

```bash
rsync -avz {task_name}/ {task_remote}
```

也可以：

```bash
scp -r {task_name} {remote}
```

## 在超算上提交

```bash
cd {remote_path.rstrip('/')}/{task_name}
sbatch {submit_script}
```

## 在把目录视为最终版本前

- 先运行 Amber MD Expert 的本地预检查。
- 先汇总时长并和用户确认，再准备提交。
- 如果这是续跑任务，重新检查 `ntx`、`irest` 和输出文件名。
"""
    (task_dir / "UPLOAD_AND_RUN.md").write_text(content, encoding="utf-8")


def copy_inputs(destination: Path, spec: dict[str, object], topology: str | None, coordinates: str | None) -> None:
    if topology:
        shutil.copy2(topology, destination / str(spec["topology_name"]))
    if coordinates:
        shutil.copy2(coordinates, destination / str(spec["coordinates_name"]))


def copy_prep(destination: Path, spec: dict[str, object], prep_files: list[str]) -> None:
    prep_dir = destination / "prep"
    prep_dir.mkdir(exist_ok=True)
    for name in spec["prep_keep"]:
        src = destination / name
        if src.exists():
            shutil.copy2(src, prep_dir / name)
    for prep_file in prep_files:
        path = Path(prep_file).resolve()
        shutil.copy2(path, prep_dir / path.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", help="Project prefix, for example proj1")
    parser.add_argument(
        "--template",
        default="standard-explicit",
        choices=sorted(TEMPLATE_SPECS),
    )
    parser.add_argument("--stage", help="Override the default stage suffix")
    parser.add_argument("--output-root", default=".")
    parser.add_argument("--topology", help="Prepared Amber topology to drop into the bundle")
    parser.add_argument("--coordinates", help="Prepared Amber coordinate or restart file")
    parser.add_argument("--prep-file", action="append", default=[], help="Preparation files to copy into prep/")
    parser.add_argument("--remote-user", default="your_username")
    parser.add_argument("--remote-host", default="your.cluster.edu")
    parser.add_argument("--remote-path", default="~/amber-runs")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    spec = TEMPLATE_SPECS[args.template]
    stage = args.stage or str(spec["stage"])
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    destination = build_destination(output_root, args.project, stage, args.overwrite)

    template_dir = ASSETS_DIR / args.template
    copy_tree(template_dir, destination)
    copy_inputs(destination, spec, args.topology, args.coordinates)
    copy_prep(destination, spec, args.prep_file)
    render_upload_manifest(
        task_dir=destination,
        submit_script=str(spec["submit_script"]),
        remote_user=args.remote_user,
        remote_host=args.remote_host,
        remote_path=args.remote_path,
    )

    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
