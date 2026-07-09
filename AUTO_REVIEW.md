# Auto Review

## Round 2 - Public Skill Collection Audit

### Scope

Prepared and reviewed thirteen CADD/AIDD skills for public release:

- `af-analysis`
- `amber-md-expert`
- `bindingdb-skill`
- `chebi-skill`
- `chembl-skill`
- `gmx-workflow-packer`
- `haddock`
- `hdock`
- `pubchem-pug-skill`
- `rcsb-pdb-skill`
- `rfdiffusion3`
- `unidock-pro`
- `uniprot-skill`

### Checks Run

- Skill structure validation with `quick_validate.py`
- Python syntax compilation for bundled Python scripts
- Sensitive string scan for local user paths, WSL mount paths, account names, common API key and private key markers
- Conventional GROMACS MD bundle dry-run
- Boltz directory exclusion check
- Generated-cache scan for `__pycache__`
- Large-file scan for files over 1 MB
- Git whitespace check with `git diff --check`

### Findings

1. `af-analysis/SKILL.md` and `haddock/SKILL.md` had unsupported frontmatter fields before cleanup.
2. Several existing skills contained machine-specific GPU, WSL, and cluster defaults before sanitization.
3. `gmx-workflow-packer` originally focused on tREMD/REST2 and now also supports conventional MD packaging.
4. Sensitive scans still report ordinary code variables such as `token` and public safety warnings about API keys; these are not credentials.

### Actions Taken

- Removed unsupported frontmatter fields from `af-analysis` and `haddock`.
- Replaced local install paths, specific cluster partitions/QOS names, GPU model assumptions, and project-specific examples with public placeholders.
- Added public database skills for PubChem, ChEMBL, BindingDB, RCSB PDB, UniProt, and ChEBI.
- Added conventional GROMACS MD support through `assets/md-config-template.yaml` and `scripts/build_md_bundle.py`.
- Rewrote English and Chinese README files with quick selectors, install commands, and combined workflow examples.

### Final Status

Ready to publish after commit and push.

Validation status:

- 13/13 skills passed `quick_validate.py`.
- Python script syntax check passed.
- Conventional GROMACS MD dry-run generated the expected bundle files under `/tmp`.
- No Boltz skill directories are included.
- No credential-like secrets were found by the final scan; remaining matches are public safety warnings or ordinary code variable names.
