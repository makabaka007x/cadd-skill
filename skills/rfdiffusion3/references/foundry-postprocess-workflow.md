# Foundry RFD3 -> MPNN -> RF3 Workflow

Use this reference when the user wants to continue from RFD3 outputs into sequence design and structure-prediction review.

## Official Sources

- Foundry README: https://github.com/RosettaCommons/foundry
- MPNN README: https://github.com/RosettaCommons/foundry/blob/production/models/mpnn/README.md
- RF3 README: https://github.com/RosettaCommons/foundry/blob/production/models/rf3/README.md
- End-to-end notebook pointer: https://github.com/RosettaCommons/foundry/blob/production/examples/all.ipynb

Foundry describes RFD3 as design, MPNN as inverse folding, and RF3 as protein folding/structure prediction. Keep these stages conceptually separate.

The user supplied a WeChat tutorial describing an in-memory Python API pipeline: RFD3 generates an AtomArray backbone, MPNN designs sequences on that AtomArray, RF3 refolds the designed AtomArray, then Biotite computes backbone RMSD for QC. Use that route for notebooks and method learning; use CLI/file workflows for routine batch jobs.

## Local Checkpoints

```text
RFD3:        /path/to/foundry/checkpoints/rfd3_latest.ckpt
RF3:         /path/to/foundry/checkpoints/rf3_foundry_01_24_latest_remapped.ckpt
ProteinMPNN: /path/to/foundry/checkpoints/proteinmpnn_v_48_020.pt
LigandMPNN:  /path/to/foundry/checkpoints/ligandmpnn_v_32_010_25.pt
```

For ProteinMPNN/LigandMPNN/SolubleMPNN original-style weights, use `is_legacy_weights=True`.

## MPNN CLI

Local `mpnn --help` shows that without `--config_json`, these are required:

```text
--model_type protein_mpnn|ligand_mpnn
--checkpoint_path <path>
--is_legacy_weights True|False
--structure_path <CIF-or-PDB>
```

ProteinMPNN verified command:

```bash
mpnn --model_type protein_mpnn --checkpoint_path /path/to/foundry/checkpoints/proteinmpnn_v_48_020.pt --is_legacy_weights True --structure_path /path/to/foundry/workspace/rfd3_demo/verify_installation/demo_output/demo_compat_M0255_1mg5_unfixed_0_model_0.cif.gz --out_directory /path/to/foundry/workspace/mpnn_rf3_demo/proteinmpnn --name demo_proteinmpnn --batch_size 1 --number_of_batches 1 --write_fasta True --write_structures True
```

Verified outputs:

```text
/path/to/foundry/workspace/mpnn_rf3_demo/proteinmpnn/demo_proteinmpnn.fa
/path/to/foundry/workspace/mpnn_rf3_demo/proteinmpnn/demo_proteinmpnn_b0_d0.cif
```

Important options:

- `--fixed_chains A` and `--designed_chains B` for binder workflows.
- `--fixed_residues A35,A38,A72` for motif/hotspot preservation.
- `--temperature 0.1` for conservative sampling.
- `--config_json <file>` ignores other CLI flags after parsing; put all settings in JSON.

## LigandMPNN CLI

Use when ligand, metal, cofactor, or atomic context matters:

```bash
mpnn --model_type ligand_mpnn --checkpoint_path /path/to/foundry/checkpoints/ligandmpnn_v_32_010_25.pt --is_legacy_weights True --structure_path <protein_ligand.cif> --out_directory <out_dir> --name <name> --batch_size 1 --number_of_batches 4 --write_fasta True --write_structures True --atomize_side_chains False
```

Always inspect ligand residue names and atom names before writing ligand-aware workflows.

## RF3 CLI

Local `rf3 fold` accepts Hydra overrides:

```bash
rf3 fold inputs='<input.json-or-cif>' out_dir='<out_dir>' ckpt_path='/path/to/foundry/checkpoints/rf3_foundry_01_24_latest_remapped.ckpt'
```

Do not use `--inputs`. A single positional path is treated as `inputs=<path>`, but explicit `inputs=...` is clearer.

Expected RF3 outputs from the official README:

```text
*_confidences.csv
*_ranking_scores.csv
*_model.cif
*_summary_confidences.json
seed-0_sample-*/
```

