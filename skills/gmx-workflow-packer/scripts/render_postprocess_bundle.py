#!/usr/bin/env python3
"""Render demux and exchange-analysis helpers for a tREMD bundle."""

from __future__ import annotations

import argparse
import csv
import shutil
import sys
from pathlib import Path

import yaml


REMD_EFFICIENCY_SCRIPT = r'''#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Tuple, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def read_index_with_time(fname: str | Path) -> Tuple[np.ndarray, pd.DataFrame]:
    times: List[float] = []
    rows: List[List[int]] = []
    expected = None
    bad: List[tuple[int, str]] = []

    with open(fname, "r", encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line[0] in ("#", "@"):
                continue
            parts = line.split()
            if expected is None:
                expected = len(parts) - 1
                if expected <= 0:
                    bad.append((lineno, "no data columns"))
                    continue
            if len(parts) - 1 != expected:
                bad.append((lineno, f"cols={len(parts)} expect={expected + 1}"))
                continue
            try:
                times.append(float(parts[0]))
                rows.append([int(x) for x in parts[1:]])
            except ValueError:
                bad.append((lineno, "non-numeric token"))

    if not rows:
        raise RuntimeError(f"无法从 {fname} 读取有效的 replica_index.xvg 数据。")
    if bad:
        print(f"WARNING: 跳过 {len(bad)} 行异常数据，示例: {bad[:5]}")

    return np.asarray(times, dtype=float), pd.DataFrame(rows)


def acceptance(df: pd.DataFrame) -> tuple[np.ndarray, float]:
    n_ladder = df.shape[1]
    acc_pair = np.zeros(n_ladder - 1, dtype=float)
    tried = np.zeros(n_ladder - 1, dtype=int)
    arr = df.to_numpy()
    for frame in range(1, arr.shape[0]):
        prev = arr[frame - 1]
        curr = arr[frame]
        swapped = (curr[:-1] == prev[1:]) & (curr[1:] == prev[:-1])
        acc_pair += swapped
        tried += 1
    acc_pair /= np.maximum(tried, 1)
    return acc_pair, float(acc_pair.mean())


def invert_permutation_rows(df: pd.DataFrame) -> np.ndarray:
    ladders = df.to_numpy()
    frames, replicas = ladders.shape
    pos = np.empty((frames, replicas), dtype=int)
    for frame in range(frames):
        pos[frame, ladders[frame]] = np.arange(replicas, dtype=int)
    return pos


def compute_msd(pos: np.ndarray, max_lag: int | None = None) -> np.ndarray:
    frames, _ = pos.shape
    if max_lag is None:
        max_lag = min(frames // 2, 500)
    msd = np.zeros(max_lag + 1, dtype=float)
    for lag in range(1, max_lag + 1):
        disp = pos[lag:, :] - pos[:-lag, :]
        msd[lag] = np.mean(disp * disp)
    return msd


def fit_diffusion_constant(msd: np.ndarray, dt: float, fit_frac: float) -> tuple[float, float]:
    length = len(msd) - 1
    kmax = max(5, int(length * fit_frac))
    kmax = min(kmax, length)
    taus = np.arange(1, kmax + 1, dtype=float) * dt
    y = msd[1 : kmax + 1]
    matrix = np.vstack([taus, np.ones_like(taus)]).T
    slope, _intercept = np.linalg.lstsq(matrix, y, rcond=None)[0]
    return float(slope / 2.0), float(slope)


def round_trip_times(times: np.ndarray, pos: np.ndarray) -> Dict[str, np.ndarray]:
    frames, replicas = pos.shape
    ladder_min = 0
    ladder_max = pos.max()
    result = {"up": [], "down": [], "total": []}
    for rid in range(replicas):
        walk = pos[:, rid]
        start = 0
        while start < frames and walk[start] != ladder_min:
            start += 1
        while start < frames:
            up_idx = start + 1
            while up_idx < frames and walk[up_idx] != ladder_max:
                up_idx += 1
            if up_idx >= frames:
                break
            down_idx = up_idx + 1
            while down_idx < frames and walk[down_idx] != ladder_min:
                down_idx += 1
            if down_idx >= frames:
                break
            result["up"].append(times[up_idx] - times[start])
            result["down"].append(times[down_idx] - times[up_idx])
            result["total"].append(times[down_idx] - times[start])
            start = down_idx + 1
            while start < frames and walk[start] != ladder_min:
                start += 1
    return {key: np.asarray(value, dtype=float) for key, value in result.items()}


def residence_times(times: np.ndarray, pos: np.ndarray) -> pd.DataFrame:
    frames, _replicas = pos.shape
    diffs = np.diff(times)
    dt = float(np.median(diffs)) if diffs.size else 1.0
    ladder_count = int(pos.max()) + 1
    per_ladder = [[] for _ in range(ladder_count)]

    for rid in range(pos.shape[1]):
        walk = pos[:, rid]
        start = 0
        while start < frames:
            ladder = walk[start]
            end = start + 1
            while end < frames and walk[end] == ladder:
                end += 1
            per_ladder[ladder].append((end - start) * dt)
            start = end

    rows = []
    for ladder, samples in enumerate(per_ladder):
        arr = np.asarray(samples, dtype=float)
        rows.append(
            (
                ladder,
                np.nan if arr.size == 0 else arr.mean(),
                np.nan if arr.size == 0 else np.median(arr),
                int(arr.size),
            )
        )
    return pd.DataFrame(rows, columns=["ladder", "res_mean", "res_median", "samples"])


def visit_stats(df: pd.DataFrame) -> pd.DataFrame:
    ladder_count = df.shape[1]
    rows = []
    for rid in range(ladder_count):
        ladders = (df == rid).idxmax(axis=1)
        rows.append((rid, ladders.min(), ladders.max(), ladders.nunique() / ladder_count))
    return pd.DataFrame(rows, columns=["replica", "min_ladder", "max_ladder", "coverage"])


def main() -> int:
    parser = argparse.ArgumentParser(description="REMD exchange diagnostics")
    parser.add_argument("index", help="replica_index.xvg")
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--dt", type=float, default=None)
    parser.add_argument("--fit-frac", type=float, default=0.2)
    parser.add_argument("--max-lag", type=int, default=None)
    parser.add_argument("--csv-prefix", type=str, default=None)
    args = parser.parse_args()

    times_raw, ladders_df = read_index_with_time(args.index)
    frames, replicas = ladders_df.shape
    if args.dt is not None:
        dt = float(args.dt)
        times = np.arange(frames, dtype=float) * dt
        unit = "override"
    else:
        times = times_raw
        diffs = np.diff(times)
        dt = float(np.median(diffs)) if diffs.size else 1.0
        unit = "file"

    acc_pair, acc_global = acceptance(ladders_df)
    pos = invert_permutation_rows(ladders_df)
    msd = compute_msd(pos, args.max_lag)
    diffusion, _slope = fit_diffusion_constant(msd, dt, args.fit_frac)
    rtt = round_trip_times(times, pos)
    residence = residence_times(times, pos)
    coverage = visit_stats(ladders_df)

    def summarize(arr: np.ndarray) -> str:
        if arr.size == 0:
            return "count=0"
        return (
            f"count={arr.size}, mean={arr.mean():.3f}, median={np.median(arr):.3f}, "
            f"p05={np.percentile(arr, 5):.3f}, p95={np.percentile(arr, 95):.3f}"
        )

    print(f"# Frames={frames}, Ladders={replicas}, dt({unit})={dt:g}")
    print("\n=== Acceptance per adjacent ladder ===")
    for idx, acc in enumerate(acc_pair):
        print(f"L{idx:02d}<->L{idx + 1:02d}: {acc:.3f}")
    print(f"Global mean acceptance: {acc_global:.3f}")

    print("\n=== Diffusion on temperature ladder ===")
    print(f"D ~= {diffusion:.4f} ladder^2 / time-unit")

    print("\n=== Round-trip times ===")
    print("up   :", summarize(rtt["up"]))
    print("down :", summarize(rtt["down"]))
    print("total:", summarize(rtt["total"]))

    print("\n=== Residence time per ladder ===")
    print(
        residence.to_string(
            index=False,
            formatters={"res_mean": "{:.3f}".format, "res_median": "{:.3f}".format},
        )
    )

    print("\n=== Replica walk coverage ===")
    print(coverage.to_string(index=False, formatters={"coverage": "{:.2f}".format}))

    if args.csv_prefix:
        prefix = Path(args.csv_prefix)
        pd.DataFrame(
            {"pair": [f"{idx}-{idx + 1}" for idx in range(replicas - 1)], "acceptance": acc_pair}
        ).to_csv(prefix.with_suffix(".accept.csv"), index=False)
        pd.DataFrame({"lag": np.arange(len(msd)), "msd": msd}).to_csv(
            prefix.with_suffix(".msd.csv"), index=False
        )
        pd.DataFrame({"up": rtt["up"], "down": rtt["down"], "total": rtt["total"]}).to_csv(
            prefix.with_suffix(".rtt.csv"), index=False
        )
        residence.to_csv(prefix.with_suffix(".residence.csv"), index=False)
        coverage.to_csv(prefix.with_suffix(".coverage.csv"), index=False)

    if args.plot:
        plt.figure(figsize=(6, 4))
        plt.imshow(ladders_df.T, aspect="auto", interpolation="nearest")
        plt.xlabel("frame")
        plt.ylabel("ladder")
        plt.title("Replica ID per ladder")
        plt.colorbar(label="replica ID")
        plt.tight_layout()

        plt.figure(figsize=(6, 4))
        taus = np.arange(len(msd), dtype=float) * dt
        plt.plot(taus[1:], msd[1:], label="MSD")
        plt.xlabel("lag")
        plt.ylabel("MSD")
        plt.title("Temperature-ladder diffusion")
        plt.legend()
        plt.tight_layout()
        plt.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


DEMUX_SH_TEMPLATE = """#!/usr/bin/env bash
#SBATCH -J tremd-demux
#SBATCH --partition={partition}
#SBATCH --qos={qos}
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH -o %j.out
#SBATCH -e %j.err

set -euo pipefail

cd "$(dirname "$0")"
module load {module_name}

DEFFNM="{deffnm}"
NREPLICAS={nreplicas}
WIDTH={width}
GMX_EXEC="{gmx_exec}"

perl ./demux.pl ../step2/replica_00/${{DEFFNM}}.log
test -s replica_index.xvg

mkdir -p demuxed
mapfile -t XTCS < <(seq -f "../step2/replica_%0${{WIDTH}}g/${{DEFFNM}}.xtc" 0 $((NREPLICAS - 1)))
"${{GMX_EXEC}}" trjcat -f "${{XTCS[@]}}" -demux replica_index.xvg -o demuxed/replica.xtc

python - <<'PY'
from pathlib import Path

demuxed = Path("demuxed")
files = sorted(demuxed.glob("*replica.xtc"))
for idx, old in enumerate(files):
    new = demuxed / f"replica_{{idx:0{width}d}}.xtc"
    if old != new:
        if new.exists():
            new.unlink()
        old.rename(new)
PY

echo "demux 完成，输出位于 analysis/demuxed/"
"""


PER_TEMP_ANALYSIS_TEMPLATE = """#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

mkdir -p by_temperature
python - <<'PY'
from pathlib import Path
import csv

mapping = Path("temperature_map.csv")
demuxed = Path("demuxed")
target = Path("by_temperature")
if not mapping.exists():
    raise SystemExit("temperature_map.csv 不存在，无法建立按温度映射。")

with mapping.open("r", encoding="utf-8") as handle:
    reader = csv.DictReader(handle)
    for row in reader:
        replica = int(row["replica"])
        temp = float(row["temperature_k"])
        src = demuxed / f"replica_{{replica:0{width}d}}.xtc"
        dst = target / f"temp_{{temp:.2f}}K.xtc"
        if src.exists():
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            dst.symlink_to(src.resolve())
PY

echo "已根据温度建立 by_temperature 目录。"
echo "后续可按需在每个 temp_*.xtc 上继续做 RMSD、Rg、聚类或结构提取。"
"""


def parse_temperatures(values: str | None) -> list[float]:
    if not values:
        return []
    return [round(float(item.strip()), 2) for item in values.split(",") if item.strip()]


def render_postprocess_bundle(
    bundle_dir: Path,
    nreplicas: int,
    deffnm: str,
    module_name: str,
    gmx_exec: str,
    cpu_partition: str,
    cpu_qos: str,
    temperatures: list[float] | None = None,
) -> Path:
    analysis_dir = bundle_dir / "analysis"
    analysis_dir.mkdir(parents=True, exist_ok=True)

    width = max(2, len(str(nreplicas - 1)))
    asset_dir = Path(__file__).resolve().parent.parent / "assets"
    shutil.copy2(asset_dir / "demux.pl", analysis_dir / "demux.pl")

    (analysis_dir / "remd_efficiency.py").write_text(REMD_EFFICIENCY_SCRIPT, encoding="utf-8")
    (analysis_dir / "demux.sh").write_text(
        DEMUX_SH_TEMPLATE.format(
            partition=cpu_partition,
            qos=cpu_qos,
            module_name=module_name,
            deffnm=deffnm,
            nreplicas=nreplicas,
            width=width,
            gmx_exec=gmx_exec,
        ),
        encoding="utf-8",
    )
    (analysis_dir / "per_temperature_analysis.sh").write_text(
        PER_TEMP_ANALYSIS_TEMPLATE.format(width=width),
        encoding="utf-8",
    )

    temperatures = temperatures or []
    if temperatures:
        with (analysis_dir / "temperature_map.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["replica", "temperature_k"])
            for idx, temp in enumerate(temperatures):
                writer.writerow([idx, f"{temp:.2f}"])

    for path in (
        analysis_dir / "demux.pl",
        analysis_dir / "demux.sh",
        analysis_dir / "remd_efficiency.py",
        analysis_dir / "per_temperature_analysis.sh",
    ):
        path.chmod(0o755)

    return analysis_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="为 tREMD bundle 生成后处理脚本。")
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("--nreplicas", type=int, required=True)
    parser.add_argument("--deffnm", default="5MD")
    parser.add_argument("--module-name", required=True)
    parser.add_argument("--gmx-exec", default="gmx_mpi")
    parser.add_argument("--cpu-partition", default="cpu8358")
    parser.add_argument("--cpu-qos", default="52cores")
    parser.add_argument("--temperatures", default="")
    args = parser.parse_args()

    analysis_dir = render_postprocess_bundle(
        bundle_dir=args.bundle_dir,
        nreplicas=args.nreplicas,
        deffnm=args.deffnm,
        module_name=args.module_name,
        gmx_exec=args.gmx_exec,
        cpu_partition=args.cpu_partition,
        cpu_qos=args.cpu_qos,
        temperatures=parse_temperatures(args.temperatures),
    )
    print(f"已生成后处理目录: {analysis_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
