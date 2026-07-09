# REST2 v2 本地打包与 HREX 预检教程

## 适用场景

用于已经准备好 GROMACS 体系、希望做 REST2 的场景：

- 已有 `1EM.gro` 或等价能量最小化后坐标。
- 已有完整 `topol.top` 和所有 include 文件。
- 目标是只增强溶质、蛋白或自定义 hot atoms 的采样。
- 如果要直接做 PLUMED 多拓扑 REST2 生产，超算上的 GROMACS 必须支持 PLUMED/HREX，即 `mdrun -h` 中能同时看到 `-hrex` 和 `-plumed`。

## v2 能力检查结论

先在目标机器上确认：

```text
gmx_mpi mdrun -h 同时列出 -plumed 和 -hrex
```

如果目标模块有 `-plumed` 但没有 `-hrex`，这意味着：

- 可以使用 `-plumed` 做普通 PLUMED CV/增强采样。
- 可以用 `plumed partial_tempering` 生成 REST2 缩放拓扑。
- 不能直接运行 PLUMED `partial_tempering` 多拓扑 REST2 replica exchange。

所以 v2 默认是能力驱动流程：

- `rest2.hrex_available=false`：生成 REST2 拓扑准备与预检包，但生产 `run.sh` 是阻断脚本。
- `rest2.hrex_available=true`：只有换到支持 `-hrex` 的 GROMACS/PLUMED 模块后，才生成真正的 REST2-HREX 生产脚本。

如果需要在当前模块上“上传后直接跑”，且缺少 `-hrex`，使用 `sampling.mode=tremd` 或常规 `sampling.mode=md`。

CPU 正式作业权限要按用户账号实际 QOS 写：

- 可用 CPU partition/QOS
- CPU/GPU 总核数或任务数限制
- wall-time 限制
- 正式 `run.sh` 的 `--ntasks-per-node` 默认等于 replica 数，但 replica 数不能超过账号/QOS 限制。

不适合直接自动化的情况：

- CHARMM CMAP 或力场特殊项未经人工验证。
- hot region 不是按 residue/atom id 能清楚定义。
- 希望手工改写 Hamiltonian，而不是用 `plumed partial_tempering`。

## 核心原理

REST2 不是把所有 replica 的 thermostat 温度都改高。它保留同一个真实模拟温度 `T0`，对 hot region 的 Hamiltonian 做缩放，让高 replica 表现为更高的 effective temperature。

本 skill 默认使用：

```text
scale_i = T0 / T_i
```

其中 `T_i` 是 REST2 effective temperature。`replica_00` 通常是 `T_i = T0`，因此 `scale = 1.0`。

## 官方实现路线

PLUMED 官方 HREX 教程给出的路线是：

1. 用 `grompp -pp` 生成展开后的 processed topology。
2. 在 processed topology 的 `[ atoms ]` section 中，把 hot atoms 的 atom type 加后缀 `_`。
3. 用 `plumed partial_tempering scale < processed_hot.top > topol_i.top` 为每个 replica 生成缩放拓扑。
4. 每个 replica 用自己的 `topol_i.top` 生成 `tpr`。
5. 用 GROMACS/PLUMED HREX 正式运行：

```bash
mpirun -np N gmx_mpi mdrun \
  -multidir replica_00 replica_01 ... \
  -s 5MD.tpr \
  -deffnm 5MD \
  -replex 250 \
  -hrex \
  -plumed plumed.dat \
  -dlb no
```

参考：

- GROMACS multi-simulation and replica exchange: https://manual.gromacs.org/current/user-guide/mdrun-features.html
- GROMACS replica exchange reference: https://manual.gromacs.org/current/reference-manual/algorithms/replica-exchange.html
- PLUMED HREX/partial_tempering tutorial: https://www.plumed.org/doc-v2.9/user-doc/html/hrex.html
- 用户提供的中文参考: https://zhuanlan.zhihu.com/p/651325095

注意：GROMACS 官方也支持基于 free-energy lambda 的原生 Hamiltonian replica exchange，但这不是 PLUMED `partial_tempering` 多拓扑 REST2 的直接替代。除非专门设计 lambda 拓扑与 mdp，不要自动把 REST2 切到原生 free-energy HREX。

## 用本 skill 生成 REST2 包

从 `assets/config-template.yaml` 复制一份配置，关键字段改成：

