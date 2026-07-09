#!/usr/bin/env python3
"""Build a conventional GROMACS MD bundle from a YAML config."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

import yaml


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"


def read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a YAML mapping.")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def render_mdp(template_name: str, temperature: float, nsteps: int | None = None) -> str:
    text = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8")
    text = text.replace("TEMP", f"{temperature:.2f}")
    if nsteps is not None:
        lines = []
        replaced = False
        for line in text.splitlines():
            if line.strip().startswith("nsteps"):
                lines.append(f"nsteps                  = {int(nsteps)}")
                replaced = True
            else:
                lines.append(line)
        text = "\n".join(lines) + "\n"
        require(replaced, f"{template_name} has no nsteps field.")
    return text


def copy_prepared_inputs(cfg: dict[str, Any], system_dir: Path, dry_run: bool) -> bool:
    prepared = (cfg.get("inputs") or {}).get("prepared") or {}
    em_gro = prepared.get("em_gro")
    topol_top = prepared.get("topol_top")
    include_files = prepared.get("include_files") or []
    if not (em_gro and topol_top):
        return False

    if dry_run:
        return True

    src_gro = Path(em_gro)
    src_top = Path(topol_top)
    require(src_gro.exists(), f"prepared.em_gro not found: {src_gro}")
    require(src_top.exists(), f"prepared.topol_top not found: {src_top}")
    shutil.copy2(src_gro, system_dir / "1EM.gro")
    shutil.copy2(src_top, system_dir / "topol.top")

    for item in include_files:
        src = Path(item)
        require(src.exists(), f"include_files entry not found: {src}")
        shutil.copy2(src, system_dir / src.name)
    return True


def render_prepare_script(cfg: dict[str, Any]) -> str:
    inputs = cfg.get("inputs") or {}
    ff = cfg.get("forcefield") or {}
    return f"""#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

GMX_EXEC="${{GMX_EXEC:-gmx}}"
INPUT_PDB="{inputs.get('protein_pdb', '')}"
BOX_DISTANCE="{inputs.get('box_distance_nm', 1.0)}"
FORCEFIELD="{ff.get('protein', 'amber99sb-ildn')}"
WATER="{ff.get('water', 'tip3p')}"
ION_CONC="{inputs.get('ion_concentration_molar', 0.15)}"

mkdir -p ../system
test -n "$INPUT_PDB"
test -f "$INPUT_PDB"

"${{GMX_EXEC}}" pdb2gmx -f "$INPUT_PDB" -o protein.gro -p ../system/topol.top -ignh -ff "$FORCEFIELD" -water "$WATER"
"${{GMX_EXEC}}" editconf -f protein.gro -o protein_box.gro -d "$BOX_DISTANCE"
"${{GMX_EXEC}}" solvate -cp protein_box.gro -cs spc216.gro -o protein_wat.gro -p ../system/topol.top
"${{GMX_EXEC}}" grompp -f ../mdp/EM.mdp -c protein_wat.gro -p ../system/topol.top -o ions.tpr -maxwarn 1
printf 'SOL\\n' | "${{GMX_EXEC}}" genion -s ions.tpr -o solv_ions.gro -p ../system/topol.top -neutral -conc "$ION_CONC"
"${{GMX_EXEC}}" grompp -f ../mdp/EM.mdp -c solv_ions.gro -p ../system/topol.top -o ../run/EM.tpr -maxwarn 1
"${{GMX_EXEC}}" mdrun -deffnm ../run/EM -v
cp ../run/EM.gro ../system/1EM.gro

echo "Prepared system/1EM.gro and system/topol.top"
"""


def render_run_script(cfg: dict[str, Any]) -> str:
    cluster = ((cfg.get("cluster") or {}).get("gpu") or {})
    sampling = cfg.get("sampling") or {}
    steps = cfg.get("steps") or {}
    maxwarn = int(sampling.get("maxwarn", 1))
    deffnm = sampling.get("deffnm", "md")
    cpt = int(steps.get("checkpoint_interval_minutes", 15))
    return f"""#!/usr/bin/env bash
#SBATCH -J gmx-md
#SBATCH --partition={cluster.get('partition', 'gpu')}
#SBATCH --qos={cluster.get('qos', 'gpu')}
#SBATCH -N 1
#SBATCH --ntasks-per-node={cluster.get('ntasks_per_node', 1)}
#SBATCH --cpus-per-task={cluster.get('cpus_per_task', 4)}
#SBATCH --gres=gpu:1
#SBATCH -o %j.out
#SBATCH -e %j.err

set -euo pipefail

cd "$(dirname "$0")"
module load {cluster.get('module', 'gromacs')}
export OMP_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{cluster.get('cpus_per_task', 4)}}}"

GMX_EXEC="${{GMX_EXEC:-{cluster.get('gmx_exec', 'gmx')}}}"
MAXWARN={maxwarn}
DEFFNM="{deffnm}"
CPT_INTERVAL_MIN={cpt}

test -f system/1EM.gro
test -f system/topol.top

mkdir -p run

"${{GMX_EXEC}}" grompp -f mdp/PR.mdp -c system/1EM.gro -r system/1EM.gro -p system/topol.top -o run/PR.tpr -maxwarn "$MAXWARN"
"${{GMX_EXEC}}" mdrun -deffnm run/PR -v -cpt "$CPT_INTERVAL_MIN"

"${{GMX_EXEC}}" grompp -f mdp/NVT.mdp -c run/PR.gro -p system/topol.top -o run/NVT.tpr -maxwarn "$MAXWARN"
"${{GMX_EXEC}}" mdrun -deffnm run/NVT -v -cpt "$CPT_INTERVAL_MIN"

