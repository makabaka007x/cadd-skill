#!/usr/bin/env python3
"""Build a standard GROMACS tREMD bundle from a YAML config."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

from optimize_remd_ladder import estimate_ladder, write_outputs as write_ladder_outputs
from render_postprocess_bundle import render_postprocess_bundle


VALID_SYSTEM_CLASSES = {"standard_protein", "protein_ligand"}


def read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} 不是有效的 YAML 字典。")
    return data


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def zero_width(nreplicas: int) -> int:
    return max(2, len(str(nreplicas - 1)))


def normalize_temperatures(cfg: dict[str, Any]) -> dict[str, Any]:
    ladder = cfg["temperature_ladder"]
    manual = ladder.get("temperatures") or []
    if manual:
        temps = [round(float(item), 2) for item in manual]
        require(len(temps) >= 2, "手动温度列表至少需要两个副本。")
        require(all(temps[idx] > temps[idx - 1] for idx in range(1, len(temps))), "手动温度列表必须严格递增。")
        result = {
            "tmin": temps[0],
            "tmax": temps[-1],
            "protein_atoms": int(ladder["protein_atoms"]),
            "water_molecules": int(ladder["water_molecules"]),
            "target_acceptance": float(ladder.get("target_acceptance", 0.25)),
            "relative_gap_estimate": None,
            "n_replicas": len(temps),
            "temperatures": temps,
            "deltas": [round(temps[idx] - temps[idx - 1], 2) for idx in range(1, len(temps))],
            "ratios": [round(temps[idx] / temps[idx - 1], 6) for idx in range(1, len(temps))],
            "note": "使用配置中提供的手动温度列表。",
        }
        return result

    return estimate_ladder(
        tmin=float(ladder["tmin"]),
        tmax=float(ladder["tmax"]),
        protein_atoms=int(ladder["protein_atoms"]),
        water_molecules=int(ladder["water_molecules"]),
        target_acceptance=float(ladder.get("target_acceptance", 0.25)),
    )


def detect_route(cfg: dict[str, Any]) -> str:
    system_class = cfg["project"]["system_class"]
    inputs = cfg["inputs"]
    prepared = inputs.get("prepared") or {}
    prepared_ready = bool(prepared.get("em_gro") and prepared.get("topol_top"))

    if system_class == "standard_protein":
        if prepared_ready:
            return "prepared_system"
        if inputs.get("protein_pdb"):
            return "protein_local_prep"
        raise ValueError("standard_protein 需要 prepared.em_gro + prepared.topol_top，或 protein_pdb。")

    if system_class == "protein_ligand":
        ligand = cfg.get("ligand") or {}
        if prepared_ready:
            return "prepared_system"
        if ligand.get("source") == "from_complex_pdb":
            require(bool(inputs.get("complex_pdb")), "ligand.source=from_complex_pdb 时必须提供 inputs.complex_pdb。")
            return "complex_local_prep"
        require(bool(inputs.get("protein_pdb")), "protein_ligand 外部配体模式需要 inputs.protein_pdb。")
        require(bool(ligand.get("ligand_file")), "protein_ligand 外部配体模式需要 ligand.ligand_file。")
        return "protein_plus_ligand_local_prep"

    raise ValueError(f"未知 system_class: {system_class}")


def copy_prepared_inputs(cfg: dict[str, Any], system_dir: Path, dry_run: bool) -> None:
    prepared = cfg["inputs"].get("prepared") or {}
    em_gro = prepared.get("em_gro")
    topol_top = prepared.get("topol_top")
    include_files = prepared.get("include_files") or []
    if not (em_gro and topol_top):
        return

    if dry_run:
        return

    src_em = Path(em_gro)
    src_top = Path(topol_top)
    require(src_em.exists(), f"找不到 prepared.em_gro: {src_em}")
    require(src_top.exists(), f"找不到 prepared.topol_top: {src_top}")
    shutil.copy2(src_em, system_dir / "1EM.gro")
    shutil.copy2(src_top, system_dir / "topol.top")

    for item in include_files:
        src = Path(item)
        require(src.exists(), f"找不到 include_files 条目: {src}")
        shutil.copy2(src, system_dir / src.name)


def render_standard_prep_script(cfg: dict[str, Any]) -> str:
    inputs = cfg["inputs"]
    ff = cfg["forcefield"]
    return f"""#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