```yaml
sampling:
  mode: rest2
  replex: 250
  deffnm: 5MD

inputs:
  prepared:
    em_gro: /absolute/path/to/1EM.gro
    topol_top: /absolute/path/to/topol.top
    include_files:
      - /absolute/path/to/forcefield_or_ligand.itp

rest2:
  workflow_version: v2
  topology_strategy: plumed_partial_tempering
  exchange_backend: plumed_partial_tempering_hrex
  reference_temperature: 300.0
  tmin: 300.0
  tmax: 500.0
  n_replicas: 8
  effective_temperatures: []
  hot_region: protein
  hot_atom_ids: []
  hot_residue_names: []
  solvent_residue_names: [SOL, WAT, HOH, TIP3, NA, CL, K, CA, MG, ZN]
  plumed_dat: empty
  require_hrex: true
  hrex_available: false

cluster:
  cpu:
    partition: <cpu-partition>
    qos: <cpu-qos>
    ntasks_per_node: auto
    cpus_per_task: 1
    max_total_tasks: 26
```

生成运行包：

```bash
python scripts/build_rest2_bundle.py rest2-config.yaml --force
```

如果只是检查目录结构，不复制真实输入：

```bash
python scripts/build_rest2_bundle.py rest2-config.yaml --dry-run --force
```

## 输出目录结构

REST2 bundle 主要包含：

```text
bundle/
├── system/
│   ├── 1EM.gro
│   └── topol.top
├── prep/
│   ├── check_rest2_capability.sh
│   ├── prepare_rest2_topologies.sh
│   ├── mark_rest2_hot_atoms.py
│   ├── rest2_preprocess.mdp
│   └── plumed.dat.template
├── rest2/
│   ├── rest2_scales.tsv
│   ├── replica_00/
│   │   └── md.mdp
│   └── replica_01/
├── run.sh
├── state.yaml
├── rest2_ladder.yaml
├── REST2_BLOCKED_NO_HREX.md
└── UPLOAD_AND_RUN.md
```

如果 `rest2.hrex_available=true`，还会生成 `analysis/` 后处理脚本。

## 超算上怎么检查

先确认模块支持：

```bash
module load gromacs/2025.1
gmx_mpi mdrun -h | grep -E -- '-hrex|-plumed'
plumed --version
```

如果集群实际模块名不是 `gromacs/2025.1`，以 `module avail gromacs` 或管理员给出的模块名为准；关键判断不是模块名，而是 `mdrun -h` 中是否同时出现 `-plumed` 和 `-hrex`。

或在 bundle 中运行：

```bash
bash prep/check_rest2_capability.sh
```

## 缺少 `-hrex` 的模块下可以做什么

可以准备拓扑和 `tpr`：

```bash
bash prep/prepare_rest2_topologies.sh
```

这一步用于检查：

- `grompp -pp` 能否生成 processed topology。
- hot atom 标记是否合理。
- `plumed partial_tempering` 是否能生成每个 replica 的缩放拓扑。
- 每个 replica 的 `tpr` 是否能通过 `grompp`。

不要提交 REST2 生产：

```bash
sbatch run.sh
```

当 `rest2.hrex_available=false` 时，v2 默认的 `run.sh` 会立即退出并说明缺少 `-hrex`，不会执行 `mdrun`。

## 换到带 `-hrex` 的模块后怎么跑

确认：

```bash
bash prep/check_rest2_capability.sh
```

输出包含 `has_hrex=1` 后，修改配置：

```yaml
rest2:
  hrex_available: true
  exchange_backend: plumed_hrex
```

重新生成 bundle，再按 `UPLOAD_AND_RUN.md` 提交生产。

## hot region 定义

默认：

```yaml
rest2:
  hot_region: protein
```

脚本会把 processed topology 中非水、非离子的 residue 当作 hot region。

如果只想加热指定 residue 名：

```yaml
rest2:
  hot_region: protein
  hot_residue_names: [ALA, GLY, LYS]
```

如果要精确到 atom id：

```yaml
rest2:
  hot_region: custom_atom_ids
  hot_atom_ids: [1, 2, 3, 4, 5]
```

自定义 atom id 对应的是 processed topology `[ atoms ]` section 第一列编号，不是 PDB serial 的无条件同义词。

## 检查与常见问题

1. `mdrun -h` 没有 `-hrex`

当前 GROMACS 没有可用 PLUMED 多拓扑 HREX 支持。v2 会生成阻断式 `run.sh`，避免误提交。换带 `-hrex` 的模块，或重新编译 GROMACS+PLUMED。

2. `plumed partial_tempering` 报错

先确认输入是 `grompp -pp` 后的 processed topology。不要直接把原始 `topol.top` 输入给 `partial_tempering`。

3. hot atoms 数量为 0

检查 `rest2.hot_region`、`hot_residue_names` 和 `solvent_residue_names`。如果体系 residue 名不是标准水/离子名，默认筛选可能会错。

4. 交换率很低

缩小 `tmax` 或增加 replica 数，先做短跑再定正式梯度。

5. `nstlist` 与 `replex` 不匹配

REST2/HREX 建议 `nstlist` 能整除 `replex`。本 skill 默认会为 REST2 选择能整除 `replex` 的 `nstlist`，例如 `replex=250` 时用 `nstlist=25`。