"${{GMX_EXEC}}" grompp -f mdp/NPT.mdp -c run/NVT.gro -p system/topol.top -o run/NPT.tpr -maxwarn "$MAXWARN"
"${{GMX_EXEC}}" mdrun -deffnm run/NPT -v -cpt "$CPT_INTERVAL_MIN"

if [[ -f "run/${{DEFFNM}}.cpt" ]]; then
  "${{GMX_EXEC}}" mdrun -deffnm "run/${{DEFFNM}}" -v -cpi "run/${{DEFFNM}}.cpt" -append -cpt "$CPT_INTERVAL_MIN"
else
  "${{GMX_EXEC}}" grompp -f mdp/md.mdp -c run/NPT.gro -p system/topol.top -o "run/${{DEFFNM}}.tpr" -maxwarn "$MAXWARN"
  "${{GMX_EXEC}}" mdrun -deffnm "run/${{DEFFNM}}" -v -cpt "$CPT_INTERVAL_MIN"
fi

python3 - <<'PY'
from pathlib import Path
Path("state.yaml").write_text("mode: md\\nstatus: completed_or_resumable\\nlast_checkpoint: run/{deffnm}.cpt\\n", encoding="utf-8")
PY
"""


def render_analysis_script(cfg: dict[str, Any]) -> str:
    deffnm = (cfg.get("sampling") or {}).get("deffnm", "md")
    return f"""#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
GMX_EXEC="${{GMX_EXEC:-gmx}}"
DEFFNM="{deffnm}"

mkdir -p analysis

cat > analysis/README.md <<'EOF'
# Basic GROMACS MD Analysis

Run these commands interactively and choose the appropriate index groups for the system.

```bash
gmx trjconv -s run/md.tpr -f run/md.xtc -o analysis/md_center.xtc -pbc mol -center
gmx rms -s run/md.tpr -f analysis/md_center.xtc -o analysis/rmsd.xvg
gmx gyrate -s run/md.tpr -f analysis/md_center.xtc -o analysis/rog.xvg
gmx hbond -s run/md.tpr -f analysis/md_center.xtc -num analysis/hbond.xvg
```
EOF

echo "Wrote analysis/README.md. Run the listed commands interactively so index-group choices match the actual system."
"""


def render_upload_guide(cfg: dict[str, Any], prepared_ready: bool) -> str:
    return f"""# GROMACS MD Upload and Run Guide

## Bundle

- Project: {cfg['project']['name']}
- Mode: conventional MD
- Prepared system copied: {str(prepared_ready).lower()}

## First Run

1. If `system/1EM.gro` and `system/topol.top` are missing, run:

```bash
bash prep/prepare_standard_system.sh
```

2. Edit `run.sh` for the target cluster partition, QOS, module, account, GPU/CPU resources, and wall-time policy.

3. Submit:

```bash
sbatch run.sh
```

## Resume

Re-submit `run.sh`. If `run/{cfg.get('sampling', {}).get('deffnm', 'md')}.cpt` exists, production resumes with `-cpi -append`.

## Basic Analysis

```bash
bash analysis/basic_analysis.sh
```

The analysis script writes an interactive command checklist. Choose index groups according to the actual system.
"""


def build_bundle(config_path: Path, dry_run: bool, force: bool) -> Path:
    cfg = read_yaml(config_path)
    require((cfg.get("sampling") or {}).get("mode") == "md", "sampling.mode must be md.")
    out_dir = Path(cfg["project"]["output_dir"]).resolve()
    if out_dir.exists():
        if not force:
            raise FileExistsError(f"{out_dir} exists. Use --force to replace it.")
        shutil.rmtree(out_dir)

    for subdir in ["system", "prep", "mdp", "run", "analysis"]:
        (out_dir / subdir).mkdir(parents=True, exist_ok=True)

    temperature = float((cfg.get("sampling") or {}).get("temperature", 300.0))
    steps = cfg.get("steps") or {}
    mdp_specs = [
        ("EM.mdp", None),
        ("PR.mdp", steps.get("pr_nsteps")),
        ("NVT.mdp", steps.get("nvt_nsteps")),
        ("NPT.mdp", steps.get("npt_nsteps")),
        ("md.mdp", steps.get("md_nsteps")),
    ]
    for name, nsteps in mdp_specs:
        (out_dir / "mdp" / name).write_text(render_mdp(name, temperature, nsteps), encoding="utf-8")

    prepared_ready = copy_prepared_inputs(cfg, out_dir / "system", dry_run)
    (out_dir / "prep" / "prepare_standard_system.sh").write_text(render_prepare_script(cfg), encoding="utf-8")
    (out_dir / "run.sh").write_text(render_run_script(cfg), encoding="utf-8")
    (out_dir / "analysis" / "basic_analysis.sh").write_text(render_analysis_script(cfg), encoding="utf-8")
    (out_dir / "UPLOAD_AND_RUN.md").write_text(render_upload_guide(cfg, prepared_ready), encoding="utf-8")
    (out_dir / "state.yaml").write_text("mode: md\nstatus: not_started\n", encoding="utf-8")
    shutil.copy2(config_path, out_dir / "bundle-config.yaml")

    for script in [
        out_dir / "prep" / "prepare_standard_system.sh",
        out_dir / "run.sh",
        out_dir / "analysis" / "basic_analysis.sh",
    ]:
        script.chmod(script.stat().st_mode | 0o111)

    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Create scripts without requiring prepared input files.")
    parser.add_argument("--force", action="store_true", help="Replace an existing output directory.")
    args = parser.parse_args()

    out_dir = build_bundle(args.config, dry_run=args.dry_run, force=args.force)
    print(out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
