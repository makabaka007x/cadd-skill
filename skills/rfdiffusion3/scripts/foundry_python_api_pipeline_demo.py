#!/usr/bin/env python3
"""Template for the in-memory Foundry RFD3 -> MPNN -> RF3 -> RMSD workflow."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from atomworks.constants import PROTEIN_BACKBONE_ATOM_NAMES
from atomworks.io.utils.io_utils import to_cif_file
from biotite.sequence import ProteinSequence
from biotite.structure import get_residue_starts, rmsd, superimpose
from lightning.fabric import seed_everything
from mpnn.inference_engines.mpnn import MPNNInferenceEngine
from rf3.inference_engines.rf3 import RF3InferenceEngine
from rf3.utils.inference import InferenceInput
from rfd3.engine import RFD3InferenceConfig, RFD3InferenceEngine


def sequence_from_atom_array(atom_array) -> str:
    starts = get_residue_starts(atom_array)
    return "".join(
        ProteinSequence.convert_letter_3to1(res_name)
        for res_name in atom_array.res_name[starts]
    )


def backbone_rmsd(generated, refolded) -> float:
    generated_bb = generated[np.isin(generated.atom_name, PROTEIN_BACKBONE_ATOM_NAMES)]
    refolded_bb = refolded[np.isin(refolded.atom_name, PROTEIN_BACKBONE_ATOM_NAMES)]
    if len(generated_bb) != len(refolded_bb):
        raise ValueError(f"backbone atom count mismatch: {len(generated_bb)} vs {len(refolded_bb)}")
    refolded_fitted, _ = superimpose(generated_bb, refolded_bb)
    return float(rmsd(generated_bb, refolded_fitted))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--length", type=int, default=80)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--rfd3-batch-size", type=int, default=1)
    parser.add_argument("--rfd3-batches", type=int, default=1)
    parser.add_argument("--mpnn-model", choices=["protein_mpnn", "ligand_mpnn"], default="protein_mpnn")
    parser.add_argument("--mpnn-batch-size", type=int, default=4)
    parser.add_argument("--remove-waters", action="store_true")
    parser.add_argument("--skip-rf3", action="store_true", help="Stop after MPNN sequence design.")
    parser.add_argument("--out-dir", default="/path/to/foundry/workspace/python_api_demo")
    parser.add_argument("--rfd3-ckpt", default="/path/to/foundry/checkpoints/rfd3_latest.ckpt")
    parser.add_argument("--rf3-ckpt", default="/path/to/foundry/checkpoints/rf3_foundry_01_24_latest_remapped.ckpt")
    parser.add_argument("--proteinmpnn-ckpt", default="/path/to/foundry/checkpoints/proteinmpnn_v_48_020.pt")
    parser.add_argument("--ligandmpnn-ckpt", default="/path/to/foundry/checkpoints/ligandmpnn_v_32_010_25.pt")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    seed_everything(args.seed)
    rfd3_config = RFD3InferenceConfig(
        specification={"length": args.length},
        diffusion_batch_size=args.rfd3_batch_size,
        ckpt_path=args.rfd3_ckpt,
    )
    rfd3_model = RFD3InferenceEngine(**rfd3_config)
    rfd3_outputs = rfd3_model.run(inputs=None, out_dir=None, n_batches=args.rfd3_batches)
    first_key = next(iter(rfd3_outputs.keys()))
    atom_array = rfd3_outputs[first_key][0].atom_array
    to_cif_file(atom_array, out_dir / "rfd3_generated.cif")
    print(f"RFD3 keys: {list(rfd3_outputs.keys())}")
    print(f"RFD3 first backbone atoms: {len(atom_array)}")

    mpnn_ckpt = args.proteinmpnn_ckpt if args.mpnn_model == "protein_mpnn" else args.ligandmpnn_ckpt
    mpnn_engine = MPNNInferenceEngine(
        model_type=args.mpnn_model,
        is_legacy_weights=True,
        out_directory=None,
        write_structures=False,
        write_fasta=False,
        checkpoint_path=mpnn_ckpt,
    )
    mpnn_outputs = mpnn_engine.run(
        input_dicts=[{"batch_size": args.mpnn_batch_size, "remove_waters": args.remove_waters}],
        atom_arrays=[atom_array],
    )
    print(f"Generated {len(mpnn_outputs)} MPNN sequences")
    for i, item in enumerate(mpnn_outputs, start=1):
        print(f"Sequence {i}: {sequence_from_atom_array(item.atom_array)}")
    mpnn_atom_array = mpnn_outputs[0].atom_array
    to_cif_file(mpnn_atom_array, out_dir / "mpnn_design_1.cif")

    if args.skip_rf3:
        return 0

    rf3_engine = RF3InferenceEngine(ckpt_path=args.rf3_ckpt, verbose=False)
    rf3_input = InferenceInput.from_atom_array(mpnn_atom_array, example_id="mpnn_design_1")
    rf3_outputs = rf3_engine.run(inputs=rf3_input)
    rf3_output = rf3_outputs["mpnn_design_1"][0]
    to_cif_file(rf3_output.atom_array, out_dir / "rf3_refolded.cif")

    summary = rf3_output.summary_confidences
    print("=== RF3 Summary ===")
    for key in ["overall_plddt", "overall_pae", "overall_pde", "ptm", "iptm", "ranking_score", "has_clash"]:
        print(f"{key}: {summary.get(key)}")
    value = backbone_rmsd(atom_array, rf3_output.atom_array)
    print(f"Backbone RMSD: {value:.3f} A")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
