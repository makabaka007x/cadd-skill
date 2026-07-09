#!/usr/bin/env python3
"""Render UPLOAD_AND_RUN.md for an Amber task directory."""

from __future__ import annotations

import argparse
from pathlib import Path


def build_manifest(
    task_dir: Path,
    submit_script: str,
    remote_user: str,
    remote_host: str,
    remote_path: str,
) -> str:
    remote = f"{remote_user}@{remote_host}:{remote_path.rstrip('/')}/"
    task_name = task_dir.name
    task_remote = f"{remote_user}@{remote_host}:{remote_path.rstrip('/')}/{task_name}/"
    return f"""# 上传与运行说明

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

## 上传前的本地检查

- 先用 Amber MD Expert 的辅助脚本检查打包目录。
- 先汇总并确认时长，再把目录视为最终版本。

## 续跑提醒

- 续跑前先确认最新的 `.rst` 文件。
- 修改 continuation 作业前重新检查 `ntx` 和 `irest`。
- 续跑优先使用新的输出文件名。
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_dir", type=Path)
    parser.add_argument("--submit-script", default="run_slurm_gpu.sh")
    parser.add_argument("--remote-user", default="your_username")
    parser.add_argument("--remote-host", default="your.cluster.edu")
    parser.add_argument("--remote-path", default="~/amber-runs")
    args = parser.parse_args()

    task_dir = args.task_dir.resolve()
    task_dir.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        task_dir=task_dir,
        submit_script=args.submit_script,
        remote_user=args.remote_user,
        remote_host=args.remote_host,
        remote_path=args.remote_path,
    )
    output_path = task_dir / "UPLOAD_AND_RUN.md"
    output_path.write_text(manifest, encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
