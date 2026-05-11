#!/usr/bin/env python3
"""Build a GROMACS/PLUMED REST2 v2 bundle from a YAML config."""

from __future__ import annotations

import argparse
import csv
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

from render_postprocess_bundle import render_postprocess_bundle


VALID_SYSTEM_CLASSES = {"standard_protein", "protein_ligand"}
VALID_HOT_REGIONS = {"protein", "solute", "custom_atom_ids"}


MARK_HOT_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def parse_csv_ints(text: str) -> set[int]:
    if not text.strip():
        return set()
    result = set()
    for token in text.replace(";", ",").split(","):
        token = token.strip()
        if token:
            result.add(int(token))
    return result


def parse_names(text: str) -> set[str]:
    return {token.strip().upper() for token in text.replace(";", ",").split(",") if token.strip()}


def should_mark(
    atom_id: int,
    residue: str,
    hot_region: str,
    hot_atom_ids: set[int],
    hot_residue_names: set[str],
    solvent_residue_names: set[str],
) -> bool:
    residue_name = residue.upper()
    if atom_id in hot_atom_ids:
        return True
    if hot_residue_names:
        return residue_name in hot_residue_names
    if hot_region == "custom_atom_ids":
        return atom_id in hot_atom_ids
    if hot_region in {"protein", "solute"}:
        return residue_name not in solvent_residue_names
    return False


def mark_topology(
    input_top: Path,
    output_top: Path,
    hot_region: str,
    hot_atom_ids: set[int],
    hot_residue_names: set[str],
    solvent_residue_names: set[str],
) -> int:
    section = None
    marked = 0
    out_lines: list[str] = []

    for raw in input_top.read_text(encoding="utf-8").splitlines():
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped.strip("[]").strip().lower()
            out_lines.append(raw)
            continue
        if section != "atoms" or not stripped or stripped.startswith(("#", ";")):
            out_lines.append(raw)
            continue

        main, sep, comment = raw.partition(";")
        parts = main.split()
        if len(parts) < 8:
            out_lines.append(raw)
            continue

        try:
            atom_id = int(parts[0])
        except ValueError:
            out_lines.append(raw)
            continue

        residue = parts[3]
        if should_mark(atom_id, residue, hot_region, hot_atom_ids, hot_residue_names, solvent_residue_names):
            if not parts[1].endswith("_"):
                parts[1] = parts[1] + "_"
                marked += 1
            head = "{:>8s} {:<14s} {:>6s} {:<8s} {:<8s} {:>6s} {:>14s} {:>12s}".format(*parts[:8])
            if len(parts) > 8:
                head += " " + " ".join(parts[8:])
            out_lines.append(head + (f" ;{comment}" if sep else ""))
        else:
            out_lines.append(raw)

    output_top.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return marked