GMX_EXEC="${{GMX_EXEC:-gmx}}"
INPUT_PDB="{inputs.get('protein_pdb', '')}"
BOX_DISTANCE="{inputs.get('box_distance_nm', 1.0)}"
FORCEFIELD="{ff['protein']}"
WATER="{ff['water']}"

mkdir -p ../system

"${{GMX_EXEC}}" pdb2gmx -f "${{INPUT_PDB}}" -o protein.gro -p ../system/topol.top -ignh -ff "${{FORCEFIELD}}" -water "${{WATER}}"
"${{GMX_EXEC}}" editconf -f protein.gro -o protein_box.gro -d "${{BOX_DISTANCE}}"
"${{GMX_EXEC}}" solvate -cp protein_box.gro -cs spc216.gro -o protein_wat.gro -p ../system/topol.top
"${{GMX_EXEC}}" grompp -f EM.mdp -c protein_wat.gro -p ../system/topol.top -o ions.tpr -maxwarn 99
printf 'SOL\\n' | "${{GMX_EXEC}}" genion -s ions.tpr -o solv_ions.gro -p ../system/topol.top -neutral
"${{GMX_EXEC}}" grompp -f EM.mdp -c solv_ions.gro -p ../system/topol.top -o ../system/1EM.tpr -maxwarn 99
"${{GMX_EXEC}}" mdrun -deffnm ../system/1EM -v
rm -f ions.tpr

echo "本地准备完成: ../system/1EM.gro 和 ../system/topol.top"
"""


def render_ligand_prep_scripts(cfg: dict[str, Any], route: str) -> tuple[str, str]:
    inputs = cfg["inputs"]
    ligand = cfg["ligand"]
    ff = cfg["forcefield"]

    if route == "complex_local_prep":
        ligand_extract = """grep '^ATOM' "${COMPLEX_PDB}" > protein_only.pdb
grep '^HETATM' "${COMPLEX_PDB}" > ligand_raw.pdb
"${OBABEL}" ligand_raw.pdb -O ligand_from_complex.sdf
LIGAND_INPUT="ligand_from_complex.sdf"
"""
    else:
        ligand_extract = f'LIGAND_INPUT="{ligand.get("ligand_file", "")}"\n'

    parameterize = f"""#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

ACPYPE="${{ACPYPE:-acpype}}"
OBABEL="${{OBABEL:-obabel}}"
COMPLEX_PDB="{inputs.get('complex_pdb', '')}"
{ligand_extract}

"${{ACPYPE}}" -i "${{LIGAND_INPUT}}" -n {ligand.get('ligand_charge', 'auto')} -c bcc
echo "配体参数化完成。请确认生成的 acpype 输出并把 ligand itp/include 文件并入 ../system/topol.top。"
"""

    prepare = f"""#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

GMX_EXEC="${{GMX_EXEC:-gmx}}"
BOX_DISTANCE="{inputs.get('box_distance_nm', 1.0)}"
FORCEFIELD="{ff['protein']}"
WATER="{ff['water']}"

mkdir -p ../system

if [[ -f "{inputs.get('complex_pdb', '')}" ]]; then
  grep '^ATOM' "{inputs.get('complex_pdb', '')}" > protein_only.pdb
else
  cp "{inputs.get('protein_pdb', '')}" protein_only.pdb
fi

