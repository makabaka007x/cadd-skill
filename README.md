# CADD Skill Collection

Chinese version: [README.zh-CN.md](README.zh-CN.md)

This repository provides reusable Codex/Claude-style skills for CADD/AIDD work. It focuses on molecular docking, virtual screening, molecular dynamics, enhanced sampling, protein design, AlphaFold3 result analysis, and public chemical/biological database lookup.

The skills are agent instructions plus small helper scripts. They are not complete software installers. A skill-aware agent should read the relevant `SKILL.md`, inspect the user's local inputs, adapt paths and cluster settings, then run or package the workflow reproducibly.

## Quick Selector

| Task | Skill | Use when you need | Typical output |
| --- | --- | --- | --- |
| Amber MD setup or analysis | `amber-md-expert` | Amber/AmberTools, topology preparation, cpptraj, MM/GBSA, PBSA, restart checks | MD run directory, analysis scripts, plots, summary notes |
| GROMACS conventional MD | `gmx-workflow-packer` | EM, NVT, NPT, production MD, GROMACS run packaging | Conventional MD bundle with `mdp/`, `run.sh`, `state.yaml`, analysis notes |
| GROMACS tREMD/REST2 | `gmx-workflow-packer` | tREMD, REST2/HREX, PLUMED partial tempering, demux, exchange analysis | Replica run bundle, HREX preflight result, post-processing scripts |
| Local HDOCK docking | `hdock` | Protein-protein or protein-nucleic-acid HDOCKlite cases | `hdock.out`, exported complex models, logs, run summary |
| HADDOCK docking | `haddock` | Information-driven docking with active/passive residues, AIR restraints, HADDOCK projects | HADDOCK project files, restraints, cluster summaries, ranked models |
| GPU virtual screening | `unidock-pro` | UniDock-Pro classical docking, similarity search, or hybrid docking | Ligand index, docking outputs, ranked CSV, mode/search-box notes |
| RFdiffusion3 design | `rfdiffusion3` | Foundry/RFD3 binder, nucleic-acid binder, small-molecule binder, enzyme scaffold design | RFD3 inputs, smoke-test notes, design outputs, QC/post-processing templates |
| AlphaFold3 result analysis | `af-analysis` | AF3 Server `fold_*.zip`, local AF3 outputs, PAE/interface metrics | Ranking tables, CSV/Markdown summaries, PAE plots, interface metrics |
| PubChem lookup | `pubchem-pug-skill` | Compound properties, descriptions, assay summaries, substances | Compact PubChem summary or saved raw payload on request |
| ChEMBL lookup | `chembl-skill` | Activities, molecules, targets, mechanisms, text search | Compact ChEMBL activity or target summary |
| BindingDB lookup | `bindingdb-skill` | Ligand-target binding records by PDB, UniProt, or similarity | Compact binding evidence summary |
| RCSB PDB lookup | `rcsb-pdb-skill` | PDB metadata, structure search, FASTA download | Structure metadata, chain/source summary |
| UniProt lookup | `uniprot-skill` | UniProtKB, UniRef, UniParc, FASTA, annotations | Protein identity, sequence, functional annotation summary |
| ChEBI lookup | `chebi-skill` | Chemical identity, ontology, structure metadata | Compact ChEBI compound/ontology summary |

## Repository Layout

```text
skills/
  af-analysis/
  amber-md-expert/
  bindingdb-skill/
  chebi-skill/
  chembl-skill/
  gmx-workflow-packer/
  haddock/
  hdock/
  pubchem-pug-skill/
  rcsb-pdb-skill/
  rfdiffusion3/
  unidock-pro/
  uniprot-skill/
```

Each skill keeps a required `SKILL.md` and may include `scripts/`, `references/`, `assets/`, or `agents/`. Read `SKILL.md` first, then load only the referenced files needed for the task.

## Install

Clone the repository:

```bash
mkdir -p ~/repos
cd ~/repos
git clone https://github.com/makabaka007x/cadd-skill.git
cd cadd-skill
```

Install all skills into a Codex skill root:

```bash
mkdir -p ~/.codex/skills
for skill_dir in skills/*; do
  [ -f "$skill_dir/SKILL.md" ] && rsync -a "$skill_dir" ~/.codex/skills/
done
```

Install one skill only:

```bash
mkdir -p ~/.codex/skills
rsync -a skills/gmx-workflow-packer ~/.codex/skills/
```

For a Claude-style local skill root, copy the same directories into the active Claude skill directory:

```bash
mkdir -p ~/.claude/skills
rsync -a skills/unidock-pro ~/.claude/skills/
```

Validate the skill list:

```bash
find skills -maxdepth 2 -name SKILL.md | sort
```

If a local skill validator is available:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/gmx-workflow-packer
```

## Combined Workflow Examples

These are prompts for a skill-aware agent, not shell commands.

### Virtual Screening

Use database skills to define the target and ligand set, then dock with UniDock-Pro:

```text
Use $uniprot-skill and $rcsb-pdb-skill to confirm the target identity, available structures, chain IDs, and co-crystal ligands. Then use $chembl-skill, $bindingdb-skill, and $pubchem-pug-skill to collect known ligands and activity evidence. Build a ligand library, run $unidock-pro classical docking against the prepared receptor, and return a ranked CSV with the assumptions for the search box and search_mode.
```

Follow-up after docking:

```text
Use $bindingdb-skill and $chembl-skill to annotate the top 50 UniDock-Pro hits with known target or analog evidence, then summarize which hits are novel versus already supported by binding data.
```

### Molecular Docking

Use sequence and structure lookup before docking:

```text
Use $uniprot-skill to confirm the protein sequence and domain boundaries, then use $rcsb-pdb-skill to identify suitable template structures. If this is protein-protein or protein-nucleic-acid docking, run $hdock and export the top models. If active/passive residues or AIR restraints are available, prepare a $haddock project and rank the resulting clusters.
```

For ligand identity checks:

```text
Use $pubchem-pug-skill and $chebi-skill to confirm the ligand identity, synonyms, charge-relevant metadata, and structure identifiers before preparing the docking inputs.
```

### Molecular Dynamics

Use structure/database skills first, then choose Amber or GROMACS:

```text
Use $rcsb-pdb-skill and $uniprot-skill to verify the source structure, chain IDs, mutations, missing residues, and sequence coverage. Then use $amber-md-expert to prepare an Amber explicit-solvent MD package with restart checks and basic cpptraj analysis.
```

For GROMACS conventional MD:

```text
Use $gmx-workflow-packer to build a conventional GROMACS MD bundle from this prepared topol.top and 1EM.gro. Generate EM/NVT/NPT/production MDP files, a resumable run.sh, state.yaml, UPLOAD_AND_RUN.md, and basic analysis notes.
```

For enhanced sampling:

```text
Use $gmx-workflow-packer to prepare a tREMD bundle for this GROMACS system, estimate or validate the temperature ladder, create step1/step2/run.sh, and include demux plus exchange-efficiency analysis scripts. If I ask for REST2, first check whether the target GROMACS/PLUMED module supports both -plumed and -hrex.
```

### AF3-to-Design or MD Triage

```text
Use $af-analysis to rank these AlphaFold3 fold_*.zip files by ipTM_d0, pDockQ, mpDockQ, and PAE. For the best-supported interface, prepare either an $amber-md-expert or $gmx-workflow-packer MD package for stability checks, and keep all conclusions limited to prediction confidence until experimental or simulation evidence exists.
```

## Public-Use Notes

- Replace placeholder paths such as `/path/to/...`, `<cpu-partition>`, and `<gpu-qos>` with the target machine's actual settings.
- Database skills return compact summaries by default. Save raw API payloads only when the user explicitly asks.
- Do not commit private home directories, WSL mount paths, cluster account names, tokens, API keys, passwords, private keys, or unpublished project data.
- Run small smoke tests before expensive docking, MD, screening, or protein-design jobs.
- Treat docking scores, AF3 confidence metrics, and design outputs as prioritization evidence, not experimental validation.
