# Foundry / RFdiffusion3 Local Workflow Reference

## Official Sources

- Foundry README: https://github.com/RosettaCommons/foundry
- RFD3 README: https://github.com/RosettaCommons/foundry/blob/production/models/rfd3/README.md
- RFD3 docs index: https://rosettacommons.github.io/foundry/models/rfd3/index.html
- RFD3 Unix installation tutorial: https://rosettacommons.github.io/foundry/models/rfd3/tutorials/RFdiffusion3_installation_tutorial.html
- RFD3 inference basics: https://rosettacommons.github.io/foundry/models/rfd3/intro_inference_calculations.html
- RFD3 input specification: https://rosettacommons.github.io/foundry/models/rfd3/input.html
- PyTorch install selector: https://pytorch.org/get-started/locally/

## Local Policy

This user's C drive is tight. Keep Foundry on E:

```text
Conda env:      /path/to/conda-envs/foundry-py312
Checkpoints:    /path/to/foundry/checkpoints
Workspace/docs: /path/to/foundry/workspace
Run root:       /path/to/foundry/workspace/rfd3_runs
Conda cache:    /path/to/conda-pkgs
Pip cache:      /path/to/pip-cache
```

`torch-week1` is a known RTX 5080 PyTorch reference but is Python 3.11, so it is not the Foundry install target.

## Installed State

The local install was validated on 2026-05-07:

```text
Python: 3.12.13
PyTorch: 2.11.0+cu128
CUDA runtime: 12.8
GPU: NVIDIA GeForce RTX 5080 Laptop GPU
Checkpoints: /path/to/foundry/checkpoints
```

Core checkpoint commands used:

```bash
foundry install rfd3 rf3 --checkpoint-dir /path/to/foundry/checkpoints
foundry install proteinmpnn ligandmpnn --checkpoint-dir /path/to/foundry/checkpoints
```

In this installed CLI, `base-models` is not valid and `mpnn` is not accepted as a direct model name despite appearing in some help text. Use `proteinmpnn` and `ligandmpnn`.

## Install Skeleton

Use only when reinstalling or repairing the env:

```bash
export FOUNDRY_ENV=/path/to/conda-envs/foundry-py312
export FOUNDRY_CKPT=/path/to/foundry/checkpoints
export CONDA_PKGS_DIRS=/path/to/conda-pkgs
export PIP_CACHE_DIR=/path/to/pip-cache
mkdir -p "$FOUNDRY_CKPT" "$CONDA_PKGS_DIRS" "$PIP_CACHE_DIR"

conda create -p "$FOUNDRY_ENV" python=3.12 -y
source ${CONDA_BASE:-$HOME/miniconda3}/etc/profile.d/conda.sh
conda activate "$FOUNDRY_ENV"
python -m pip install --upgrade pip setuptools wheel
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
python -m pip install "rc-foundry[all]"
foundry install rfd3 rf3 --checkpoint-dir "$FOUNDRY_CKPT"
foundry install proteinmpnn ligandmpnn --checkpoint-dir "$FOUNDRY_CKPT"
export FOUNDRY_CHECKPOINT_DIRS="$FOUNDRY_CKPT"
```

For this RTX 5080 machine, do not allow a reinstall to silently downgrade the working `torch 2.11.0+cu128` stack unless the replacement is explicitly verified.

## Blackwell / RTX 5080

If PyTorch warns that GPU architecture is unsupported, apply the official tutorial's cu128 nightly fallback:

```bash
python -m pip install --pre torch torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/nightly/cu128 \
  --upgrade --force-reinstall
```

Then rerun:

```bash
python /path/to/foundry/workspace/skills/rfdiffusion3/scripts/check_foundry_env.py \
  --checkpoint-dir /path/to/foundry/checkpoints
```

## Demo Validation

Prepare:

```bash
python /path/to/foundry/workspace/skills/rfdiffusion3/scripts/prepare_rfd3_demo.py \
  --workdir /path/to/foundry/workspace/rfd3_demo \
  --checkpoint-dir /path/to/foundry/checkpoints
```

Run:

```bash
cd /path/to/foundry/workspace/rfd3_demo/verify_installation
FOUNDRY_CHECKPOINT_DIRS=/path/to/foundry/checkpoints rfd3 design out_dir=demo_output inputs=demo_compat.json skip_existing=False prevalidate_inputs=True diffusion_batch_size=1 n_batches=1 low_memory_mode=True dump_trajectories=False
```

Success means `.cif.gz` structures and `.json` metadata files appear under `demo_output/`.

The upstream `demo.json` downloaded on 2026-05-07 contained `allow_ligand_on_existing_chain`, which this installed package rejected as an extra Pydantic field. Use local `demo_compat.json` for smoke tests.

## Failure Checks

- Missing CLI: `python -m pip show rc-foundry`, `which rfd3`, `which foundry`.
- Wrong env: `which python`, `python -V`, `conda info --envs`.
- GPU unavailable: `nvidia-smi`, then `python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"`.
- Checkpoint unavailable: set `FOUNDRY_CHECKPOINT_DIRS=/path/to/foundry/checkpoints`, then `foundry list-installed`.
- C drive pressure: confirm `CONDA_PKGS_DIRS` and `PIP_CACHE_DIR` point to E before large installs.