"${{GMX_EXEC}}" pdb2gmx -f protein_only.pdb -o protein.gro -p ../system/topol.top -ignh -ff "${{FORCEFIELD}}" -water "${{WATER}}"
echo "下一步: 先运行 parameterize_ligand.sh，然后把 ACPYPE 生成的 ligand 拓扑 include 到 ../system/topol.top，并把蛋白与配体坐标合并成 complex_seed.gro。"
echo "完成后按标准流程继续：editconf -> solvate -> genion -> EM，最终把结果放到 ../system/1EM.gro。"
"${{GMX_EXEC}}" editconf -f protein.gro -o protein_box.gro -d "${{BOX_DISTANCE}}"
"""

    return parameterize, prepare


def render_step1_script(cfg: dict[str, Any], nreplicas: int) -> str:
    gpu = cfg["cluster"]["gpu"]
    width = zero_width(nreplicas)
    return f"""#!/usr/bin/env bash
#SBATCH -J tremd-step1
#SBATCH --partition={gpu['partition']}
#SBATCH --qos={gpu['qos']}
#SBATCH -N 1
#SBATCH --ntasks-per-node={gpu.get('ntasks_per_node', 1)}
#SBATCH --cpus-per-task={gpu['cpus_per_task']}
#SBATCH -o %j.out
#SBATCH -e %j.err

set -euo pipefail

cd "$(dirname "$0")/.."
module load {gpu['module']}
export OMP_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{gpu['cpus_per_task']}}}"

GMX_EXEC="{gpu.get('gmx_exec', 'gmx_mpi')}"
NREPLICAS={nreplicas}
WIDTH={width}

test -f system/1EM.gro
test -f system/topol.top