def main() -> int:
    parser = argparse.ArgumentParser(description="Mark REST2 hot atoms in a processed GROMACS topology.")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hot-region", choices=("protein", "solute", "custom_atom_ids"), default="protein")
    parser.add_argument("--hot-atom-ids", default="")
    parser.add_argument("--hot-residue-names", default="")
    parser.add_argument("--solvent-residue-names", default="SOL,WAT,HOH,TIP3,NA,CL,K,CA,MG,ZN")
    args = parser.parse_args()

    hot_atom_ids = parse_csv_ints(args.hot_atom_ids)
    if args.hot_region == "custom_atom_ids" and not hot_atom_ids:
        raise SystemExit("hot-region=custom_atom_ids requires --hot-atom-ids.")

    marked = mark_topology(
        input_top=args.input,
        output_top=args.output,
        hot_region=args.hot_region,
        hot_atom_ids=hot_atom_ids,
        hot_residue_names=parse_names(args.hot_residue_names),
        solvent_residue_names=parse_names(args.solvent_residue_names),
    )
    print(f"Marked hot atoms: {marked}")
    if marked == 0:
        raise SystemExit("No hot atoms were marked. Check hot-region or residue names.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


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


def geometric_temperatures(tmin: float, tmax: float, nreplicas: int) -> list[float]:
    require(nreplicas >= 2, "REST2 至少需要两个 replica。")
    require(tmin > 0 and tmax > tmin, "REST2 tmin/tmax 必须满足 0 < tmin < tmax。")
    return [
        round(tmin * math.exp(idx * math.log(tmax / tmin) / (nreplicas - 1)), 2)
        for idx in range(nreplicas)
    ]


def normalize_rest2_ladder(cfg: dict[str, Any]) -> dict[str, Any]:
    rest2 = cfg["rest2"]
    manual = rest2.get("effective_temperatures") or []
    if manual:
        temps = [round(float(item), 2) for item in manual]
    else:
        temps = geometric_temperatures(
            tmin=float(rest2.get("tmin", rest2.get("reference_temperature", 300.0))),
            tmax=float(rest2["tmax"]),
            nreplicas=int(rest2["n_replicas"]),
        )
    require(len(temps) >= 2, "REST2 effective_temperatures 至少需要两个 replica。")
    require(all(temps[idx] > temps[idx - 1] for idx in range(1, len(temps))), "REST2 effective_temperatures 必须严格递增。")

    reference = float(rest2.get("reference_temperature") or temps[0])
    scales = [round(reference / temp, 8) for temp in temps]
    return {
        "reference_temperature": round(reference, 2),
        "n_replicas": len(temps),
        "effective_temperatures": temps,
        "scales": scales,
        "note": "REST2 effective temperature ladder; thermostat reference temperature remains constant.",
    }


def choose_nstlist(replex: int, requested: int | None) -> int:
    if requested:
        require(replex % requested == 0, f"REST2 要求 nstlist 能整除 replex；当前 replex={replex}, nstlist={requested}。")
        return requested
    for candidate in (25, 20, 10, 5, 1):
        if replex % candidate == 0:
            return candidate
    return 1


def set_mdp_value(text: str, key: str, value: str | int | float) -> str:
    lines = text.splitlines()
    replaced = False
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f"{key}") and "=" in stripped.split(";", 1)[0]:
            lines[idx] = f"{key:<24} = {value}"
            replaced = True
    if not replaced:
        lines.append(f"{key:<24} = {value}")
    return "\n".join(lines) + "\n"


def render_rest2_mdp(reference_temperature: float, nsteps: int, nstlist: int) -> str:
    template = Path(__file__).resolve().parent.parent / "assets" / "templates" / "md.mdp"
    text = template.read_text(encoding="utf-8").replace("TEMP", f"{reference_temperature:.2f}")
    for key, value in (
        ("nsteps", nsteps),
        ("nstlist", nstlist),
        ("ref-t", f"{reference_temperature:.2f}"),
        ("gen-vel", "no"),
        ("continuation", "yes"),
    ):
        text = set_mdp_value(text, key, value)
    return text


