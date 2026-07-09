<p align="center">
  <img src="CADDskill-github-banner.png" alt="CADD Skill Collection banner">
</p>

# CADD Skill Collection

Chinese version: [README.zh-CN.md](README.zh-CN.md)

This repository provides reusable Codex/Claude-style skills for CADD/AIDD work. It is designed for researchers and agents working on molecular docking, virtual screening, molecular dynamics, enhanced sampling, protein design, AlphaFold3 result analysis, and public chemical or biological database lookup.

A skill is not a full software installer. It is an agent-facing workflow guide with optional helper scripts, templates, and reference notes. A skill-aware agent should read the relevant `SKILL.md`, inspect the user's real input files and local environment, adapt paths and compute settings, then run or package the workflow reproducibly.

## What Is Included

| Area | Skills |
| --- | --- |
| Molecular dynamics | `amber-md-expert`, `gmx-workflow-packer` |
| Molecular docking | `hdock`, `haddock`, `unidock-pro` |
| Protein design and AF3 analysis | `rfdiffusion3`, `af-analysis` |
| Compound and activity databases | `pubchem-pug-skill`, `chembl-skill`, `bindingdb-skill`, `chebi-skill` |
| Protein and structure databases | `uniprot-skill`, `rcsb-pdb-skill` |

## Quick Selector

Use this table when you know the task but not the best skill.

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

Each skill keeps a required `SKILL.md` and may include `scripts/`, `references/`, `assets/`, or `agents/`.

- `SKILL.md` contains trigger conditions and workflow instructions.
- `scripts/` contains deterministic helper scripts for repeated operations.
- `references/` contains longer method notes that should be read only when needed.
- `assets/` contains templates or bundled resources used to generate outputs.
- `agents/openai.yaml` is optional UI metadata for agent skill lists.

## Install and Update

Clone the repository:

```bash
mkdir -p ~/repos
cd ~/repos
git clone https://github.com/makabaka007x/cadd-skill.git
cd cadd-skill
```

Pull future updates:

```bash
cd ~/repos/cadd-skill
git pull --ff-only
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

Check what is installed:

```bash
find skills -maxdepth 2 -name SKILL.md | sort
```

If a local skill validator is available:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/gmx-workflow-packer
```

## Skill Details

### `amber-md-expert`

`amber-md-expert` packages Amber and AmberTools workflows into reproducible preparation, run, resume, or analysis directories.

Use it for:

- `pdb4amber`, `tleap`, `antechamber`, `parmchk2`, `pmemd`, `pmemd.cuda`, `cpptraj`, `MMPBSA.py`, or PBSA tasks.
- Explicit-solvent, implicit-solvent, membrane, nucleic-acid, Zn, nonstandard-residue, and REMD systems.
- Restart-chain checks before extending an Amber run.
- Basic trajectory processing, contact analysis, DSSP/DSSPplot, and MM/GBSA-style analysis packages.

Typical inputs:

- Raw PDB, protein-ligand complex, ligand files, or prepared Amber `prmtop`/`inpcrd`/`rst7`.
- Desired force fields, water model, ion conditions, production length, and target machine constraints.

Typical outputs:

- Prepared run directory with input files, submit script templates, `UPLOAD_AND_RUN.md`, and restart notes.
- Optional analysis bundle with `cpptraj` scripts, stripped trajectories, representative frames, tables, and plots.

Important notes:

- Force fields, protonation states, water model, ion placement, and production length are scientific decisions.
- Cluster partition, QOS, module names, account strings, and wall-time policy must be adapted to the target machine.

### `gmx-workflow-packer`

`gmx-workflow-packer` packages GROMACS conventional MD, tREMD, and REST2/HREX workflows.

Use it for:

- Conventional MD: EM, restrained equilibration, NVT, NPT, production, restart, and basic analysis.
- tREMD: temperature ladder generation, replica setup, segmented resume, demux, exchange efficiency, and trajectory reorganization.
- REST2/HREX: PLUMED `partial_tempering`, hot-region topology preparation, and `-hrex` capability checks.

Typical inputs:

- Prepared GROMACS `topol.top` plus coordinate files such as `1EM.gro`.
- Or a protein PDB for local `pdb2gmx -> editconf -> solvate -> genion -> EM` preparation.
- For ligand systems, ligand file and parameterization choice such as ACPYPE/GAFF.

Typical outputs:

- Conventional MD bundle with `mdp/`, `run.sh`, `state.yaml`, `UPLOAD_AND_RUN.md`, and analysis notes.
- tREMD bundle with `step1/`, `step2/`, `run.sh`, ladder files, demux tools, and exchange analysis.
- REST2 preflight bundle that blocks production if the target GROMACS/PLUMED module lacks `-hrex`.

