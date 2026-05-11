# CADD Skill Collection

This repository collects reusable Codex/Claude-style skills for CADD/AIDD,
molecular docking, molecular dynamics, virtual screening, and protein design
workflows.

## Included Skills

| Skill | Purpose |
| --- | --- |
| `amber-md-expert` | Package Amber/AmberTools molecular dynamics jobs, analysis, restart, and MM/GBSA workflows for local or HPC execution. |
| `hdock` | Run and package reproducible HDOCKlite protein-protein or protein-nucleic-acid docking cases. |
| `haddock` | Work with HADDOCK 2.5 projects, parameters, constraints, docking runs, and result analysis. |
| `gmx-workflow-packer` | Package GROMACS tREMD and REST2/HREX-style workflows with preflight checks and post-processing. |
| `unidock-pro` | Run UniDock-Pro GPU virtual screening, ligand-similarity searching, hybrid docking, and result ranking. |
| `rfdiffusion3` | Install, validate, teach, and run RFdiffusion3/Foundry protein design workflows. |
| `af-analysis` | Analyze AlphaFold3 Server or local AF3 outputs with `af-analysis`, including ipTM_d0, pDockQ, mpDockQ, and PAE plots. |

## Layout

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

Each skill keeps its own `SKILL.md` plus optional `scripts/`, `references/`,
`assets/`, and `agents/` files.

## Installation

Copy the skill directories you need into your agent skill directory.

For Codex:

```bash
mkdir -p ~/.codex/skills
rsync -a skills/amber-md-expert ~/.codex/skills/
rsync -a skills/hdock ~/.codex/skills/
rsync -a skills/haddock ~/.codex/skills/
rsync -a skills/gmx-workflow-packer ~/.codex/skills/
rsync -a skills/unidock-pro ~/.codex/skills/
rsync -a skills/rfdiffusion3 ~/.codex/skills/
rsync -a skills/af-analysis ~/.codex/skills/
```

For Claude-style local skill roots, copy the same directories into your active
Claude skill directory, for example `~/.claude/skills` or another configured
skill root.

## Local Configuration

This public version replaces machine-specific paths with placeholders such as:

- `/path/to/haddock2.5`
- `/path/to/UniDock-Pro`
- `/path/to/conda-envs/unidock-pro`
- `/path/to/conda-envs/foundry-py312`
- `/path/to/foundry/checkpoints`
- `/path/to/foundry/workspace`

Before running the workflows, edit the relevant `SKILL.md`, reference files, or
script arguments to match your local installation. HPC partition and QOS values
in templates are examples and should be adjusted to your scheduler.

## Public-Release Sanitization

Before the initial public push, the repository was scanned for:

- personal home directories and WSL mount paths
- local conda/model/application install paths
- HPC account names
- common secret tokens, API keys, passwords, and private key markers

No credential-like secrets were intentionally included. The bundled scripts and
templates are workflow helpers, not complete environment installers.
