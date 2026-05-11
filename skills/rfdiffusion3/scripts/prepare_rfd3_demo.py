#!/usr/bin/env python3
"""Download official RFdiffusion3 demo inputs into a runnable work directory."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


BASE = "https://raw.githubusercontent.com/RosettaCommons/foundry/production"
FILES = {
    "verify_installation/demo.json": f"{BASE}/models/rfd3/docs/examples/demo.json",
    "input_pdbs/M0255_1mg5.pdb": f"{BASE}/models/rfd3/docs/input_pdbs/M0255_1mg5.pdb",
    "input_pdbs/7v11.pdb": f"{BASE}/models/rfd3/docs/input_pdbs/7v11.pdb",
    "input_pdbs/1bna.pdb": f"{BASE}/models/rfd3/docs/input_pdbs/1bna.pdb",
}


def download(url: str, dest: Path, force: bool) -> None:
    if dest.exists() and dest.stat().st_size > 0 and not force:
        print(f"[SKIP] {dest}")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"[GET] {url}")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:
            data = response.read()
    except urllib.error.URLError as exc:
        raise SystemExit(f"failed to download {url}: {exc}") from exc
    if not data:
        raise SystemExit(f"downloaded empty file: {url}")
    dest.write_bytes(data)
    print(f"[OK] {dest} ({len(data)} bytes)")


def write_compat_json(workdir: Path) -> Path:
    src = workdir / "verify_installation" / "demo.json"
    dest = workdir / "verify_installation" / "demo_compat.json"
    data = json.loads(src.read_text())
    for spec in data.values():
        if isinstance(spec, dict):
            spec.pop("allow_ligand_on_existing_chain", None)
    dest.write_text(json.dumps(data, indent=4) + "\n")
    print(f"[OK] {dest} (removed unsupported allow_ligand_on_existing_chain)")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workdir",
        default="/path/to/foundry/workspace/rfd3_demo",
        help="Directory that will contain input_pdbs/ and verify_installation/.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    parser.add_argument(
        "--checkpoint-dir",
        default="/path/to/foundry/checkpoints",
        help="Checkpoint directory shown in the printed run command.",
    )
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    for relative, url in FILES.items():
        download(url, workdir / relative, args.force)
    write_compat_json(workdir)

    verify_dir = workdir / "verify_installation"
    print("\nRun demo:")
    print(f"cd {verify_dir}")
    print(
        "FOUNDRY_CHECKPOINT_DIRS="
        f"{args.checkpoint_dir} "
        "rfd3 design out_dir=demo_output inputs=demo_compat.json "
        "skip_existing=False prevalidate_inputs=True "
        "diffusion_batch_size=1 n_batches=1 low_memory_mode=True "
        "dump_trajectories=False"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
