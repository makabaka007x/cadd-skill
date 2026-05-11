# RFdiffusion3 Usage Workflows

This reference condenses the official RFD3 tutorials into local, runnable patterns. Use it when generating input JSON/YAML or packaging jobs for the user.

## Official Sources

- Inference basics: https://rosettacommons.github.io/foundry/models/rfd3/intro_inference_calculations.html
- Input specification: https://rosettacommons.github.io/foundry/models/rfd3/input.html
- Protein binder tutorial: https://rosettacommons.github.io/foundry/models/rfd3/tutorials/ppi_design_tutorial.html
- Nucleic acid binder tutorial: https://rosettacommons.github.io/foundry/models/rfd3/tutorials/na_binder_tutorial.html
- Small molecule binder example: https://rosettacommons.github.io/foundry/models/rfd3/examples/sm_binder_design.html
- Protein binder example: https://rosettacommons.github.io/foundry/models/rfd3/examples/protein_binder_design.html
- Enzyme design tutorial: https://rosettacommons.github.io/foundry/models/rfd3/tutorials/enzyme_design_tutorial.html

## Local Run Defaults

Use these settings for first-pass jobs on the user's 16GB RTX 5080:

```bash
prevalidate_inputs=True
skip_existing=False
diffusion_batch_size=1
n_batches=1
low_memory_mode=True
dump_trajectories=False
```

Prefer increasing `n_batches` before increasing `diffusion_batch_size`.

## Input Preparation Rules

Before writing JSON/YAML:

1. Confirm the input structure exists.
2. Inspect chain IDs, residue numbers, hetero residue names, and nucleic acid chains.
3. Use absolute paths in `input`.
4. Keep first trials small and explicit.
5. Use `prevalidate_inputs=True` before long GPU runs.

Common fields:

- `input`: PDB/CIF path.
- `contig`: design/motif layout such as `80-120,/0,A1-150`.
- `length`: design length or total length range.
- `select_hotspots`: target residues and atoms for binder interaction.
- `infer_ori_strategy`: use `hotspots` for PPI when hotspots define the desired interface.
- `is_non_loopy`: useful for PPI and NA examples to reduce loop-heavy designs.
- `select_unfixed_sequence`: input residues whose sequence can be redesigned.
- `ligand`: ligand residue name or selection for ligand-aware design.
- `select_fixed_atoms`: atoms to keep fixed; `ALL` fixes all atoms, `BKBN` fixes backbone, empty string/list allows flexibility depending on dialect/example style.
- `select_buried` / `select_exposed`: RASA-style conditioning for ligand or residue atoms.
- `unindex`: include motif residues without fixing their final sequence index.
- `ori_token`: desired center of mass/origin token for the diffused region.
- `partial_t`: partial-diffusion noise level.

`/0` in a contig marks a chain break. Always adapt examples to real chain IDs and residue numbers.

## Protein Binder

Use for target protein binder generation. Template:

```json
{
  "ppi_case": {
    "dialect": 2,
    "infer_ori_strategy": "hotspots",
    "input": "/absolute/path/to/target.pdb",
    "contig": "80-120,/0,A1-150",
    "length": "230-270",
    "select_hotspots": {
      "A35": "CD2,CZ",
      "A38": "CG,CZ",
      "A72": "CD1,CZ"
    },
    "is_non_loopy": true
  }
}
```

Command:

```bash
FOUNDRY_CHECKPOINT_DIRS=/path/to/foundry/checkpoints rfd3 design out_dir=/path/to/foundry/workspace/rfd3_runs/ppi_case/output inputs=/path/to/foundry/workspace/rfd3_runs/ppi_case/ppi_case.json prevalidate_inputs=True skip_existing=False diffusion_batch_size=1 n_batches=1 low_memory_mode=True dump_trajectories=False
```

Ask the user or infer from structure:

- Target chain and residue range.
- Hotspot residues and atoms; hotspots must be inside the contig-preserved target segment.
- Desired binder length and final complex length.

## Nucleic Acid Binder

Use for DNA/RNA binders or protein-nucleic acid contexts. Template:

```json
{
  "na_case": {
    "input": "/absolute/path/to/nucleic_acid_or_complex.pdb",
    "contig": "C5-18,/0,D24-37,/0,40-50,A146-154,80-90",
    "length": "157-177",
    "unindex": "/0,/0,B251-B255",
    "select_fixed_atoms": {
      "C9-14": "ALL",
      "D28-33": "ALL",
      "C5-8,C15-18": "",
      "D24-27,D34-37": ""
    },
    "ori_token": [25, 35, 20],
    "is_non_loopy": true
  }
}
```

Check PDB chain IDs carefully. Optional hydrogen-bond conditioning uses `select_hbond_acceptor` and `select_hbond_donor`, but the official tutorial notes that HBPLUS is required.

## Small Molecule Binder

Use when a ligand is present in the input structure and should guide pocket/binder generation. Template:

```json
{
  "sm_case": {
    "input": "/absolute/path/to/protein_ligand_complex.pdb",
    "length": "180-180",
    "ligand": "LIG",
    "select_fixed_atoms": {
      "LIG": ""
    },
    "select_buried": {
      "LIG": "C1,C2,N1,O1"
    },
    "select_exposed": {
      "LIG": "C10,C11"
    }
  }
}
```

Always inspect the real ligand residue name and atom names in the PDB/CIF before writing `ligand`, `select_buried`, or `select_exposed`.

## Enzyme Scaffold

Use when preserving catalytic residues, a functional motif, or ligand and generating a supporting scaffold. Template:

```json
{
  "enzyme_case": {
    "input": "/absolute/path/to/motif_with_ligand.pdb",
    "ligand": "LIG",
    "unindex": "A514,A531,A574,A579-581",
    "length": "100-200",
    "ori_token": [0, 1, 0],
    "select_fixed_atoms": {
      "A514": "NE2,CE1,ND1,CD2,CG,CB",
      "A531": "OD1,CG,OD2,CB",
      "A574": "NE2,CD,OE1,CG",
      "A579": "C,O,CA,N",
      "A580": "SG,CB,CA,N,C,O",
      "A581": "C,O,CA,N"
    },
    "select_buried": {
      "LIG": "O1,C8,O3,C4"
    },
    "select_exposed": {
      "LIG": "C2,C22,C19"
    },
    "select_unfixed_sequence": "A579,A581"
  }
}
```

Replace motif residues, ligand name, fixed atoms, and RASA atoms with real system-specific values. Use `unindex` when motif residues should preserve geometry but need not keep final sequence positions. Enzyme tasks are sensitive; run small batches and inspect structures manually.

## Partial Diffusion

Use to perturb or redesign around an existing structure. Template:

```json
{
  "partial_case": {
    "input": "/absolute/path/to/start_structure.pdb",
    "contig": "A1-120",
    "partial_t": 0.2
  }
}
```

Start with `partial_t` values like `0.1`, `0.2`, and `0.3`. Lower values stay closer to the input.

## Output Review

Expected outputs:

```text
<out_dir>/
  *_model_0.cif.gz
  *_model_0.json
```

First triage:

- Load `.cif.gz` in PyMOL.
- Check target/binder contacts or ligand pocket geometry.
- Read `.json` metadata for task name, input path, and checkpoint path.
- For promising designs, follow with RF3/MPNN, relaxation, docking, or short MD as appropriate.
