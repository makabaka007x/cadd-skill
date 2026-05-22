# Auto CADD Skill Collection

Chinese version: [README.zh-CN.md](README.zh-CN.md)

This repository collects reusable Codex/Claude-style skills for CADD/AIDD work, including molecular dynamics, enhanced sampling, molecular docking, GPU virtual screening, protein design, and AlphaFold3 result analysis.

The repository is intended to be an agent skill manual and a portable skill bundle. The skills are not full software installers. They provide reusable instructions, helper scripts, templates, and safety checks that help an agent turn a scientific request into a reproducible workflow or run directory.

## Quick Skill Selector

| Task | Recommended skill | Use it for |
| --- | --- | --- |
| Amber molecular dynamics | `amber-md-expert` | Amber/AmberTools system preparation, explicit or implicit solvent MD, restart handling, cpptraj analysis, MM/GBSA, and HPC-ready run bundles. |
| GROMACS enhanced sampling | `gmx-workflow-packer` | GROMACS tREMD, REST2/HREX-style packaging, replica layout, preflight checks, demux, and exchange analysis. |
| Local HDOCK docking | `hdock` | Reproducible HDOCKlite protein-protein or protein-nucleic-acid docking cases, including optional site restraints and model export. |
| HADDOCK 2.5 docking | `haddock` | Information-driven biomolecular docking projects, restraint handling, example runs, and result analysis. |
| GPU virtual screening | `unidock-pro` | UniDock-Pro classical docking, ligand similarity search, hybrid docking, ligand indexing, batch execution, and result ranking. |
| Protein design | `rfdiffusion3` | Foundry/RFdiffusion3 environment validation, checkpoint setup, smoke tests, and design workflows. |
| AlphaFold3 result analysis | `af-analysis` | AlphaFold3 Server zip or local AF3 output analysis, ranking tables, ipTM_d0, pDockQ, mpDockQ, and PAE plots. |

## Repository Layout

```text
skills/
  amber-md-expert/
  hdock/
  haddock/
  gmx-workflow-packer/
  unidock-pro/
  rfdiffusion3/
  af-analysis/
```

Each skill keeps its own `SKILL.md` plus optional `scripts/`, `references/`, `assets/`, `templates/`, or `agents/` files. Read the skill's `SKILL.md` first, then load only the specific referenced script or document needed for the task.

## Local Clone Tutorial

Use this section when you want a local editable copy of the repository before installing skills into Codex or Claude.

1. Check that Git is available.

```bash
git --version
```

2. Choose a working directory and clone the repository.

```bash
mkdir -p ~/repos
cd ~/repos
git clone https://github.com/makabaka007x/cadd-skill.git
cd cadd-skill
```

3. Confirm that the skill directories exist.

```bash
ls skills
find skills -maxdepth 2 -name SKILL.md | sort
```

4. Pull future updates from GitHub.

```bash
cd ~/repos/cadd-skill
git pull --ff-only
```

5. If you prefer SSH and your GitHub SSH key is already configured, clone with SSH instead.

```bash
git clone git@github.com:makabaka007x/cadd-skill.git
```

Use HTTPS for the simplest read-only setup. Use SSH when you plan to push changes back to the repository.

## Install Into Agent Skill Roots

Install all skills into a Codex skill root:

```bash
cd ~/repos/cadd-skill
mkdir -p ~/.codex/skills
for skill_dir in skills/*; do
  rsync -a "$skill_dir" ~/.codex/skills/
done
```

Install one skill only:

```bash
cd ~/repos/cadd-skill
mkdir -p ~/.codex/skills
rsync -a skills/unidock-pro ~/.codex/skills/
```

For Claude-style local skill roots, copy the same directories into the active Claude skill directory, for example:

```bash
cd ~/repos/cadd-skill
mkdir -p ~/.claude/skills
rsync -a skills/unidock-pro ~/.claude/skills/
```