for idx in $(seq -f "%0${{WIDTH}}g" 0 $((NREPLICAS - 1))); do
  repdir="step1/replica_${{idx}}"
  "${{GMX_EXEC}}" grompp -f "${{repdir}}/PR.mdp" -c system/1EM.gro -r system/1EM.gro -p system/topol.top -o "${{repdir}}/2PR.tpr" -maxwarn 99
  "${{GMX_EXEC}}" mdrun -deffnm "${{repdir}}/2PR" -v

  "${{GMX_EXEC}}" grompp -f "${{repdir}}/NVT.mdp" -c "${{repdir}}/2PR.gro" -p system/topol.top -o "${{repdir}}/3NVT.tpr" -maxwarn 99
  "${{GMX_EXEC}}" mdrun -deffnm "${{repdir}}/3NVT" -v

  "${{GMX_EXEC}}" grompp -f "${{repdir}}/NPT.mdp" -c "${{repdir}}/3NVT.gro" -p system/topol.top -o "${{repdir}}/4NPT.tpr" -maxwarn 99
  "${{GMX_EXEC}}" mdrun -deffnm "${{repdir}}/4NPT" -v

  rm -f "${{repdir}}"/*.trr "${{repdir}}"/*.edr "${{repdir}}"/*.tpr "${{repdir}}"/*.log "${{repdir}}"/*.xtc "${{repdir}}"/#*
done
"""


def render_step2_script(cfg: dict[str, Any], nreplicas: int) -> str:
    gpu = cfg["cluster"]["gpu"]
    width = zero_width(nreplicas)
    deffnm = cfg["sampling"].get("deffnm", "5MD")
    return f"""#!/usr/bin/env bash
#SBATCH -J tremd-step2
#SBATCH --partition={gpu['partition']}
#SBATCH --qos={gpu['qos']}
#SBATCH -N 1
#SBATCH --ntasks-per-node={gpu.get('ntasks_per_node', 1)}
#SBATCH --cpus-per-task={gpu['cpus_per_task']}
#SBATCH -o %j.out
#SBATCH -e %j.err

set -euo pipefail

cd "$(dirname "$0")/.."
module load {gpu['module']}
export OMP_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{gpu['cpus_per_task']}}}"

GMX_EXEC="{gpu.get('gmx_exec', 'gmx_mpi')}"
NREPLICAS={nreplicas}
WIDTH={width}

for idx in $(seq -f "%0${{WIDTH}}g" 0 $((NREPLICAS - 1))); do
  repdir="step2/replica_${{idx}}"
  "${{GMX_EXEC}}" grompp -f "${{repdir}}/md.mdp" -c "step1/replica_${{idx}}/4NPT.gro" -p system/topol.top -o "${{repdir}}/{deffnm}.tpr" -maxwarn 99
done
"""


def render_run_script(cfg: dict[str, Any], nreplicas: int) -> str:
    cpu = cfg["cluster"]["cpu"]
    ntasks_per_node = cpu.get("ntasks_per_node", "auto")
    if ntasks_per_node == "auto":
        ntasks_per_node = nreplicas
    ntasks_per_node = int(ntasks_per_node)
    cpus_per_task = int(cpu.get("cpus_per_task", 1))
    max_total_tasks = cpu.get("max_total_tasks")
    if max_total_tasks is not None:
        max_total_cpus = int(max_total_tasks)
        requested_cpus = ntasks_per_node * cpus_per_task
        require(
            requested_cpus <= max_total_cpus,
            (
                f"CPU 生产任务请求 {requested_cpus} cores，超过当前 QOS "
                f"{cpu.get('qos')} 的 max_total_tasks={max_total_cpus}。"
            ),
        )

    width = zero_width(nreplicas)
    deffnm = cfg["sampling"].get("deffnm", "5MD")
    cpt_minutes = cfg["steps"]["production"].get("checkpoint_interval_minutes", 15)

    return f"""#!/usr/bin/env bash
#SBATCH -J tremd-run
#SBATCH --partition={cpu['partition']}
#SBATCH --qos={cpu['qos']}
#SBATCH -N 1
#SBATCH --ntasks-per-node={ntasks_per_node}
#SBATCH --cpus-per-task={cpu['cpus_per_task']}
#SBATCH -o %j.out
#SBATCH -e %j.err

set -euo pipefail

cd "$(dirname "$0")"
module load {cpu['module']}
export OMP_NUM_THREADS="${{SLURM_CPUS_PER_TASK:-{cpu['cpus_per_task']}}}"

MPI_LAUNCH="{cpu.get('mpi_launch', 'mpirun')}"
GMX_EXEC="{cpu.get('gmx_exec', 'gmx_mpi')}"
NREPLICAS={nreplicas}
WIDTH={width}
DEFFNM="{deffnm}"
STATE_FILE="{cfg['restart'].get('state_file', 'state.yaml')}"
CPT_INTERVAL_MIN={cpt_minutes}

eval "$(
python - "$STATE_FILE" <<'PY'
import sys
from pathlib import Path

state = {{}}
for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines():
    if ":" not in line:
        continue
    key, value = line.split(":", 1)
    state[key.strip()] = value.strip()
print(f"SEGMENT_STEPS={{state['segment_steps']}}")
print(f"SEGMENTS_TOTAL={{state['segments_total']}}")
print(f"SEGMENTS_COMPLETED={{state['segments_completed']}}")
PY
)"

if [[ "$SEGMENTS_COMPLETED" -ge "$SEGMENTS_TOTAL" ]]; then
  echo "state.yaml 显示所有 segment 已完成，无需继续。"
  exit 0
fi

declare -a REPLICA_DIRS=()
for idx in $(seq -f "%0${{WIDTH}}g" 0 $((NREPLICAS - 1))); do
  REPLICA_DIRS+=("step2/replica_${{idx}}")
done

for seg in $(seq $((SEGMENTS_COMPLETED + 1)) "$SEGMENTS_TOTAL"); do
  target_steps=$((seg * SEGMENT_STEPS))
  echo "=== Segment $seg / $SEGMENTS_TOTAL ==="

  for repdir in "${{REPLICA_DIRS[@]}}"; do
    "${{GMX_EXEC}}" convert-tpr -s "${{repdir}}/${{DEFFNM}}.tpr" -nsteps "$target_steps" -o "${{repdir}}/${{DEFFNM}}.segment.tpr"
    mv "${{repdir}}/${{DEFFNM}}.segment.tpr" "${{repdir}}/${{DEFFNM}}.tpr"
  done

  "${{MPI_LAUNCH}}" -np "$NREPLICAS" "${{GMX_EXEC}}" mdrun \
    -multidir "${{REPLICA_DIRS[@]}}" \
    -s "${{DEFFNM}}.tpr" \
    -deffnm "${{DEFFNM}}" \
    -cpi "${{DEFFNM}}.cpt" \
    -append \
    -cpt "$CPT_INTERVAL_MIN" \
    -replex {cfg['sampling'].get('replex', 250)} \
    -ntomp "${{SLURM_CPUS_PER_TASK:-{cpu['cpus_per_task']}}}"

  python - "$STATE_FILE" "$seg" "$SEGMENTS_TOTAL" "$SEGMENT_STEPS" "step2/replica_00/${{DEFFNM}}.cpt" <<'PY'
import sys
from pathlib import Path

state_path = Path(sys.argv[1])
segment = sys.argv[2]
segments_total = sys.argv[3]
segment_steps = sys.argv[4]
last_checkpoint = sys.argv[5]

state = {{}}
for line in state_path.read_text(encoding="utf-8").splitlines():
    if ":" not in line:
        continue
    key, value = line.split(":", 1)
    state[key.strip()] = value.strip()

state["segments_completed"] = segment
state["last_completed_segment"] = segment
state["segments_total"] = segments_total
state["segment_steps"] = segment_steps
state["last_checkpoint"] = last_checkpoint
state["status"] = "ready_for_resume" if int(segment) < int(segments_total) else "completed"

ordered = [
    "segments_total",
    "segments_completed",
    "segment_steps",
    "deffnm",
    "last_completed_segment",
    "last_checkpoint",
    "status",
]
state_path.write_text(
    "\\n".join(f"{{key}}: {{state[key]}}" for key in ordered if key in state) + "\\n",
    encoding="utf-8",
)
PY
done
"""


def render_upload_guide(cfg: dict[str, Any], route: str, nreplicas: int) -> str:
    return f"""# 上传与运行说明

## 目录定位

- 项目名: {cfg['project']['name']}
- system_class: {cfg['project']['system_class']}
- 输入路径模式: {route}
- 副本数: {nreplicas}

## 首跑顺序

1. 如果 `system/1EM.gro` 和 `system/topol.top` 还没有准备好，先进入 `prep/` 执行本地准备脚本。
2. 上传整个 bundle 到超算工作目录。
3. 提交 `step1/submit_step1.sh`。
4. 等 `step1` 完成后提交 `step2/submit_step2.sh`。
5. 等 `step2` 完成后提交 `run.sh`。

## 续跑怎么跑

- 当前设计是单 `run.sh` 分段续跑。
- 只要 `state.yaml` 里的 `segments_completed < segments_total`，重新执行：

```bash
sbatch run.sh
```

- `run.sh` 会自动读取 `state.yaml`，从下一个 segment 接着跑。
- 不需要改 `-cpi` 或手工改 checkpoint 名字。

## 想继续加长总采样时长

如果已经跑完当前总段数，但还想继续往后跑：

1. 打开 `state.yaml`
2. 把 `segments_total` 改成更大的数字
3. 再次提交 `sbatch run.sh`

例如当前总段数是 10，想再多跑 5 段，就把：

```yaml
segments_total: 10
```

改成：

```yaml
segments_total: 15
```

## state.yaml 含义

- `segments_total`: 当前计划总段数
- `segments_completed`: 已完成段数
- `segment_steps`: 每段步数
- `deffnm`: 正式生产前缀
- `last_completed_segment`: 最近成功完成的段号
- `last_checkpoint`: 最近 checkpoint 路径
- `status`: `ready_for_resume` 或 `completed`

## demux 与交换效率分析

正式生产后，进入 `analysis/`：

```bash
sbatch demux.sh
python remd_efficiency.py replica_index.xvg
./per_temperature_analysis.sh
```

## 默认约束

- 当前 bundle 默认不写 `#SBATCH --time`
- 当前 bundle 默认不使用 `-maxh`
- 生产续跑依赖 `-cpi -append + state.yaml`
"""


def write_mdp_templates(bundle_dir: Path, temperatures: list[float]) -> None:
    asset_templates = Path(__file__).resolve().parent.parent / "assets" / "templates"
    width = zero_width(len(temperatures))

    for idx, temp in enumerate(temperatures):
        rep = f"replica_{idx:0{width}d}"
        step1_dir = bundle_dir / "step1" / rep
        step2_dir = bundle_dir / "step2" / rep
        step1_dir.mkdir(parents=True, exist_ok=True)
        step2_dir.mkdir(parents=True, exist_ok=True)

        for name in ("PR", "NVT", "NPT"):
            content = (asset_templates / f"{name}.mdp").read_text(encoding="utf-8").replace("TEMP", f"{temp:.2f}")
            (step1_dir / f"{name}.mdp").write_text(content, encoding="utf-8")

        md_content = (asset_templates / "md.mdp").read_text(encoding="utf-8").replace("TEMP", f"{temp:.2f}")
        (step2_dir / "md.mdp").write_text(md_content, encoding="utf-8")

    shutil.copy2(asset_templates / "EM.mdp", bundle_dir / "prep" / "EM.mdp")


def validate_config(cfg: dict[str, Any]) -> None:
    require("project" in cfg, "缺少 project 配置块。")
    require("sampling" in cfg, "缺少 sampling 配置块。")
    require("inputs" in cfg, "缺少 inputs 配置块。")
    require("forcefield" in cfg, "缺少 forcefield 配置块。")
    require("temperature_ladder" in cfg, "缺少 temperature_ladder 配置块。")
    require("cluster" in cfg and "gpu" in cfg["cluster"] and "cpu" in cfg["cluster"], "缺少 cluster.gpu 或 cluster.cpu 配置。")
    require("steps" in cfg and "production" in cfg["steps"], "缺少 steps.production 配置。")
    require("restart" in cfg, "缺少 restart 配置块。")

    sampling_mode = cfg["sampling"].get("mode")
    if sampling_mode != "tremd":
        raise ValueError("当前 v1 只支持 sampling.mode=tremd。REST2/HREMD 仅为未来保留接口。")

    system_class = cfg["project"].get("system_class")
    require(system_class in VALID_SYSTEM_CLASSES, f"当前 v1 只支持 {sorted(VALID_SYSTEM_CLASSES)}。")


def build_bundle(config_path: Path, output_dir: Path | None, dry_run: bool, force: bool) -> Path:
    cfg = read_yaml(config_path)
    validate_config(cfg)
    route = detect_route(cfg)

    bundle_dir = Path(output_dir or cfg["project"].get("output_dir") or f"./{cfg['project']['name']}_bundle").resolve()
    if bundle_dir.exists():
        if not force:
            raise ValueError(f"输出目录已存在: {bundle_dir}。如需覆盖请使用 --force。")
        shutil.rmtree(bundle_dir)

    for subdir in ("prep", "system", "step1", "step2", "analysis"):
        (bundle_dir / subdir).mkdir(parents=True, exist_ok=True)

    ladder = normalize_temperatures(cfg)
    temperatures = ladder["temperatures"]
    nreplicas = len(temperatures)

    write_ladder_outputs(ladder, bundle_dir, "temperatures")
    write_mdp_templates(bundle_dir, temperatures)

    resolved_config = dict(cfg)
    resolved_config["temperature_ladder"] = dict(cfg["temperature_ladder"])
    resolved_config["temperature_ladder"]["temperatures"] = temperatures
    resolved_config["temperature_ladder"]["n_replicas"] = nreplicas
    (bundle_dir / "bundle_config.yaml").write_text(
        yaml.safe_dump(resolved_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    system_dir = bundle_dir / "system"
    copy_prepared_inputs(cfg, system_dir, dry_run=dry_run)

    route_file = bundle_dir / "prep" / "prepare_local.sh"
    if route == "protein_local_prep":
        route_file.write_text(render_standard_prep_script(cfg), encoding="utf-8")
        route_file.chmod(0o755)
    elif route in {"complex_local_prep", "protein_plus_ligand_local_prep"}:
        parameterize, prepare = render_ligand_prep_scripts(cfg, route)
        route_file.write_text(prepare, encoding="utf-8")
        route_file.chmod(0o755)
        ligand_script = bundle_dir / "prep" / "parameterize_ligand.sh"
        ligand_script.write_text(parameterize, encoding="utf-8")
        ligand_script.chmod(0o755)

    state_text = "\n".join(
        [
            f"segments_total: {cfg['steps']['production']['total_segments']}",
            "segments_completed: 0",
            f"segment_steps: {cfg['steps']['production']['segment_steps']}",
            f"deffnm: {cfg['sampling'].get('deffnm', '5MD')}",
            "last_completed_segment: 0",
            f"last_checkpoint: step2/replica_00/{cfg['sampling'].get('deffnm', '5MD')}.cpt",
            "status: ready_for_resume",
            "",
        ]
    )
    (bundle_dir / cfg["restart"].get("state_file", "state.yaml")).write_text(state_text, encoding="utf-8")

    step1_script = bundle_dir / "step1" / "submit_step1.sh"
    step1_script.write_text(render_step1_script(cfg, nreplicas), encoding="utf-8")
    step1_script.chmod(0o755)

    step2_script = bundle_dir / "step2" / "submit_step2.sh"
    step2_script.write_text(render_step2_script(cfg, nreplicas), encoding="utf-8")
    step2_script.chmod(0o755)

    run_script = bundle_dir / "run.sh"
    run_script.write_text(render_run_script(cfg, nreplicas), encoding="utf-8")
    run_script.chmod(0o755)

    (bundle_dir / "UPLOAD_AND_RUN.md").write_text(render_upload_guide(cfg, route, nreplicas), encoding="utf-8")

    if cfg.get("postprocess", {}).get("enabled", True):
        render_postprocess_bundle(
            bundle_dir=bundle_dir,
            nreplicas=nreplicas,
            deffnm=cfg["sampling"].get("deffnm", "5MD"),
            module_name=cfg["cluster"]["cpu"]["module"],
            gmx_exec=cfg["cluster"]["cpu"].get("gmx_exec", "gmx_mpi"),
            cpu_partition=cfg["cluster"]["cpu"]["partition"],
            cpu_qos=cfg["cluster"]["cpu"]["qos"],
            temperatures=temperatures,
        )

    manifest = {
        "route": route,
        "dry_run": dry_run,
        "n_replicas": nreplicas,
        "bundle_dir": str(bundle_dir),
        "temperature_yaml": str(bundle_dir / "temperatures.yaml"),
    }
    (bundle_dir / "bundle_manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return bundle_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="根据 YAML 配置生成 GROMACS tREMD 运行包。")
    parser.add_argument("config", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        bundle_dir = build_bundle(args.config, args.output_dir, args.dry_run, args.force)
    except Exception as exc:  # noqa: BLE001
        print(f"生成 bundle 失败: {exc}", file=sys.stderr)
        return 1

    print(f"已生成 bundle: {bundle_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
