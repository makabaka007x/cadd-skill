#!/usr/bin/env python3
"""Download official RFdiffusion3 tutorial/example assets when available."""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


BASE = "https://raw.githubusercontent.com/RosettaCommons/foundry/production"


@dataclass(frozen=True)
class Asset:
    profile: str
    relative_path: str
    urls: tuple[str, ...]
    required: bool = True


ASSETS = [
    Asset("demo", "demo/verify_installation/demo.json", (f"{BASE}/models/rfd3/docs/examples/demo.json",)),
    Asset("demo", "demo/input_pdbs/M0255_1mg5.pdb", (f"{BASE}/models/rfd3/docs/input_pdbs/M0255_1mg5.pdb",)),
    Asset("demo", "demo/input_pdbs/7v11.pdb", (f"{BASE}/models/rfd3/docs/input_pdbs/7v11.pdb",)),
    Asset("demo", "demo/input_pdbs/1bna.pdb", (f"{BASE}/models/rfd3/docs/input_pdbs/1bna.pdb",)),
    Asset("ppi", "ppi/examples/protein_binder_design.json", (f"{BASE}/models/rfd3/docs/examples/protein_binder_design.json",), False),
    Asset("ppi", "ppi/input_pdbs/4zxb_cropped.pdb", (f"{BASE}/models/rfd3/docs/input_pdbs/4zxb_cropped.pdb",), False),
    Asset("ppi", "ppi/input_pdbs/5o45_cropped.pdb", (f"{BASE}/models/rfd3/docs/input_pdbs/5o45_cropped.pdb",), False),
    Asset("na", "na/input_pdbs/2r5z.pdb", (
        f"{BASE}/models/rfd3/docs/tutorials/na_tutorial_files/2r5z.pdb",
        f"{BASE}/models/rfd3/docs/na_tutorial_files/2r5z.pdb",
        f"{BASE}/models/rfd3/docs/input_pdbs/2r5z.pdb",
    ), False),
    Asset("sm", "sm/examples/sm_binder_design.json", (f"{BASE}/models/rfd3/docs/examples/sm_binder_design.json",), False),
    Asset("sm", "sm/input_pdbs/IAI.pdb", (
        f"{BASE}/models/rfd3/docs/input_pdbs/IAI.pdb",
        f"{BASE}/models/rfd3/docs/examples/IAI.pdb",
    ), False),
    Asset("enzyme", "enzyme/input_pdbs/1euv_lig.pdb", (
        f"{BASE}/models/rfd3/docs/tutorials/enzyme_tutorial_files/1euv_lig.pdb",
        f"{BASE}/models/rfd3/docs/input_pdbs/1euv_lig.pdb",
    ), False),
]


def fetch_first(urls: tuple[str, ...]) -> tuple[bytes | None, str | None, list[str]]:
    errors: list[str] = []
    for url in urls:
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
        except urllib.error.HTTPError as exc:
            errors.append(f"{url} -> HTTP {exc.code}")
            continue
        except urllib.error.URLError as exc:
            errors.append(f"{url} -> {exc.reason}")
            continue
        if data:
            return data, url, errors
        errors.append(f"{url} -> empty response")
    return None, None, errors


def write_demo_compat(workdir: Path) -> None:
    demo = workdir / "demo" / "verify_installation" / "demo.json"
    if not demo.exists():
        return
    data = json.loads(demo.read_text())
    changed = False
    for spec in data.values():
        if isinstance(spec, dict) and "allow_ligand_on_existing_chain" in spec:
            spec.pop("allow_ligand_on_existing_chain", None)
            changed = True
    compat = demo.with_name("demo_compat.json")
    compat.write_text(json.dumps(data, indent=4) + "\n")
    print(f"[OK] {compat}" + (" (compat field removed)" if changed else ""))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=["demo", "ppi", "na", "sm", "enzyme", "all"],
        default="demo",
        help="Asset group to download.",
    )
    parser.add_argument(
        "--workdir",
        default="/path/to/foundry/workspace/rfd3_tutorial_assets",
        help="Output directory.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing files.")
    args = parser.parse_args()

    workdir = Path(args.workdir).expanduser().resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    profiles = {"demo", "ppi", "na", "sm", "enzyme"} if args.profile == "all" else {args.profile}

    failed_required = False
    for asset in ASSETS:
        if asset.profile not in profiles:
            continue
        dest = workdir / asset.relative_path
        if dest.exists() and dest.stat().st_size > 0 and not args.force:
            print(f"[SKIP] {dest}")
            continue
        data, source_url, errors = fetch_first(asset.urls)
        if data is None:
            label = "FAIL" if asset.required else "WARN"
            print(f"[{label}] {asset.relative_path}")
            for error in errors:
                print(f"  {error}")
            failed_required = failed_required or asset.required
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print(f"[OK] {dest} ({len(data)} bytes) <- {source_url}")

    if "demo" in profiles:
        write_demo_compat(workdir)

    print("\nDone. Use these files as starting points; adapt chain IDs, residue numbers, ligands, and contigs to the user's real structure.")
    return 1 if failed_required else 0


if __name__ == "__main__":
    raise SystemExit(main())