Validate a copied skill when a local validator is available:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/unidock-pro
```

If the validator is not installed, at minimum confirm that the target skill directory contains a `SKILL.md` file with valid YAML frontmatter and no machine-specific private paths.

## Detailed Skill Guide

### `amber-md-expert`

**Category:** Molecular dynamics and Amber workflow packaging.

**What it does:** This skill turns Amber or AmberTools work into a reproducible local or HPC-ready workflow. It covers structure preparation, topology generation, explicit or implicit solvent MD, restart/resume logic, cpptraj analysis, MM/GBSA or PBSA, contact analysis, and upload-ready run directories.

**Use when the request mentions:** Amber, AmberTools, pdb4amber, tleap, antechamber, parmchk2, pmemd, cpptraj, MMPBSA.py, PBSA, REMD, membrane systems, zinc or nonstandard residues, nucleic acids, DSSP, contact analysis, or packaging an MD job for a cluster.

**Typical inputs:** raw PDB or complex structures, ligand files, existing `prmtop`/`inpcrd`/`rst7` files, trajectories, restart files, force-field decisions, run length requirements, and target cluster constraints.

**Common workflow:** classify the task as raw structure preparation, existing Amber topology packaging, or analysis-only; choose force fields and water model; generate or assemble the run directory; add upload and resume instructions; validate run scripts and time scales before treating the bundle as ready.

**Example validation command:**

```bash
python3 skills/amber-md-expert/scripts/validate_amber_task.py /path/to/amber_run_dir
```

**Expected outputs:** a structured run directory, preparation files, MD input files, submit scripts, analysis scripts, restart/resume notes, and an `UPLOAD_AND_RUN.md` style instruction file when packaging for HPC.

**Important caveats:** force-field and water-model choices are scientific decisions, not generic defaults. Production time scales must be confirmed before final delivery. HPC partition, QOS, module, and wall-time policies must be adapted to the target cluster.

### `gmx-workflow-packer`

**Category:** GROMACS enhanced sampling and workflow packaging.

**What it does:** This skill packages GROMACS tREMD and REST2/HREX-style jobs into reproducible directories with preflight checks, replica layout, run scripts, state tracking, and post-processing support.

**Use when the request mentions:** GROMACS, `gmx`, tREMD, REMD, REST2, HREX, PLUMED `partial_tempering`, temperature ladders, replica exchange, demux, continuation, `step1`/`step2`, or HPC packaging for multi-replica simulations.

**Typical inputs:** `topol.top`, starting `.gro` or equivalent coordinate files, MDP templates, temperature or effective-temperature ladder, replica count, cluster limits, and whether the available GROMACS build supports `-hrex` and `-plumed`.

**Common workflow:** run an environment check; choose tREMD or REST2 mode; read or generate YAML config; generate replica directories and run scripts; render post-processing scripts; block production script generation if the environment lacks required HREX/PLUMED support.

**Example commands:**

```bash
python3 skills/gmx-workflow-packer/scripts/check_env.py --mode rest2 --check-hrex
python3 skills/gmx-workflow-packer/scripts/build_remd_bundle.py --config /path/to/config.yaml
```

**Expected outputs:** `step1/`, `step2/`, `analysis/`, zero-padded replica directories, `state.yaml`, demux scripts, exchange analysis helpers, and run instructions.

**Important caveats:** REST2 effective temperature is not the thermostat temperature. Do not fake REST2 exchange with `-replex` if the GROMACS build lacks `-hrex`. Replica count must fit the actual scheduler/QOS limits.

### `hdock`

**Category:** Local HDOCKlite docking.

**What it does:** This skill runs and packages reproducible HDOCKlite docking cases for protein-protein or protein-nucleic-acid systems. It can run `hdock`, export models with `createpl`, preserve logs, and create a summary for later inspection.

**Use when the request mentions:** HDOCK, HDOCKlite, `hdock`, `createpl`, receptor/ligand PDB files, `rsite.txt`, `lsite.txt`, `restr.txt`, binding-site restraints, or generating complex models from an existing `hdock.out`.

**Typical inputs:** receptor PDB, ligand PDB, optional site/restraint files, optional existing `hdock.out`, output directory, and number of models to export.

**Common workflow:** verify receptor and ligand inputs; decide whether to run docking or only export models from an existing `.out`; call the wrapper script; inspect logs and `run-summary.json`; report produced models and raw score output.

**Example commands:**

```bash
python3 skills/hdock/scripts/run_hdock_case.py receptor.pdb ligand.pdb \
  --output-dir runs/case1 \
  --nmax 20

