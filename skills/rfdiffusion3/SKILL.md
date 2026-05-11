---
name: rfdiffusion3
description: Install, validate, teach, and run RosettaCommons Foundry/RFdiffusion3 workflows on this user's WSL/Conda RTX 5080 machine. Use when the user mentions RFdiffusion3, RFD3, Foundry, rc-foundry, RF3, ProteinMPNN, LigandMPNN, checkpoint downloads, official RFD3 tutorials, RFD3 design JSON/YAML inputs, protein binder, nucleic acid binder, small molecule binder, enzyme scaffold, partial diffusion, or asks to package/run/debug RFD3 jobs.
---

# RFdiffusion3

## Defaults

Use these paths unless the user gives different ones:

```text
env_prefix=/path/to/conda-envs/foundry-py312
checkpoint_dir=/path/to/foundry/checkpoints
workspace=/path/to/foundry/workspace
run_root=/path/to/foundry/workspace/rfd3_runs
conda_pkgs_dir=/path/to/conda-pkgs
pip_cache_dir=/path/to/pip-cache
```

Prefer the installed Python 3.12 Foundry env. Do not install into `torch-week1` unless explicitly requested; it is Python 3.11.

## First Step

For any install/debug/run request, inspect the live state before making claims:

```bash
conda info --envs
nvidia-smi
test -d /path/to/conda-envs/foundry-py312
test -d /path/to/foundry/checkpoints
```

When running commands:

```bash
source ${CONDA_BASE:-$HOME/miniconda3}/etc/profile.d/conda.sh
conda activate /path/to/conda-envs/foundry-py312
export FOUNDRY_CHECKPOINT_DIRS=/path/to/foundry/checkpoints
mkdir -p /path/to/foundry/workspace/rfd3_runs
```

## Validate

Use the bundled script before expensive GPU work:

```bash
python /path/to/foundry/workspace/skills/rfdiffusion3/scripts/check_foundry_env.py \
  --checkpoint-dir /path/to/foundry/checkpoints
```

For official demo smoke tests:

```bash
python /path/to/foundry/workspace/skills/rfdiffusion3/scripts/prepare_rfd3_demo.py \
  --workdir /path/to/foundry/workspace/rfd3_demo \
  --checkpoint-dir /path/to/foundry/checkpoints
cd /path/to/foundry/workspace/rfd3_demo/verify_installation
FOUNDRY_CHECKPOINT_DIRS=/path/to/foundry/checkpoints rfd3 design out_dir=demo_output inputs=demo_compat.json skip_existing=False prevalidate_inputs=True diffusion_batch_size=1 n_batches=1 low_memory_mode=True dump_trajectories=False
```

Use `demo_compat.json` for this machine's smoke test; the upstream demo file included an unsupported `allow_ligand_on_existing_chain` field for the installed package version.

## Run RFD3

Minimum command:

```bash
FOUNDRY_CHECKPOINT_DIRS=/path/to/foundry/checkpoints rfd3 design out_dir=<out_dir> inputs=<input.json>
```

First-pass RTX 5080 settings:

```bash
rfd3 design out_dir=<out_dir> inputs=<input.json> prevalidate_inputs=True skip_existing=False diffusion_batch_size=1 n_batches=1 low_memory_mode=True dump_trajectories=False
```

Before writing an input file, inspect the user's PDB/CIF for chain IDs, residue numbers, and ligand residue names. Prefer absolute input paths under `/mnt/e`.

## References

Read only the reference needed for the task:

- `references/foundry-rfd3-workflow.md`: installation, local path policy, checkpoints, environment validation, RTX 5080 notes.
- `references/rfd3-usage-workflows.md`: official tutorial distilled workflows, input fields, templates for PPI, NA, small molecule, enzyme scaffold, and partial diffusion.
- `references/foundry-postprocess-workflow.md`: RFD3 outputs into ProteinMPNN/LigandMPNN, RF3 fold/review, Python API in-memory pipeline, and RMSD/QC.

User-facing tutorials live outside the skill:

- `/path/to/foundry/workspace/RFdiffusion3_Foundry_安装教程.md`
- `/path/to/foundry/workspace/RFdiffusion3_使用教程.md`
- `/path/to/foundry/workspace/Foundry_RFD3_MPNN_RF3_后处理教程.md`

Bundled scripts:

- `scripts/check_foundry_env.py`: validate Python, torch/CUDA, Foundry CLIs, and checkpoints.
- `scripts/prepare_rfd3_demo.py`: download official demo inputs and create `demo_compat.json`.
- `scripts/prepare_rfd3_tutorial_assets.py`: download official tutorial/example assets by profile when available.
- `scripts/make_foundry_postprocess_case.py`: generate an MPNN JSON config plus runnable MPNN/RF3 shell scripts for a chosen RFD3 structure.
- `scripts/foundry_python_api_pipeline_demo.py`: template for notebook-style in-memory RFD3 -> MPNN -> RF3 -> RMSD workflow.
- `scripts/qc_foundry_backbone_rmsd.py`: file-based backbone RMSD/QC between an RFD3 design and RF3 refolded structure.