Important notes:

- `sampling.mode=md` uses `assets/md-config-template.yaml` and `scripts/build_md_bundle.py`.
- `sampling.mode=tremd` and `sampling.mode=rest2` use the enhanced-sampling templates.
- REST2 effective temperature is not the thermostat temperature; it comes from Hamiltonian scaling.

### `hdock`

`hdock` runs and packages local HDOCKlite docking cases.

Use it for:

- Protein-protein docking.
- Protein-nucleic-acid docking.
- HDOCK runs with optional `rsite.txt`, `lsite.txt`, or `restr.txt`.
- Exporting complex models from an existing `hdock.out`.

Typical outputs:

- `hdock.out`
- `models.pdb`
- copied input files
- stdout/stderr logs
- `run-summary.json`

Important notes:

- HDOCK scores are docking-prioritization evidence, not biological validation.
- Restraints should be used only when supplied or scientifically justified.

### `haddock`

`haddock` helps create, run, and analyze HADDOCK 2.5 projects.

Use it for:

- Protein-protein, protein-DNA/RNA, protein-ligand, peptide, and restraint-driven docking.
- Active/passive residues, AIR restraints, ambiguous interaction restraints, or HADDOCK examples.
- Cluster scoring, top-model selection, and result summarization.

Typical outputs:

- HADDOCK project directory
- parameter and restraint files
- cluster score tables
- selected top models
- interpretation notes tied to the available restraints and scores

Important notes:

- HADDOCK depends on a configured local/licensed environment.
- The skill uses placeholder paths; users must adapt them to their own installation.

### `unidock-pro`

`unidock-pro` runs UniDock-Pro workflows for GPU virtual screening.

Use it for:

- Classical docking with `receptor.pdbqt` and a ligand library.
- Ligand similarity searching with a reference ligand.
- Hybrid docking with both receptor and reference ligand.
- Ranking `*_out.pdbqt` files into a CSV table.

Typical inputs:

- receptor PDBQT
- ligand directory or ligand index
- reference ligand for similarity or hybrid mode
- search-box center and size
- explicit `search_mode`

Typical outputs:

- ligand index
- UniDock-Pro output PDBQT files
- logs
- ranked CSV
- explanation of mode, search box, and assumptions

Important notes:

- `search_mode` must be explicit.
- Use a fresh output directory for each screening run.
- Hybrid docking assumes the reference ligand is compatible with the receptor binding site.

### `rfdiffusion3`

`rfdiffusion3` validates and runs RosettaCommons Foundry/RFdiffusion3 workflows.

Use it for:

- RFD3 environment validation.
- Checkpoint checks.
- Official demo smoke tests.
- Protein binder, nucleic-acid binder, small-molecule binder, enzyme scaffold, or partial-diffusion design jobs.
- Optional downstream ProteinMPNN/LigandMPNN/RF3-style post-processing.

Typical outputs:

- validated environment notes
- design input JSON/YAML
- RFD3 run directory
- optional MPNN/RF3 post-processing scripts
- basic QC summaries

Important notes:

- Inspect chain IDs, residue numbers, ligand residue names, and input file paths before writing design inputs.
- Start with small, low-memory smoke tests before expensive GPU work.

### `af-analysis`

`af-analysis` analyzes AlphaFold3 prediction outputs with the `af-analysis` Python package.

Use it for:

- AlphaFold Server `fold_*.zip` files.
- Local AF3 output directories containing `.cif`/`.pdb` plus JSON files.
- ipTM, ipTM_d0, pDockQ, mpDockQ, LIS, PAE, and interface-quality comparisons.

Typical outputs:

- Markdown ranking tables
- CSV ranking tables
- PAE heatmaps
- summary text
- interface-confidence notes

Important notes:

- AF3 confidence metrics support prioritization, not direct experimental claims.
- NGLView-based visualization requires a compatible Jupyter environment.

### Database Skills

The database skills are lightweight REST/API helpers. By default, they return compact summaries and do not save large raw payloads unless the user explicitly asks.

| Skill | Main use | Common query examples |
| --- | --- | --- |
| `pubchem-pug-skill` | PubChem compound properties, descriptions, assays, substances | CID/name lookup, molecular formula, molecular weight, assay summary |
| `chembl-skill` | ChEMBL activity, molecule, target, mechanism, text search | ligand activity table, target metadata, mechanism records |
| `bindingdb-skill` | BindingDB target-ligand evidence | known ligands for a UniProt target, binding data for a PDB-linked target |
| `rcsb-pdb-skill` | RCSB PDB metadata, structure search, FASTA | structure availability, chain IDs, organism/source, experimental method |
| `uniprot-skill` | UniProt protein identity, sequence, annotations | accession lookup, FASTA, domain/function annotations |
| `chebi-skill` | ChEBI compound identity and ontology | synonyms, ontology parents/children, chemical metadata |

