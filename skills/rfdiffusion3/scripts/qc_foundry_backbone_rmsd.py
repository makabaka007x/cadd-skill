#!/usr/bin/env python3
"""Compute backbone RMSD between an RFD3 design and an RF3 refolded structure."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
from atomworks.constants import PROTEIN_BACKBONE_ATOM_NAMES
from atomworks.io.utils.io_utils import load_any, to_cif_file
from biotite.structure import AtomArray, rmsd, superimpose


def load_atom_array(path: Path) -> AtomArray:
    array = load_any(path, model=1)
    if hasattr(array, "stack_depth"):
        if array.stack_depth() != 1:
            raise ValueError(f"{path} contains multiple models; pass a single-model structure")
        array = array[0]
    return array


def backbone(array: AtomArray, atom_names: list[str]) -> AtomArray:
    mask = np.isin(array.atom_name.astype(str), atom_names)
    bb = array[mask]
    if len(bb) == 0:
        raise ValueError("no selected backbone atoms found")
    return bb


def interpretation(value: float) -> str:
    if value < 1.0:
        return "excellent"
    if value < 2.0:
        return "good"
    if value < 4.0:
        return "moderate"
    return "poor"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", required=True, help="Original RFD3 structure.")
    parser.add_argument("--refolded", required=True, help="RF3-predicted/refolded structure.")
    parser.add_argument(
        "--atom-names",
        default=",".join(PROTEIN_BACKBONE_ATOM_NAMES),
        help="Comma-separated atom names used for RMSD.",
    )
    parser.add_argument("--out-json", help="Write summary JSON.")
    parser.add_argument("--out-tsv", help="Append/write one-row TSV summary.")
    parser.add_argument("--export-dir", help="Write generated.cif and refolded_fitted.cif.")
    args = parser.parse_args()

    generated_path = Path(args.generated).expanduser().resolve()
    refolded_path = Path(args.refolded).expanduser().resolve()
    atom_names = [name.strip() for name in args.atom_names.split(",") if name.strip()]

    generated = load_atom_array(generated_path)
    refolded = load_atom_array(refolded_path)
    generated_bb = backbone(generated, atom_names)
    refolded_bb = backbone(refolded, atom_names)

    if len(generated_bb) != len(refolded_bb):
        raise SystemExit(
            "backbone atom count mismatch: "
            f"generated={len(generated_bb)} refolded={len(refolded_bb)}. "
            "Compare structures with matching residue ranges or trim them first."
        )

    refolded_fitted, _ = superimpose(generated_bb, refolded_bb)
    value = float(rmsd(generated_bb, refolded_fitted))
    result = {
        "generated": str(generated_path),
        "refolded": str(refolded_path),
        "atom_names": atom_names,
        "backbone_atom_count": int(len(generated_bb)),
        "backbone_rmsd_angstrom": value,
        "interpretation": interpretation(value),
    }

    print(f"Backbone RMSD: {value:.3f} A")
    print(f"Interpretation: {result['interpretation']}")

    if args.export_dir:
        export_dir = Path(args.export_dir).expanduser().resolve()
        export_dir.mkdir(parents=True, exist_ok=True)
        to_cif_file(generated, export_dir / "generated.cif")
        to_cif_file(refolded_fitted, export_dir / "refolded_backbone_fitted.cif")
        result["export_dir"] = str(export_dir)

    if args.out_json:
        out_json = Path(args.out_json).expanduser().resolve()
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(result, indent=2) + "\n")

    if args.out_tsv:
        out_tsv = Path(args.out_tsv).expanduser().resolve()
        out_tsv.parent.mkdir(parents=True, exist_ok=True)
        write_header = not out_tsv.exists() or out_tsv.stat().st_size == 0
        with out_tsv.open("a", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(result.keys()), delimiter="\t")
            if write_header:
                writer.writeheader()
            writer.writerow(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
