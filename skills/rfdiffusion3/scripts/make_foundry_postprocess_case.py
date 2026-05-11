#!/usr/bin/env python3
"""Create a reproducible Foundry MPNN/RF3 post-processing case."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_CKPTS = {
    "protein_mpnn": "/path/to/foundry/checkpoints/proteinmpnn_v_48_020.pt",
    "ligand_mpnn": "/path/to/foundry/checkpoints/ligandmpnn_v_32_010_25.pt",
}
DEFAULT_RF3_CKPT = "/path/to/foundry/checkpoints/rf3_foundry_01_24_latest_remapped.ckpt"
DEFAULT_ENV = "/path/to/conda-envs/foundry-py312"
DEFAULT_CKPT_DIR = "/path/to/foundry/checkpoints"


def parse_csv(value: str | None) -> list[str] | None:
    if value is None or value.strip() == "":
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def shell_quote(path: str) -> str:
    return "'" + path.replace("'", "'\"'\"'") + "'"


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return cleaned.strip("_") or "foundry_postprocess"


def write_executable(path: Path, text: str) -> None:
    path.write_text(text)
    path.chmod(0o755)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure", required=True, help="RFD3 or MPNN structure path.")
    parser.add_argument("--case-name", required=True, help="Short case label.")
    parser.add_argument("--out-root", required=True, help="Directory to create.")
    parser.add_argument(
        "--mpnn-model",
        choices=["protein_mpnn", "ligand_mpnn"],
        default="protein_mpnn",
        help="MPNN model type.",
    )
    parser.add_argument("--checkpoint-path", help="Override MPNN checkpoint path.")
    parser.add_argument("--rf3-ckpt", default=DEFAULT_RF3_CKPT, help="RF3 checkpoint path.")
    parser.add_argument("--fixed-chains", help="Comma-separated fixed chain IDs.")
    parser.add_argument("--designed-chains", help="Comma-separated designed chain IDs.")
    parser.add_argument("--fixed-residues", help="Comma-separated fixed residues, e.g. A35,B40.")
    parser.add_argument("--designed-residues", help="Comma-separated designed residues.")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--number-of-batches", type=int, default=4)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--env-prefix", default=DEFAULT_ENV)
    parser.add_argument("--checkpoint-dir", default=DEFAULT_CKPT_DIR)
    args = parser.parse_args()

    structure = Path(args.structure).expanduser().resolve()
    if not structure.exists():
        raise SystemExit(f"structure not found: {structure}")

    case_name = safe_name(args.case_name)
    out_root = Path(args.out_root).expanduser().resolve()
    mpnn_out = out_root / "mpnn"
    rf3_out = out_root / "rf3"
    out_root.mkdir(parents=True, exist_ok=True)
    mpnn_out.mkdir(parents=True, exist_ok=True)
    rf3_out.mkdir(parents=True, exist_ok=True)

    checkpoint_path = args.checkpoint_path or DEFAULT_CKPTS[args.mpnn_model]
    input_cfg = {
        "structure_path": str(structure),
        "name": case_name,
        "batch_size": args.batch_size,
        "number_of_batches": args.number_of_batches,
        "temperature": args.temperature,
        "fixed_chains": parse_csv(args.fixed_chains),
        "designed_chains": parse_csv(args.designed_chains),
        "fixed_residues": parse_csv(args.fixed_residues),
        "designed_residues": parse_csv(args.designed_residues),
    }
    input_cfg = {k: v for k, v in input_cfg.items() if v is not None}
    if args.mpnn_model == "ligand_mpnn":
        input_cfg["atomize_side_chains"] = False

    config = {
        "model_type": args.mpnn_model,
        "checkpoint_path": checkpoint_path,
        "is_legacy_weights": True,
        "out_directory": str(mpnn_out),
        "write_fasta": True,
        "write_structures": True,
        "inputs": [input_cfg],
    }
    config_path = out_root / "mpnn_config.json"
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    run_mpnn = out_root / "run_mpnn.sh"
    write_executable(
        run_mpnn,
        f"""#!/usr/bin/env bash
set -euo pipefail
source ${CONDA_BASE:-$HOME/miniconda3}/etc/profile.d/conda.sh
conda activate {shell_quote(args.env_prefix)}
export FOUNDRY_CHECKPOINT_DIRS={shell_quote(args.checkpoint_dir)}
mpnn --config_json {shell_quote(str(config_path))}
""",
    )

    run_rf3 = out_root / "run_rf3.sh"
    default_rf3_input = mpnn_out / f"{case_name}_b0_d0.cif"
    write_executable(
        run_rf3,
        f"""#!/usr/bin/env bash
set -euo pipefail
source ${CONDA_BASE:-$HOME/miniconda3}/etc/profile.d/conda.sh
conda activate {shell_quote(args.env_prefix)}
export FOUNDRY_CHECKPOINT_DIRS={shell_quote(args.checkpoint_dir)}
RF3_INPUT=${{RF3_INPUT:-{shell_quote(str(default_rf3_input))}}}
rf3 fold inputs="$RF3_INPUT" out_dir={shell_quote(str(rf3_out))} ckpt_path={shell_quote(args.rf3_ckpt)}
""",
    )

    run_qc = out_root / "run_qc_rmsd.sh"
    write_executable(
        run_qc,
        f"""#!/usr/bin/env bash
set -euo pipefail
source ${CONDA_BASE:-$HOME/miniconda3}/etc/profile.d/conda.sh
conda activate {shell_quote(args.env_prefix)}
GENERATED=${{GENERATED:-{shell_quote(str(structure))}}}
REFOLDED=${{REFOLDED:?Set REFOLDED=/path/to/rf3_model.cif}}
python /path/to/foundry/workspace/skills/rfdiffusion3/scripts/qc_foundry_backbone_rmsd.py \\
  --generated "$GENERATED" \\
  --refolded "$REFOLDED" \\
  --out-json {shell_quote(str(out_root / "qc_rmsd.json"))} \\
  --out-tsv {shell_quote(str(out_root / "qc_rmsd.tsv"))} \\
  --export-dir {shell_quote(str(out_root / "aligned"))}
""",
    )

    readme = out_root / "README.md"
    readme.write_text(
        f"""# {case_name} Foundry Postprocess Case

Input structure:

```text
{structure}
```

Run MPNN:

```bash
bash {run_mpnn}
```

Expected MPNN files:

```text
{mpnn_out}/{case_name}.fa
{mpnn_out}/{case_name}_b0_d0.cif
```

Run RF3 on the first MPNN structure:

```bash
bash {run_rf3}
```

Run RF3 on a different MPNN structure:

```bash
RF3_INPUT=/absolute/path/to/other_mpnn_output.cif bash {run_rf3}
```

Run RMSD/QC after RF3:

```bash
REFOLDED=/absolute/path/to/rf3_model.cif bash {run_qc}
```
"""
    )

    print(f"[OK] {config_path}")
    print(f"[OK] {run_mpnn}")
    print(f"[OK] {run_rf3}")
    print(f"[OK] {run_qc}")
    print(f"[OK] {readme}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