## Combined Workflow Examples

These are prompts for a skill-aware agent, not shell commands.

### Virtual Screening From Public Evidence

Goal: build a target-aware ligand set, dock it, and annotate the ranked hits.

1. Confirm the target.
2. Identify structures and binding-site evidence.
3. Collect known ligands and activity records.
4. Build or verify the ligand library.
5. Run UniDock-Pro.
6. Annotate and summarize ranked hits.

Prompt:

```text
Use $uniprot-skill and $rcsb-pdb-skill to confirm the target identity, available structures, chain IDs, organism, mutations, and co-crystal ligands. Then use $chembl-skill, $bindingdb-skill, and $pubchem-pug-skill to collect known ligands and activity evidence. Build a clean ligand library, run $unidock-pro classical docking against the prepared receptor, and return a ranked CSV with the search-box, search_mode, ligand provenance, and top-hit annotation.
```

Follow-up:

```text
Use $bindingdb-skill and $chembl-skill to annotate the top 50 UniDock-Pro hits with known target or analog evidence. Group hits into known actives, analog-supported candidates, and apparently novel candidates. Keep docking scores separate from experimental binding evidence.
```

### Structure-Guided Molecular Docking

Goal: choose the right docking route based on the molecular system and available restraints.

Prompt:

```text
Use $uniprot-skill to confirm the protein sequence, isoform, domain boundaries, mutations, and residue numbering. Use $rcsb-pdb-skill to identify suitable template structures and chain IDs. If the task is protein-protein or protein-nucleic-acid docking without detailed restraints, use $hdock and export the top models. If active/passive residues, AIR restraints, or experimental interaction evidence are available, prepare a $haddock project and rank the resulting clusters.
```

Ligand identity check:

```text
Use $pubchem-pug-skill and $chebi-skill to confirm ligand identity, synonyms, structure identifiers, and charge-relevant metadata before preparing ligand docking files.
```

### Molecular Dynamics After Docking

Goal: turn a selected docking model into a reproducible MD package.

Amber route:

```text
Use $rcsb-pdb-skill and $uniprot-skill to verify the source structure, chain IDs, mutations, missing residues, and sequence coverage. Then use $amber-md-expert to prepare an explicit-solvent Amber MD package for the selected docking model, including topology preparation, staged minimization/equilibration, restart checks, and basic cpptraj analysis.
```

GROMACS conventional MD route:

```text
Use $gmx-workflow-packer to build a conventional GROMACS MD bundle from this prepared topol.top and 1EM.gro. Generate EM/NVT/NPT/production MDP files, a resumable run.sh, state.yaml, UPLOAD_AND_RUN.md, and basic analysis notes. Keep all cluster partition, QOS, module, and wall-time values as target-machine placeholders until confirmed.
```

Enhanced sampling route:

```text
Use $gmx-workflow-packer to prepare a tREMD bundle for this GROMACS system. Estimate or validate the temperature ladder, create step1/step2/run.sh, include demux and exchange-efficiency analysis scripts, and explain how to resume segmented production. If I ask for REST2, first check whether the target GROMACS/PLUMED module supports both -plumed and -hrex.
```

### AF3 Triage To MD or Design

Goal: rank predicted complexes, then decide which structures deserve simulation or design follow-up.

Prompt:

```text
Use $af-analysis to rank these AlphaFold3 fold_*.zip files by ipTM_d0, pDockQ, mpDockQ, LIS, and PAE. For the best-supported interfaces, recommend whether to prepare an $amber-md-expert MD package, a $gmx-workflow-packer MD package, or an $rfdiffusion3 design follow-up. Keep all conclusions limited to prediction confidence until simulation or experimental evidence exists.
```

### Protein Design With Evidence Checks

Goal: prepare an RFD3 design job using clean target structure and residue information.

Prompt:

```text
Use $uniprot-skill and $rcsb-pdb-skill to confirm target identity, chain IDs, residue numbering, missing regions, and ligand or nucleic-acid components. Then use $rfdiffusion3 to validate the Foundry/RFD3 environment, run a small smoke test, inspect the input structure, and prepare a first-pass binder design job with conservative low-memory settings.
```

## References and Upstream Resources

Use these links for method documentation, installation details, API behavior, and citation guidance. For manuscripts, cite the original method papers recommended by each upstream project.

