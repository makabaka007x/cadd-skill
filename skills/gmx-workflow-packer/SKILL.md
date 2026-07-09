---
name: gmx-workflow-packer
description: Package GROMACS conventional MD, tREMD, and REST2/HREX workflows into reproducible local or cluster run bundles with blocking preflight checks. Use for prepared GROMACS systems, protein or protein-ligand MD setup, EM/NVT/NPT/production runs, ACPYPE/GAFF ligand preparation, tREMD, REST2 solute-scaling topology generation, PLUMED partial_tempering, GROMACS -hrex capability checks, resume logic, demux, exchange-efficiency analysis, or trajectory reorganization.
---

# Gmx Workflow Packer

## Overview

把一次性的 GROMACS 常规 MD、tREMD 或 REST2 操作整理成可复用、可交付的目录和脚本。
默认目标不是只解释参数，而是留下一个能在本地准备、上传目标机器并适配提交的运行包；如果当前模块不支持某种增强采样，必须生成阻断式说明，不能给出会失败的提交脚本。

## 入口判断

先把请求归到下面五类入口之一：

1. 常规 GROMACS MD
- 适用于标准 EM -> position-restrained/NVT -> NPT -> production MD。
- 可从已有 `topol.top` 和能量最小化坐标开始，也可从蛋白 PDB 生成准备脚本。
- 使用 `assets/md-config-template.yaml` 和 `scripts/build_md_bundle.py`。

2. 已有 GROMACS 体系直接打包为 tREMD
- 适用于用户已经有 `topol.top`、`1EM.gro` 或等价起始坐标。
- 直接生成 `step1/step2/analysis/run.sh/state.yaml`。
- 这是最稳的主路径。

3. 标准蛋白本地准备后打包为 tREMD
- 适用于用户只有蛋白 `PDB`。
- 生成本地准备脚本，执行 `pdb2gmx -> editconf -> solvate -> genion -> EM`。
- 再生成标准 tREMD 运行目录。

4. 蛋白配体本地准备后打包
- 适用于蛋白配体复合物做标准 tREMD。
- 支持两种配体入口：
- 独立 `ligand.mol2` 或 `ligand.sdf`
- 从 `complex.pdb` 中拆出配体
- 配体默认用 `ACPYPE/GAFF`，但不自动安装依赖。

5. REST2/HREX 打包
- 适用于用户已有 `1EM.gro` 或等价起始坐标、`topol.top`，希望只升温溶质或 hot region。
- 默认使用 PLUMED 官方 `partial_tempering` 生成每个 replica 的缩放拓扑。
- REST2 v2 默认按能力检查结果决定是否生成生产脚本。
- 如果 `mdrun -h` 能看到 `-plumed` 但没有 `-hrex`，只生成拓扑准备与预检包，生产 `run.sh` 必须阻断并解释“缺少 `-hrex`，不能直接做 PLUMED 多拓扑 REST2 交换”。
- 只有在用户明确提供带 `-hrex` 的 GROMACS/PLUMED 模块，并把 `rest2.hrex_available=true` 时，才生成真正的 REST2-HREX 生产脚本。
- REST2 细节读取 [references/rest2-workflow.md](references/rest2-workflow.md)。
- 如果用户要求非 PLUMED 的手工拓扑缩放、CHARMM CMAP、或复杂自定义 Hamiltonian，先说明需要人工审查，不要盲目自动化。

## 默认工作流

默认按下面顺序推进：

1. 先检查环境
- 运行 `scripts/check_env.py`。
- 如果缺少 `gmx`、`gmx_mpi`、`perl`，先停止。
- 如果是蛋白配体路径，再额外检查 `acpype`、`antechamber`、`obabel`。
- 如果是 REST2 路径，运行 `scripts/check_env.py --mode rest2 --check-hrex`，并在目标模块中确认 `gmx_mpi mdrun -h` 是否同时支持 `-hrex` 和 `-plumed`。
- 如果检查结果缺少 `-hrex`，必须阻断 REST2 生产提交，只允许生成准备和预检包。

2. 读取或生成 YAML 配置
- 常规 MD 默认使用 `assets/md-config-template.yaml` 作为起点。
- tREMD/REST2 默认使用 `assets/config-template.yaml` 作为起点。
- `sampling.mode=md` 使用 `scripts/build_md_bundle.py`。
- `sampling.mode=tremd` 使用 `scripts/build_remd_bundle.py`。
- `sampling.mode=rest2` 使用 `scripts/build_rest2_bundle.py`。

3. 确定温度梯度
- tREMD：如果配置里已经给出 `temperature_ladder.temperatures`，直接使用；否则运行 `scripts/optimize_remd_ladder.py` 估算。
- REST2：使用 `rest2.effective_temperatures`；如果为空，用 `rest2.tmin/tmax/n_replicas` 生成几何 effective-temperature 梯度，缩放因子为 `scale_i = T0 / T_i`。
- 所有梯度都只是经验初值。默认提醒用户先短跑检查交换率，再决定是否加密或拉宽梯度。