def write_rest2_tables(bundle_dir: Path, ladder: dict[str, Any]) -> None:
    rest2_dir = bundle_dir / "rest2"
    rest2_dir.mkdir(parents=True, exist_ok=True)
    with (rest2_dir / "rest2_scales.tsv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["replica", "effective_temperature_k", "scale"])
        width = zero_width(ladder["n_replicas"])
        for idx, (temp, scale) in enumerate(zip(ladder["effective_temperatures"], ladder["scales"], strict=True)):
            writer.writerow([f"replica_{idx:0{width}d}", f"{temp:.2f}", f"{scale:.8f}"])

    (bundle_dir / "rest2_ladder.yaml").write_text(
        yaml.safe_dump(ladder, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def copy_prepared_inputs(cfg: dict[str, Any], system_dir: Path, dry_run: bool) -> None:
    prepared = cfg["inputs"].get("prepared") or {}
    if dry_run:
        return

    for key, target in (("em_gro", "1EM.gro"), ("topol_top", "topol.top")):
        src = Path(prepared[key])
        require(src.exists(), f"找不到 inputs.prepared.{key}: {src}")
        shutil.copy2(src, system_dir / target)

    for item in prepared.get("include_files") or []:
        src = Path(item)
        require(src.exists(), f"找不到 include_files 条目: {src}")
        shutil.copy2(src, system_dir / src.name)


def write_plumed_template(cfg: dict[str, Any], prep_dir: Path, dry_run: bool) -> None:
    value = str(cfg["rest2"].get("plumed_dat", "empty"))
    target = prep_dir / "plumed.dat.template"
    if value.lower() in {"", "empty", "none"}:
        target.write_text("# Empty PLUMED input required by GROMACS -hrex.\n", encoding="utf-8")
        return

    src = Path(value)
    if src.exists():
        shutil.copy2(src, target)
    elif dry_run:
        target.write_text(f"# Dry-run placeholder. Original plumed_dat was not found: {src}\n", encoding="utf-8")
    else:
        raise ValueError(f"找不到 rest2.plumed_dat: {src}")


def render_prepare_script(cfg: dict[str, Any], ladder: dict[str, Any], nstlist: int) -> str:
    gpu = cfg["cluster"]["gpu"]
    sampling = cfg["sampling"]
    rest2 = cfg["rest2"]
    hot_atom_ids = ",".join(str(item) for item in rest2.get("hot_atom_ids") or [])
    hot_residue_names = ",".join(str(item) for item in rest2.get("hot_residue_names") or [])
    solvent_residue_names = ",".join(str(item) for item in rest2.get("solvent_residue_names") or [])
    return f"""#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
module load {gpu['module']}

GMX_EXEC="${{GMX_EXEC:-{gpu.get('gmx_exec', 'gmx_mpi')}}}"
PLUMED="${{PLUMED:-plumed}}"
DEFFNM="{sampling.get('deffnm', '5MD')}"
MAXWARN="${{MAXWARN:-99}}"

test -f system/1EM.gro
test -f system/topol.top
test -f prep/plumed.dat.template

"${{GMX_EXEC}}" grompp \\
  -f prep/rest2_preprocess.mdp \\
  -c system/1EM.gro \\
  -p system/topol.top \\
  -o prep/rest2_preprocess.tpr \\
  -pp prep/processed.top \\
  -maxwarn "$MAXWARN"

python prep/mark_rest2_hot_atoms.py \\
  --input prep/processed.top \\
  --output prep/processed_hot.top \\
  --hot-region "{rest2.get('hot_region', 'protein')}" \\
  --hot-atom-ids "{hot_atom_ids}" \\
  --hot-residue-names "{hot_residue_names}" \\
  --solvent-residue-names "{solvent_residue_names}"

while IFS=$'\\t' read -r replica effective_temp scale; do
  [[ "$replica" == "replica" ]] && continue
  repdir="rest2/${{replica}}"
  test -d "$repdir"
  "$PLUMED" partial_tempering "$scale" < prep/processed_hot.top > "$repdir/topol.top"
  cp prep/plumed.dat.template "$repdir/plumed.dat"
  "${{GMX_EXEC}}" grompp \\
    -f "$repdir/md.mdp" \\
    -c system/1EM.gro \\
    -p "$repdir/topol.top" \\
    -o "$repdir/${{DEFFNM}}.tpr" \\
    -maxwarn "$MAXWARN"
done < rest2/rest2_scales.tsv

echo "REST2 拓扑和 tpr 准备完成。reference_temperature={ladder['reference_temperature']:.2f} K, nstlist={nstlist}。"
"""


def hrex_available(cfg: dict[str, Any]) -> bool:
    rest2 = cfg.get("rest2") or {}
    cluster = cfg.get("cluster") or {}
    capabilities = cluster.get("capabilities") or {}
    if "hrex_available" in rest2:
        return bool(rest2["hrex_available"])
    return bool(capabilities.get("has_hrex", False))


def render_capability_check_script(cfg: dict[str, Any]) -> str:
    cpu = cfg["cluster"]["cpu"]
    return f"""#!/usr/bin/env bash
set -euo pipefail

module load {cpu['module']}
GMX_EXEC="${{GMX_EXEC:-{cpu.get('gmx_exec', 'gmx_mpi')}}}"

help_text="$("${{GMX_EXEC}}" mdrun -h 2>&1 || true)"
printf '%s\\n' "$help_text" | grep -E -- '-plumed|-hrex' || true

has_plumed=0
has_hrex=0
printf '%s\\n' "$help_text" | grep -q -- '-plumed' && has_plumed=1
printf '%s\\n' "$help_text" | grep -q -- '-hrex' && has_hrex=1

echo "has_plumed=${{has_plumed}}"
echo "has_hrex=${{has_hrex}}"

if [[ "$has_plumed" -ne 1 ]]; then
  echo "ERROR: 当前 GROMACS 不支持 -plumed。"
  exit 2
fi
if [[ "$has_hrex" -ne 1 ]]; then
  echo "ERROR: 当前 GROMACS 支持 -plumed 但不支持 -hrex，不能直接运行 PLUMED partial_tempering 多拓扑 REST2。"
  exit 3
fi

echo "OK: 当前 GROMACS 支持 -plumed 和 -hrex，可运行 PLUMED-HREX REST2。"
"""


def render_blocked_run_script(cfg: dict[str, Any], nreplicas: int) -> str:
    cpu = cfg["cluster"]["cpu"]
    return f"""#!/usr/bin/env bash
# REST2 v2 blocker for xpsz GROMACS 2025.1 style modules.
set -euo pipefail

cd "$(dirname "$0")"

cat <<'MSG'
REST2 生产提交已被阻断。

原因:
  当前配置 rest2.hrex_available=false。
  用户在 xpsz 上确认的 GROMACS 2025.1-spack 模块只显示 -plumed，没有 -hrex。
  PLUMED partial_tempering 可以生成缩放拓扑，但多拓扑 REST2 交换运行需要 mdrun -hrex。

已生成的内容:
  prep/prepare_rest2_topologies.sh  可生成 processed topology、hot-atom 标记拓扑、各 replica 缩放拓扑和 tpr。
  rest2/rest2_scales.tsv            effective temperature 与 scale 表。
  rest2/replica_00...               REST2 replica 目录骨架。

下一步:
  1. 如果要做可直接提交的增强采样，请改用 sampling.mode=tremd。
  2. 如果必须做 REST2，请换带 -hrex 的 GROMACS/PLUMED 模块或自行编译。
  3. 换模块后运行:
       bash prep/check_rest2_capability.sh
     确认 has_hrex=1，再把配置改为 rest2.hrex_available=true 并重新生成 bundle。

当前不会执行 mdrun，避免提交一个科学含义错误或必然失败的 REST2 作业。
MSG

module load {cpu['module']} || true
GMX_EXEC="${{GMX_EXEC:-{cpu.get('gmx_exec', 'gmx_mpi')}}}"
"${{GMX_EXEC}}" mdrun -h 2>&1 | grep -E -- '-plumed|-hrex' || true
exit 2
"""


def render_run_script(cfg: dict[str, Any], nreplicas: int) -> str:
    if not hrex_available(cfg):
        return render_blocked_run_script(cfg, nreplicas)

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
#SBATCH -J rest2-run
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
  REPLICA_DIRS+=("rest2/replica_${{idx}}")
done

for seg in $(seq $((SEGMENTS_COMPLETED + 1)) "$SEGMENTS_TOTAL"); do
  target_steps=$((seg * SEGMENT_STEPS))
  echo "=== REST2 Segment $seg / $SEGMENTS_TOTAL ==="

  for repdir in "${{REPLICA_DIRS[@]}}"; do
    "${{GMX_EXEC}}" convert-tpr -s "${{repdir}}/${{DEFFNM}}.tpr" -nsteps "$target_steps" -o "${{repdir}}/${{DEFFNM}}.segment.tpr"
    mv "${{repdir}}/${{DEFFNM}}.segment.tpr" "${{repdir}}/${{DEFFNM}}.tpr"
    test -f "${{repdir}}/plumed.dat"
  done

  "${{MPI_LAUNCH}}" -np "$NREPLICAS" "${{GMX_EXEC}}" mdrun \\
    -multidir "${{REPLICA_DIRS[@]}}" \\
    -s "${{DEFFNM}}.tpr" \\
    -deffnm "${{DEFFNM}}" \\
    -cpi "${{DEFFNM}}.cpt" \\
    -append \\
    -cpt "$CPT_INTERVAL_MIN" \\
    -replex {cfg['sampling'].get('replex', 250)} \\
    -hrex \\
    -plumed plumed.dat \\
    -dlb no \\
    -ntomp "${{SLURM_CPUS_PER_TASK:-{cpu['cpus_per_task']}}}"

  python - "$STATE_FILE" "$seg" "$SEGMENTS_TOTAL" "$SEGMENT_STEPS" "rest2/replica_00/${{DEFFNM}}.cpt" <<'PY'
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
    "mode",
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


def render_blocked_note(cfg: dict[str, Any], ladder: dict[str, Any]) -> str:
    return f"""# REST2 v2 阻断说明

## 当前结论

当前 bundle 不会直接运行 REST2 生产。

原因是当前配置为：

```yaml
rest2:
  hrex_available: false
```

并且用户在 xpsz 超算上已经确认：

```text
GROMACS 2025.1-spack: 有 -plumed，没有 -hrex
```

PLUMED `partial_tempering` 只能负责生成缩放拓扑；多拓扑 REST2 replica exchange 运行还需要 `mdrun -hrex`。

## 本 bundle 仍然可用于什么

- 生成 `rest2/rest2_scales.tsv`
- 生成 `prep/processed.top`
- 生成 `prep/processed_hot.top`
- 生成每个 replica 的缩放拓扑和 `tpr`
- 检查 hot atom 标记是否正确

## 不能做什么

- 不能在当前模块上直接提交 REST2/HREX 生产。
- 不能把 `-replex` 加到无 `-hrex` 的多拓扑模拟里假装 REST2。
- 不能把 REST2 effective temperature 当作 thermostat 真实温度。

## 可选路径

1. 需要马上能跑：改用 `sampling.mode=tremd`。
2. 必须 REST2：换带 `-hrex` 的 GROMACS/PLUMED 模块，或重新编译。
3. 换模块后运行：

```bash
bash prep/check_rest2_capability.sh
```

确认 `has_hrex=1` 后，把配置改为：

```yaml
rest2:
  hrex_available: true
```

再重新生成 bundle。

## 当前 REST2 梯度

- reference temperature: {ladder['reference_temperature']:.2f} K
- replica 数: {ladder['n_replicas']}
- effective temperature 范围: {ladder['effective_temperatures'][0]:.2f}-{ladder['effective_temperatures'][-1]:.2f} K
"""


def render_upload_guide(cfg: dict[str, Any], ladder: dict[str, Any], nstlist: int) -> str:
    if not hrex_available(cfg):
        return f"""# REST2 v2 上传与运行说明

## 当前状态

这是 REST2 v2 阻断式预检包，不是可直接生产提交的 REST2-HREX 包。

- 项目名: {cfg['project']['name']}
- replica 数: {ladder['n_replicas']}
- reference temperature: {ladder['reference_temperature']:.2f} K
- effective temperature 范围: {ladder['effective_temperatures'][0]:.2f}-{ladder['effective_temperatures'][-1]:.2f} K
- 当前配置: `rest2.hrex_available=false`

## 先做能力检查

```bash
bash prep/check_rest2_capability.sh
```

如果输出 `has_plumed=1` 但 `has_hrex=0`，说明当前模块只能支持 PLUMED CV/增强采样接口，不能直接做 PLUMED `partial_tempering` 多拓扑 REST2 交换。

## 可做的准备步骤

如果只是想检查 REST2 拓扑缩放是否能生成，可以运行：

```bash
bash prep/prepare_rest2_topologies.sh
```

这一步会生成 processed topology、hot atom 标记拓扑、每个 replica 的缩放拓扑和 `tpr`。

## 不要直接提交 REST2 生产

`run.sh` 是阻断脚本。执行或提交它只会打印原因并退出，不会运行 `mdrun`。

需要可直接跑的增强采样时，使用 tREMD 路径；需要 REST2 时，换带 `-hrex` 的 GROMACS/PLUMED 模块后重新生成 bundle。

详见 `REST2_BLOCKED_NO_HREX.md`。
"""

    return f"""# REST2 上传与运行说明

## 目录定位

- 项目名: {cfg['project']['name']}
- system_class: {cfg['project']['system_class']}
- replica 数: {ladder['n_replicas']}
- reference temperature: {ladder['reference_temperature']:.2f} K
- effective temperature 范围: {ladder['effective_temperatures'][0]:.2f}-{ladder['effective_temperatures'][-1]:.2f} K
- nstlist: {nstlist}

## 首跑顺序

1. 确认超算模块中的 GROMACS 支持 PLUMED/HREX：

```bash
module load {cfg['cluster']['cpu']['module']}
{cfg['cluster']['cpu'].get('gmx_exec', 'gmx_mpi')} mdrun -h | grep -E -- '-hrex|-plumed'
plumed --version
```

2. 上传整个 bundle 到超算工作目录。
3. 先生成 processed topology、REST2 缩放拓扑和各 replica 的 `tpr`：

```bash
bash prep/prepare_rest2_topologies.sh
```

4. 提交正式 REST2/HREX：

```bash
sbatch run.sh
```

## 续跑

重新提交：

```bash
sbatch run.sh
```

`run.sh` 会读取 `state.yaml`，用 `-cpi -append` 从下一个 segment 接着跑。

## 加长采样

把 `state.yaml` 里的 `segments_total` 改成更大的数字，然后重新提交 `sbatch run.sh`。

## 分析

正式生产后进入 `analysis/`：

```bash
sbatch demux.sh
python remd_efficiency.py replica_index.xvg
./per_temperature_analysis.sh
```

这里的温度表是 REST2 effective temperature，不是 thermostat 的真实温度。

## 注意

- REST2 的 hot atom 标记来自 `prep/processed_hot.top` 中 atom type 后缀 `_`。
- 当前默认用 `plumed partial_tempering` 缩放 hot region。
- 当前生产脚本不写 `#SBATCH --time`，不使用 `-maxh`。
- `run.sh` 固定包含 `-hrex -plumed plumed.dat -dlb no`。
"""


def validate_config(cfg: dict[str, Any]) -> None:
    for key in ("project", "sampling", "inputs", "rest2", "cluster", "steps", "restart"):
        require(key in cfg, f"缺少 {key} 配置块。")
    require(cfg["sampling"].get("mode") == "rest2", "build_rest2_bundle.py 只支持 sampling.mode=rest2。")
    require(cfg["project"].get("system_class") in VALID_SYSTEM_CLASSES, f"REST2 当前支持 {sorted(VALID_SYSTEM_CLASSES)}。")

    prepared = cfg["inputs"].get("prepared") or {}
    require(bool(prepared.get("em_gro")), "REST2 需要 inputs.prepared.em_gro。")
    require(bool(prepared.get("topol_top")), "REST2 需要 inputs.prepared.topol_top。")

    rest2 = cfg["rest2"]
    require(rest2.get("topology_strategy", "plumed_partial_tempering") == "plumed_partial_tempering", "当前 REST2 自动化只支持 topology_strategy=plumed_partial_tempering。")
    require(rest2.get("hot_region", "protein") in VALID_HOT_REGIONS, f"rest2.hot_region 必须是 {sorted(VALID_HOT_REGIONS)}。")
    if rest2.get("exchange_backend") == "plumed_hrex":
        require(hrex_available(cfg), "exchange_backend=plumed_hrex 时必须设置 rest2.hrex_available=true。")
    require("cpu" in cfg["cluster"] and "gpu" in cfg["cluster"], "缺少 cluster.cpu 或 cluster.gpu 配置。")
    require("production" in cfg["steps"], "缺少 steps.production 配置。")


def build_bundle(config_path: Path, output_dir: Path | None, dry_run: bool, force: bool) -> Path:
    cfg = read_yaml(config_path)
    validate_config(cfg)

    ladder = normalize_rest2_ladder(cfg)
    nreplicas = ladder["n_replicas"]
    replex = int(cfg["sampling"].get("replex", 250))
    requested_nstlist = cfg["rest2"].get("nstlist")
    nstlist = choose_nstlist(replex, int(requested_nstlist) if requested_nstlist is not None else None)

    bundle_dir = Path(output_dir or cfg["project"].get("output_dir") or f"./{cfg['project']['name']}_rest2_bundle").resolve()
    if bundle_dir.exists():
        if not force:
            raise ValueError(f"输出目录已存在: {bundle_dir}。如需覆盖请使用 --force。")
        shutil.rmtree(bundle_dir)

    for subdir in ("prep", "system", "rest2", "analysis"):
        (bundle_dir / subdir).mkdir(parents=True, exist_ok=True)

    copy_prepared_inputs(cfg, bundle_dir / "system", dry_run=dry_run)
    write_rest2_tables(bundle_dir, ladder)
    write_plumed_template(cfg, bundle_dir / "prep", dry_run=dry_run)

    mdp = render_rest2_mdp(
        reference_temperature=ladder["reference_temperature"],
        nsteps=int(cfg["steps"]["production"].get("md_nsteps", 500000)),
        nstlist=nstlist,
    )
    (bundle_dir / "prep" / "rest2_preprocess.mdp").write_text(mdp, encoding="utf-8")
    (bundle_dir / "prep" / "mark_rest2_hot_atoms.py").write_text(MARK_HOT_SCRIPT, encoding="utf-8")
    (bundle_dir / "prep" / "mark_rest2_hot_atoms.py").chmod(0o755)
    capability_script = bundle_dir / "prep" / "check_rest2_capability.sh"
    capability_script.write_text(render_capability_check_script(cfg), encoding="utf-8")
    capability_script.chmod(0o755)

    width = zero_width(nreplicas)
    for idx in range(nreplicas):
        repdir = bundle_dir / "rest2" / f"replica_{idx:0{width}d}"
        repdir.mkdir(parents=True, exist_ok=True)
        (repdir / "md.mdp").write_text(mdp, encoding="utf-8")

    prepare_script = bundle_dir / "prep" / "prepare_rest2_topologies.sh"
    prepare_script.write_text(render_prepare_script(cfg, ladder, nstlist), encoding="utf-8")
    prepare_script.chmod(0o755)

    resolved_config = dict(cfg)
    resolved_config["rest2"] = dict(cfg["rest2"])
    resolved_config["rest2"]["effective_temperatures"] = ladder["effective_temperatures"]
    resolved_config["rest2"]["scales"] = ladder["scales"]
    resolved_config["rest2"]["n_replicas"] = nreplicas
    resolved_config["rest2"]["reference_temperature"] = ladder["reference_temperature"]
    resolved_config["rest2"]["nstlist"] = nstlist
    (bundle_dir / "bundle_config.yaml").write_text(
        yaml.safe_dump(resolved_config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    state_text = "\n".join(
        [
            "mode: rest2",
            f"segments_total: {cfg['steps']['production']['total_segments']}",
            "segments_completed: 0",
            f"segment_steps: {cfg['steps']['production']['segment_steps']}",
            f"deffnm: {cfg['sampling'].get('deffnm', '5MD')}",
            "last_completed_segment: 0",
            f"last_checkpoint: rest2/replica_00/{cfg['sampling'].get('deffnm', '5MD')}.cpt",
            "status: ready_for_resume",
            "",
        ]
    )
    (bundle_dir / cfg["restart"].get("state_file", "state.yaml")).write_text(state_text, encoding="utf-8")

    run_script = bundle_dir / "run.sh"
    run_script.write_text(render_run_script(cfg, nreplicas), encoding="utf-8")
    run_script.chmod(0o755)

    (bundle_dir / "UPLOAD_AND_RUN.md").write_text(render_upload_guide(cfg, ladder, nstlist), encoding="utf-8")
    if not hrex_available(cfg):
        (bundle_dir / "REST2_BLOCKED_NO_HREX.md").write_text(render_blocked_note(cfg, ladder), encoding="utf-8")

    if hrex_available(cfg) and cfg.get("postprocess", {}).get("enabled", True):
        render_postprocess_bundle(
            bundle_dir=bundle_dir,
            nreplicas=nreplicas,
            deffnm=cfg["sampling"].get("deffnm", "5MD"),
            module_name=cfg["cluster"]["cpu"]["module"],
            gmx_exec=cfg["cluster"]["cpu"].get("gmx_exec", "gmx_mpi"),
            cpu_partition=cfg["cluster"]["cpu"]["partition"],
            cpu_qos=cfg["cluster"]["cpu"]["qos"],
            temperatures=ladder["effective_temperatures"],
        )

    hrex_ok = hrex_available(cfg)
    manifest = {
        "route": "rest2_hrex" if hrex_ok else "rest2_blocked_no_hrex",
        "workflow_version": "v2",
        "hrex_available": hrex_ok,
        "dry_run": dry_run,
        "n_replicas": nreplicas,
        "bundle_dir": str(bundle_dir),
        "rest2_ladder_yaml": str(bundle_dir / "rest2_ladder.yaml"),
    }
    (bundle_dir / "bundle_manifest.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return bundle_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="根据 YAML 配置生成 GROMACS/PLUMED REST2 v2 运行或阻断式预检包。")
    parser.add_argument("config", type=Path)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    try:
        bundle_dir = build_bundle(args.config, args.output_dir, args.dry_run, args.force)
    except Exception as exc:  # noqa: BLE001
        print(f"生成 REST2 bundle 失败: {exc}", file=sys.stderr)
        return 1

    print(f"已生成 REST2 bundle: {bundle_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
