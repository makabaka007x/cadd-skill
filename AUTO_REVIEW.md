# Auto Review

## Round 1 - Public Skill Release Audit

### Scope

Prepared and reviewed seven CADD/AIDD skills for public release:

- `amber-md-expert`
- `hdock`
- `haddock`
- `gmx-workflow-packer`
- `unidock-pro`
- `rfdiffusion3`
- `af-analysis`

### Checks Run

- Skill structure validation with `quick_validate.py`
- Python syntax compilation for bundled Python scripts
- Sensitive string scan for local user paths, WSL mount paths, account names, common API key and private key markers
- Generated-cache scan for `__pycache__`
- Large-file scan for files over 1 MB
- Git whitespace check with `git diff --check`

### Findings

1. `af-analysis/SKILL.md` used unsupported frontmatter keys: `author`, `version`, and `date`.
2. Python syntax compilation generated local `__pycache__` directories.
3. Several public files contained machine-specific install paths and one HPC account reference before sanitization.
4. Final sensitive scan still reports two `token` matches, both ordinary local variable names in source code, not credentials.

### Actions Taken

- Moved `af-analysis` metadata under the allowed `metadata` frontmatter key.
- Replaced local install paths with public placeholders such as `/path/to/UniDock-Pro`, `/path/to/haddock2.5`, and `/path/to/foundry/checkpoints`.
- Replaced the HPC account reference with `<your-hpc-account>`.
- Removed generated `__pycache__` directories.
- Added `.gitignore` for Python caches, env files, logs, archives, and common biomolecular trajectory/structure files.
- Added a top-level `README.md` explaining included skills, install commands, local configuration, and sanitization scope.

### Final Status

Ready to publish.

Validation status:

- 7/7 skills passed `quick_validate.py`.
- Python script syntax check passed.
- No generated caches remain.
- No files larger than 1 MB were found.
- `git diff --check` passed.
- No credential-like secrets were found by the final scan.