4. 生成运行包
- 常规 MD 运行 `scripts/build_md_bundle.py`。
- tREMD 运行 `scripts/build_remd_bundle.py`。
- REST2 运行 `scripts/build_rest2_bundle.py`。
- 常规 MD 输出目录保留 `mdp/run/analysis/prep/system/state.yaml/UPLOAD_AND_RUN.md` 语义。
- tREMD 输出目录固定保留 `step1/step2/analysis` 语义。
- REST2 输出目录使用 `prep/rest2/analysis/run.sh/state.yaml`，其中 `rest2/replica_00` 等目录直接对应 REST2 replica。
- `rest2.hrex_available=false` 时，`run.sh` 是阻断脚本，不能提交生产；`rest2.hrex_available=true` 时，`run.sh` 才是生产脚本。
- 副本目录统一使用 `replica_00` 风格，不再沿用旧的 `equ_0` 或 `MD_0` 命名。

5. 生成后处理包
- 运行 `scripts/render_postprocess_bundle.py`，或让 `build_remd_bundle.py` 自动调用它。
- 输出 `demux.pl`、`demux.sh`、交换效率分析脚本、按温度轨迹分析骨架。

## 集群配置原则

- `step1` 和 `step2` 可以使用 GPU 队列，正式多副本 `run.sh` 常用 CPU 或 MPI 队列，具体以目标集群为准。
- GPU/CPU partition、QOS、module、account、wall-time、MPI launcher 和最大任务数必须由用户或集群文档确认。
- `cluster.cpu.max_total_tasks` 必须大于等于 replica 数；否则停止并要求用户减少 replica 数或提供更高资源限制。
- GROMACS 可执行入口通常是 `gmx` 或 `gmx_mpi`，不要把某个集群路径写成公开默认。

## 关键约束

始终遵循这些约束：

- `run.sh` 使用单脚本分段续跑。
- 续跑必须依赖 `-cpi -append` 和 `state.yaml`。
- 默认不要在任何提交脚本里写 `#SBATCH --time`。
- 默认不要在生产 `run.sh` 中使用 `-maxh`。
- 不要复用旧版 `step2.sh` 的逗号字符串温度循环。
- 副本目录必须零填充，避免 `replica_1 replica_10 replica_2` 这种字典序问题。
- 正式 CPU 多副本任务默认 `--ntasks-per-node` 等于副本数；如果超过 `cluster.cpu.max_total_tasks`，必须停下来让用户调整配置。
- REST2 的 effective temperature 不是 thermostat 真实温度；REST2 各 replica 的 `md.mdp` 默认使用同一个参考温度，采样增强来自缩放 Hamiltonian。
- REST2 拓扑必须从 `grompp -pp` 生成的 processed topology 开始标记 hot atoms，不要直接改带 `#include` 的原始 `topol.top`。
- PLUMED `partial_tempering` 多拓扑 REST2 生产脚本必须包含 `-hrex -plumed plumed.dat -dlb no`，并要求 `nstlist` 能整除 `replex`。
- 如果 `mdrun -h` 只有 `-plumed` 没有 `-hrex`，不要用 `-replex` 伪装 REST2；这只会变成错误的普通多模拟或在运行时报错。
- GROMACS 官方原生 HREX 是 free-energy lambda 路线，不等价于 PLUMED `partial_tempering` 多拓扑 REST2；除非用户专门要求并提供 lambda 拓扑设计，不要自动切换。

## 主要资源

优先使用这些资源，不要现场重写：

- 环境检查：
- `scripts/check_env.py`
- 温度梯度估算：
- `scripts/optimize_remd_ladder.py`
- 运行包生成：
- `scripts/build_md_bundle.py`
- `scripts/build_remd_bundle.py`
- REST2 运行包生成：
- `scripts/build_rest2_bundle.py`
- 后处理生成：
- `scripts/render_postprocess_bundle.py`
- 标准 tREMD 工作流：
- `references/core-workflow.md`
- REST2 教程：
- `references/rest2-workflow.md`
- HREMD/复杂 REST2 注意事项：
- `references/future-rest2.md`
- 默认配置模板：
- `assets/md-config-template.yaml`
- `assets/config-template.yaml`
- 默认 `mdp` 模板：
- `assets/templates/`
- demux 资源：
- `assets/demux.pl`

## 输出要求

把目录视为“已完成可交付”之前，至少要满足：

- 有完整 YAML 配置副本。
- 常规 MD 包有 `mdp/run/analysis/system/run.sh/state.yaml/UPLOAD_AND_RUN.md`。
- tREMD 包有 `step1/step2/analysis/run.sh/state.yaml/UPLOAD_AND_RUN.md`。
- REST2 包有 `prep/rest2/run.sh/state.yaml/UPLOAD_AND_RUN.md`；只有 `rest2.hrex_available=true` 时才要求 `analysis/` 后处理脚本。
- 有温度表 YAML 和 CSV。
- 有中文说明，写清首跑、续跑、demux 和效率分析命令。
- REST2 包还必须有 effective-temperature/scale 表、`prep/prepare_rest2_topologies.sh`、`prep/mark_rest2_hot_atoms.py`，以及每个 replica 的 `plumed.dat`。
- 如果只是 dry-run，要明确说明哪些输入文件还未准备好。