### Molecular Dynamics and Enhanced Sampling

| Topic | References |
| --- | --- |
| Amber / AmberTools | [Amber official site](https://ambermd.org/), [Amber manuals](https://ambermd.org/Manuals.php), [Amber tutorials](https://ambermd.org/tutorials/), [Amber force fields](https://ambermd.org/AmberModels.php) |
| GROMACS | [GROMACS documentation](https://manual.gromacs.org/current/index.html), [installation guide](https://manual.gromacs.org/current/install-guide/index.html), [mdrun features](https://manual.gromacs.org/current/user-guide/mdrun-features.html), [replica exchange](https://manual.gromacs.org/current/reference-manual/algorithms/replica-exchange.html) |
| PLUMED / REST2 context | [PLUMED user manual](https://www.plumed.org/doc-v2.9/user-doc/html/), [PLUMED tutorials](https://www.plumed.org/doc-v2.9/user-doc/html/tutorials.html) |

### Docking, Screening, Design, and AF3 Analysis

| Topic | References |
| --- | --- |
| HDOCK | [HDOCK server](https://hdock.phys.hust.edu.cn/), [HDOCK help](https://hdock.phys.hust.edu.cn/help.php) |
| HADDOCK | [HADDOCK 2.4/2.5 software page](https://www.bonvinlab.org/software/haddock2.4/), [HADDOCK documentation](https://www.bonvinlab.org/software/haddock2.4/documentation/) |
| Uni-Dock / UniDock-Pro context | [Uni-Dock GitHub](https://github.com/dptech-corp/Uni-Dock), [Uni-Dock JCTC paper DOI](https://doi.org/10.1021/acs.jctc.2c01145) |
| RFdiffusion3 / Foundry | [Foundry GitHub](https://github.com/RosettaCommons/foundry), [RFdiffusion3 documentation](https://rosettacommons.github.io/foundry/models/rfd3/index.html), [RFD3 input specification](https://rosettacommons.github.io/foundry/models/rfd3/input.html) |
| AlphaFold3 result analysis | [af_analysis GitHub](https://github.com/samuelmurail/af_analysis), [af_analysis documentation](https://af-analysis.readthedocs.io/) |

### Public Databases and APIs

| Database | References |
| --- | --- |
| PubChem | [PubChem PUG REST](https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest), [PubChem docs](https://pubchem.ncbi.nlm.nih.gov/docs) |
| ChEMBL | [ChEMBL REST API](https://www.ebi.ac.uk/chembl/api/data/docs), [ChEMBL web services](https://chembl.gitbook.io/chembl-interface-documentation/web-services) |
| BindingDB | [BindingDB home](https://www.bindingdb.org/), [BindingDB web services/downloads](https://www.bindingdb.org/rwd/bind/chemsearch/marvin/SDFdownload.jsp?all_download=yes) |
| RCSB PDB | [RCSB Data API](https://data.rcsb.org/), [RCSB Search API](https://search.rcsb.org/), [RCSB PDB](https://www.rcsb.org/) |
| UniProt | [UniProt API help](https://www.uniprot.org/help/api), [UniProt REST API endpoint](https://rest.uniprot.org/) |
| ChEBI | [ChEBI API documentation](https://www.ebi.ac.uk/chebi/backend/api/docs/), [ChEBI search](https://www.ebi.ac.uk/chebi/) |

## Local Configuration Checklist

Before running any expensive workflow, confirm these items:

- Real input paths exist and are not stale intermediate files.
- Protein chain IDs, residue numbering, ligand residue names, and protonation assumptions are known.
- Force field, water model, ion conditions, and restraint choices are scientifically justified.
- GPU/CPU partition, QOS, account, module names, MPI launcher, and wall-time limits match the target machine.
- Output directories are fresh, or overwrite behavior has been explicitly approved.
- A small smoke test or short run has passed before full production.

## Public-Use and Safety Notes

- Replace placeholder paths such as `/path/to/...`, `<cpu-partition>`, and `<gpu-qos>` with the target machine's actual settings.
- Database skills return compact summaries by default. Save raw API payloads only when the user explicitly asks.
- Do not commit private home directories, WSL mount paths, cluster account names, tokens, API keys, passwords, private keys, unpublished project data, or personal machine paths.
- Keep docking scores, AF3 confidence metrics, and design outputs separate from experimental evidence.
- Run small validation or smoke tests before expensive docking, MD, screening, or protein-design jobs.
- Document assumptions in the final output: input provenance, software versions when known, search box, force field, simulation length, and any unverified biological interpretation.