python3 skills/hdock/scripts/run_hdock_case.py \
  --hdock-out hdock.out \
  --output-dir runs/from-out \
  --nmax 20
```

**Expected outputs:** `hdock.out`, `models.pdb`, copied inputs, stdout/stderr logs, and `run-summary.json`.

**Important caveats:** restraints should only be used when provided or scientifically justified. Raw docking scores are not biological validation.

### `haddock`

**Category:** HADDOCK 2.5 information-driven docking.

**What it does:** This skill helps create, run, and analyze HADDOCK 2.5 projects for protein-protein, protein-nucleic-acid, protein-ligand, peptide, and restraint-driven docking workflows.

**Use when the request mentions:** HADDOCK, HADDOCK 2.5, AIR restraints, ambiguous interaction restraints, docking examples, project setup, CNS/HADDOCK environment checks, or analysis of HADDOCK clusters and scores.

**Typical inputs:** molecule PDB files, active/passive residues, AIR or restraint files, HADDOCK parameter choices, project name, and the local HADDOCK installation path.

**Common workflow:** check the HADDOCK environment; create or select a project; prepare restraints and parameters; run the appropriate example or custom project; analyze clusters, scores, FCC/iRMSD when available, and top models.

**Example command pattern:**

```bash
# after activating the local HADDOCK environment
haddock2.5
```

Use the skill's helper commands and references for project creation, parameter editing, restraint generation, and result analysis.

**Expected outputs:** HADDOCK run directories, parameter files, restraints, cluster summaries, score tables, and selected top models.

**Important caveats:** HADDOCK is proprietary/local-install dependent. The public skill uses placeholder paths and cannot replace a configured licensed/local environment.

### `unidock-pro`

**Category:** GPU virtual screening.

**What it does:** This skill runs UniDock-Pro workflows for classical docking, ligand similarity searching, and hybrid docking. It provides wrappers for ligand indexing, batch execution, and result ranking.

**Use when the request mentions:** UniDock-Pro, `udp`, GPU virtual screening, `receptor.pdbqt`, `reference_ligand`, `ligand_index`, `ligand_dir`, `search_mode`, docking score ranking, or batch screening.

**Typical inputs:** receptor PDBQT for docking/hybrid modes, reference ligand for similarity/hybrid modes, ligand directory or ligand index, search box center and size, explicit search mode, and output directory.

**Common workflow:** identify the mode as docking, similarity, or hybrid; build a ligand index if only a ligand directory is provided; confirm search box and `search_mode`; run the wrapper script; summarize `*_out.pdbqt` files into a ranked CSV.

**Example commands:**

```bash
python3 skills/unidock-pro/scripts/make_ligand_index.py /path/to/ligands /path/to/ligand_index.txt

python3 skills/unidock-pro/scripts/run_unidock_case.py \
  --mode docking \
  --receptor /path/to/receptor.pdbqt \
  --ligand-index /path/to/ligand_index.txt \
  --center-x 0 --center-y 0 --center-z 0 \
  --size-x 20 --size-y 20 --size-z 20 \
  --search-mode <fast|balance|detail> \
  --output-dir /path/to/results