RF3 can early-stop without an MSA and only write metrics/score files. Use it on a small shortlist rather than every raw RFD3 design.

## Python API In-Memory Pipeline

RFD3 unconditional generation:

```python
from lightning.fabric import seed_everything
from rfd3.engine import RFD3InferenceConfig, RFD3InferenceEngine

seed_everything(0)
config = RFD3InferenceConfig(
    specification={"length": 80},
    diffusion_batch_size=1,
    ckpt_path="/path/to/foundry/checkpoints/rfd3_latest.ckpt",
)
rfd3 = RFD3InferenceEngine(**config)
rfd3_outputs = rfd3.run(inputs=None, out_dir=None, n_batches=1)
atom_array = rfd3_outputs[next(iter(rfd3_outputs.keys()))][0].atom_array
```

MPNN in memory:

```python
from mpnn.inference_engines.mpnn import MPNNInferenceEngine

mpnn = MPNNInferenceEngine(
    model_type="protein_mpnn",
    is_legacy_weights=True,
    out_directory=None,
    write_structures=False,
    write_fasta=False,
    checkpoint_path="/path/to/foundry/checkpoints/proteinmpnn_v_48_020.pt",
)
mpnn_outputs = mpnn.run(
    input_dicts=[{"batch_size": 10, "remove_waters": True}],
    atom_arrays=[atom_array],
)
```

RF3 refold:

```python
from rf3.inference_engines.rf3 import RF3InferenceEngine
from rf3.utils.inference import InferenceInput

rf3 = RF3InferenceEngine(
    ckpt_path="/path/to/foundry/checkpoints/rf3_foundry_01_24_latest_remapped.ckpt",
    verbose=False,
)
rf3_input = InferenceInput.from_atom_array(mpnn_outputs[0].atom_array, example_id="mpnn_design_1")
rf3_outputs = rf3.run(inputs=rf3_input)
rf3_output = rf3_outputs["mpnn_design_1"][0]
```

Important RF3 summary fields:

- `overall_plddt`
- `overall_pae`
- `overall_pde`
- `ptm`
- `iptm`
- `ranking_score`
- `has_clash`

## RMSD / QC

Backbone RMSD in memory:

```python
import numpy as np
from atomworks.constants import PROTEIN_BACKBONE_ATOM_NAMES
from biotite.structure import rmsd, superimpose

bb_generated = atom_array[np.isin(atom_array.atom_name, PROTEIN_BACKBONE_ATOM_NAMES)]
bb_refolded = rf3_output.atom_array[np.isin(rf3_output.atom_array.atom_name, PROTEIN_BACKBONE_ATOM_NAMES)]
bb_refolded_fitted, _ = superimpose(bb_generated, bb_refolded)
backbone_rmsd = rmsd(bb_generated, bb_refolded_fitted)
```

Interpretation:

- `<1.0 A`: excellent
- `1-2 A`: good
- `2-4 A`: moderate
- `>4 A`: poor

Use the bundled file-based QC script after CLI RF3 runs:

```bash
python /path/to/foundry/workspace/skills/rfdiffusion3/scripts/qc_foundry_backbone_rmsd.py --generated <rfd3.cif.gz> --refolded <rf3_model.cif> --out-json <rmsd.json> --out-tsv <summary.tsv> --export-dir <aligned_dir>
```

Use the Python API template script for demos:

```bash
python /path/to/foundry/workspace/skills/rfdiffusion3/scripts/foundry_python_api_pipeline_demo.py --length 80 --rfd3-batch-size 1 --mpnn-batch-size 4 --skip-rf3 --out-dir /path/to/foundry/workspace/python_api_demo
```

## Recommended Agent Behavior

When user asks to run the full workflow:

1. Inspect RFD3 outputs and choose candidate `.cif.gz` or `.cif`.
2. Inspect chain IDs/residue IDs/ligands before deciding ProteinMPNN vs LigandMPNN.
3. Use `scripts/make_foundry_postprocess_case.py` to generate config and run scripts.
4. Run MPNN first; verify `.fa` and `.cif` outputs.
5. Run RF3 only on selected MPNN `.cif` outputs unless the user explicitly asks for batch RF3.
6. Compute RFD3-vs-RF3 backbone RMSD when both structures have matching residue ranges.
7. Summarize outputs in a small TSV/Markdown table with RMSD and RF3 confidence fields.
