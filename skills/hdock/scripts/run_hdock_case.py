#!/usr/bin/env python3
"""Run HDOCK or export models from an existing HDOCK output."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run HDOCK from receptor/ligand PDBs or export models from an existing .out file."
    )
    parser.add_argument("receptor", nargs="?", help="Receptor PDB path")
    parser.add_argument("ligand", nargs="?", help="Ligand PDB path")
    parser.add_argument(
        "--hdock-out",
        help="Existing HDOCK output file. If set, skip docking and only run createpl.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="./hdock_case",
        help="Output directory for the case",
    )
    parser.add_argument(
        "-n",
        "--nmax",
        type=int,
        default=100,
        help="Number of models to export with createpl",
    )
    parser.add_argument("--spacing", help="Pass -spacing to hdock")
    parser.add_argument("--angle", help="Pass -angle to hdock")
    parser.add_argument("--rsite", help="Path to receptor site file")
    parser.add_argument("--lsite", help="Path to ligand site file")
    parser.add_argument("--restr", help="Path to receptor-ligand restraint file")
    parser.add_argument(
        "--itscore",
        choices=["true", "false"],
        help="Pass -itscore to hdock",
    )
    parser.add_argument(
        "--skip-models",
        action="store_true",
        help="Only generate hdock.out and skip createpl",
    )
    parser.add_argument("--hdock-bin", help="Explicit path to the hdock executable")
    parser.add_argument("--createpl-bin", help="Explicit path to the createpl executable")
    return parser.parse_args()


def ensure_file(path_str: str | None, label: str) -> Path | None:
    if path_str is None:
        return None
    path = Path(path_str).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"{label} not found: {path}")
    return path


def resolve_binary(name: str, explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit).expanduser().resolve()
        if path.is_file() and os.access(path, os.X_OK):
            return path
        raise FileNotFoundError(f"{name} executable not found: {path}")

    candidates: list[Path] = []
    env_dir = os.environ.get("HDOCK_BIN_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser().resolve())

    script_path = Path(__file__).resolve()
    candidates.append(Path.cwd())
    candidates.extend(script_path.parents)

    seen: set[Path] = set()
    for directory in candidates:
        if directory in seen:
            continue
        seen.add(directory)
        candidate = directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return candidate

    path_from_shell = shutil.which(name)
    if path_from_shell:
        return Path(path_from_shell).resolve()

    raise FileNotFoundError(
        f"Could not locate `{name}`. Set HDOCK_BIN_DIR or pass --{name}-bin explicitly."
    )


def copy_into_dir(src: Path, dst_dir: Path) -> Path:
    dst = dst_dir / src.name
    if src.resolve() != dst.resolve():
        shutil.copy2(src, dst)
    return dst


def infer_companion_pdbs(hdock_out: Path) -> list[str]:
    pdb_names: list[str] = []
    with hdock_out.open(encoding="utf-8", errors="ignore") as handle:
        for _ in range(12):
            line = handle.readline()
            if not line:
                break
            token = line.strip().split(maxsplit=1)
            if token and token[0].lower().endswith(".pdb") and token[0] not in pdb_names:
                pdb_names.append(token[0])
            if len(pdb_names) == 2:
                break
    return pdb_names


def stage_companion_pdbs(hdock_out: Path, inputs_dir: Path, output_dir: Path) -> list[str]:
    archived: list[str] = []
    search_dirs = [hdock_out.parent, Path.cwd()]
    for pdb_name in infer_companion_pdbs(hdock_out):
        for directory in search_dirs:
            candidate = (directory / pdb_name).resolve()
            if candidate.is_file():
                archived_path = copy_into_dir(candidate, inputs_dir)
                copy_into_dir(candidate, output_dir)
                archived.append(str(archived_path))
                break
    return archived


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def run_logged(cmd: list[str], stdout_path: Path, stderr_path: Path, cwd: Path) -> None:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    write_text(stdout_path, result.stdout)
    write_text(stderr_path, result.stderr)
    if result.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {result.returncode}: {' '.join(cmd)}\n"
            f"See {stdout_path} and {stderr_path}"
        )


def build_hdock_command(
    hdock_bin: Path,
    receptor: Path,
    ligand: Path,
    hdock_out: Path,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [str(hdock_bin), str(receptor), str(ligand), "-out", str(hdock_out)]
    for flag in ("spacing", "angle", "rsite", "lsite", "restr", "itscore"):
        value = getattr(args, flag)
        if value:
            cmd.extend([f"-{flag}", str(value)])
    return cmd


def build_createpl_command(
    createpl_bin: Path,
    hdock_out: Path,
    models_path: Path,
    args: argparse.Namespace,
) -> list[str]:
    cmd = [
        str(createpl_bin),
        str(hdock_out),
        str(models_path),
        "-nmax",
        str(args.nmax),
        "-complex",
        "-models",
    ]
    for flag in ("rsite", "lsite", "restr"):
        value = getattr(args, flag)
        if value:
            cmd.extend([f"-{flag}", str(value)])
    return cmd


def main() -> int:
    args = parse_args()

    receptor = ensure_file(args.receptor, "receptor") if args.receptor else None
    ligand = ensure_file(args.ligand, "ligand") if args.ligand else None
    existing_out = ensure_file(args.hdock_out, "hdock output") if args.hdock_out else None
    rsite = ensure_file(args.rsite, "rsite") if args.rsite else None
    lsite = ensure_file(args.lsite, "lsite") if args.lsite else None
    restr = ensure_file(args.restr, "restr") if args.restr else None

    if existing_out is not None:
        if receptor or ligand:
            raise ValueError("Do not pass receptor/ligand together with --hdock-out")
    else:
        if receptor is None or ligand is None:
            raise ValueError("Pass receptor and ligand, or provide --hdock-out")

    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    inputs_dir = output_dir / "inputs"
    inputs_dir.mkdir(exist_ok=True)

    archived_rsite = copy_into_dir(rsite, inputs_dir) if rsite else None
    archived_lsite = copy_into_dir(lsite, inputs_dir) if lsite else None
    archived_restr = copy_into_dir(restr, inputs_dir) if restr else None
    staged_rsite = copy_into_dir(rsite, output_dir) if rsite else None
    staged_lsite = copy_into_dir(lsite, output_dir) if lsite else None
    staged_restr = copy_into_dir(restr, output_dir) if restr else None

    args.rsite = staged_rsite.name if staged_rsite else None
    args.lsite = staged_lsite.name if staged_lsite else None
    args.restr = staged_restr.name if staged_restr else None

    summary: dict[str, object] = {
        "output_dir": str(output_dir),
        "nmax": args.nmax,
        "used_rsite": bool(archived_rsite),
        "used_lsite": bool(archived_lsite),
        "used_restr": bool(archived_restr),
    }

    createpl_cwd = output_dir

    if existing_out is not None:
        archived_out = copy_into_dir(existing_out, inputs_dir)
        hdock_out_path = copy_into_dir(existing_out, output_dir)
        summary["mode"] = "models-from-existing-out"
        summary["hdock_out"] = str(hdock_out_path)
        summary["archived_hdock_out"] = str(archived_out)
        summary["source_hdock_out"] = str(existing_out)
        archived_companions = stage_companion_pdbs(existing_out, inputs_dir, output_dir)
        if archived_companions:
            summary["archived_inputs"] = archived_companions
        createpl_source_out = Path(hdock_out_path.name)
    else:
        hdock_bin = resolve_binary("hdock", args.hdock_bin)
        archived_receptor = copy_into_dir(receptor, inputs_dir)
        archived_ligand = copy_into_dir(ligand, inputs_dir)
        staged_receptor = copy_into_dir(receptor, output_dir)
        staged_ligand = copy_into_dir(ligand, output_dir)
        hdock_out_path = output_dir / "hdock.out"
        hdock_cmd = build_hdock_command(
            hdock_bin,
            Path(staged_receptor.name),
            Path(staged_ligand.name),
            Path(hdock_out_path.name),
            args,
        )
        run_logged(
            hdock_cmd,
            output_dir / "hdock.stdout.log",
            output_dir / "hdock.stderr.log",
            output_dir,
        )
        summary["mode"] = "dock-and-export"
        summary["receptor"] = str(staged_receptor)
        summary["ligand"] = str(staged_ligand)
        summary["archived_inputs"] = [str(archived_receptor), str(archived_ligand)]
        summary["hdock_bin"] = str(hdock_bin)
        summary["hdock_out"] = str(hdock_out_path)
        summary["hdock_cmd"] = hdock_cmd
        createpl_source_out = Path(hdock_out_path.name)

    if not args.skip_models:
        createpl_bin = resolve_binary("createpl", args.createpl_bin)
        models_path = output_dir / "models.pdb"
        createpl_cmd = build_createpl_command(
            createpl_bin,
            createpl_source_out,
            Path(models_path.name),
            args,
        )
        run_logged(
            createpl_cmd,
            output_dir / "createpl.stdout.log",
            output_dir / "createpl.stderr.log",
            createpl_cwd,
        )
        summary["createpl_bin"] = str(createpl_bin)
        summary["models"] = str(models_path)
        summary["createpl_cmd"] = createpl_cmd
    else:
        summary["models"] = None

    (output_dir / "run-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