python3 skills/unidock-pro/scripts/analyze_unidock_results.py /path/to/results /path/to/docking_results.csv --top-n 50
```

**Expected outputs:** UniDock-Pro output PDBQT files, logs, ranked CSV summaries, and a report of the actual mode and assumptions used.

**Important caveats:** `search_mode` must be explicit. In hybrid mode, the reference ligand should match the receptor binding site and pose assumptions. Do not mix results from unrelated screening runs in one output directory.

### `rfdiffusion3`

**Category:** Protein design with Foundry/RFdiffusion3.

**What it does:** This skill validates and runs RosettaCommons Foundry/RFdiffusion3 workflows. It covers environment checks, checkpoint paths, official demo smoke tests, design input preparation, and downstream post-processing templates.

**Use when the request mentions:** RFdiffusion3, RFD3, Foundry, rc-foundry, RF3, ProteinMPNN, LigandMPNN, checkpoint downloads, binder design, nucleic-acid binders, small-molecule binders, enzyme scaffolds, partial diffusion, or RFD3 JSON/YAML design inputs.

**Typical inputs:** a configured Foundry/RFD3 environment, checkpoint directory, target PDB/CIF, chain IDs, residue numbering, optional ligand names, design JSON/YAML, output directory, and GPU constraints.

**Common workflow:** inspect the live environment; validate Python, torch/CUDA, Foundry CLIs, and checkpoints; run a small demo or smoke test before expensive GPU work; prepare design inputs from inspected structures; run low-memory first-pass settings when appropriate; post-process with MPNN/RF3/QC tools when requested.

**Example commands:**

```bash
python skills/rfdiffusion3/scripts/check_foundry_env.py \
  --checkpoint-dir /path/to/foundry/checkpoints

FOUNDRY_CHECKPOINT_DIRS=/path/to/foundry/checkpoints \
rfd3 design out_dir=/path/to/out inputs=/path/to/input.json \
  prevalidate_inputs=True diffusion_batch_size=1 n_batches=1 low_memory_mode=True
```

**Expected outputs:** RFD3 design outputs, optional trajectories, design metadata, MPNN/RF3 post-processing configs, and QC summaries.

**Important caveats:** inspect chain IDs, residue numbers, and ligand residue names before writing design inputs. GPU memory and package-version differences can change which tutorial fields are valid.

### `af-analysis`

**Category:** AlphaFold3 output analysis.

**What it does:** This skill analyzes AlphaFold3 Server zip files or local AF3 output directories with the `af-analysis` Python package. It focuses on ranking and interface quality metrics beyond basic ipTM.

**Use when the request mentions:** AlphaFold3 Server `fold_*.zip`, local AF3 output folders, ipTM_d0, pDockQ, mpDockQ, LIS, PAE matrices, PPI quality ranking, or AF3 result comparison.

**Typical inputs:** one or more `fold_*.zip` files, local AF3 output directories containing model structures and JSON files, output path, and desired table or figure format.

**Common workflow:** run quick ranking across a directory; export Markdown or CSV; run deeper analysis for selected samples; inspect PAE and interface metrics; keep biological interpretation bounded by prediction confidence.

**Example commands:**

```bash
python skills/af-analysis/af3_ranking.py --input . --output af3_ranking --format both

python skills/af-analysis/af3_deepanalyze.py \
  --zip fold_example.zip \
  --output example_af3_analysis/
```

**Expected outputs:** ranking tables, CSV/Markdown summaries, PAE heatmaps, analysis summaries, and optional notebook-style 3D visualization support.

**Important caveats:** NGLView-based 3D visualization requires a Jupyter-compatible environment. AF3 confidence metrics support prioritization, not direct experimental proof.

## Local Configuration Notes

This public repository uses placeholder paths such as:

- `/path/to/haddock2.5`
- `/path/to/UniDock-Pro`
- `/path/to/conda-envs/unidock-pro`
- `/path/to/conda-envs/foundry-py312`
- `/path/to/foundry/checkpoints`
- `/path/to/foundry/workspace`

Before running a workflow, edit the relevant `SKILL.md`, reference file, config file, or script argument to match the actual machine. Cluster partitions, QOS names, GPU limits, CPU limits, module names, and wall-time policies are examples only.

## Public-Use and Safety Notes

- Do not commit private home directories, WSL mount paths, cluster account names, tokens, API keys, passwords, or private key material.
- Treat bundled scripts as workflow helpers, not full environment installers.
- Run small validation or smoke tests before expensive docking, MD, screening, or protein-design jobs.
- Keep scientific claims bounded by the actual method: docking scores, AF3 confidence metrics, and design outputs are prioritization evidence, not experimental validation.
