---
name: unidock-pro
description: 使用本机 UniDock-Pro 环境执行 GPU 虚拟筛选，并在 classical docking、ligand similarity searching、hybrid docking 三类任务中完成环境探测、构建验证、批量运行和结果汇总。用户提到 UniDock-Pro、`udp`、虚拟筛选、`receptor.pdbqt`、`reference_ligand`、`ligand_index`、`ligand_dir`、`search_mode`、对接结果排序，或希望把当前机器的 UniDock-Pro 工作流整理成可复用脚本时使用。
---

# UniDock-Pro 本地虚拟筛选

把任务默认理解为“在这台机器上交付一个可复现的 UniDock-Pro 运行结果”，不要只解释命令行。
优先使用 `scripts/run_unidock_case.py`、`scripts/make_ligand_index.py`、`scripts/analyze_unidock_results.py`，避免临时手写长命令。

## 默认工作流

1. 先读 `references/local-setup.md`，确认本机仓库、二进制、conda 环境和文档偏差。
2. 判断任务属于 pure docking、similarity searching、hybrid 三类之一。
3. 先检查 `build/udp` 是否可直接运行；如果不可运行，再切到本机 `unidock-pro` 环境，必要时按本地构建指引重建。
4. 明确搜索框中心、搜索框尺寸和 `--search_mode`。`--search_mode` 必须显式设置，不允许省略；如果用户没有明确说用哪一个，每次都先问，不得替用户默认选择。
5. 优先通过 `scripts/run_unidock_case.py` 执行，不要直接手写一长串 `udp` 参数。
6. 如果用户只有配体目录，没有索引文件，先运行 `scripts/make_ligand_index.py`。
7. 运行结束后，用 `scripts/analyze_unidock_results.py` 汇总 `*_out.pdbqt`，给出排序结果和输出路径。

## 输入判定

把请求先归到下面三类之一：

1. pure docking
- 有 `receptor`
- 没有 `reference_ligand`
- 典型目标是经典结构对接

2. similarity searching
- 有 `reference_ligand`
- 没有 `receptor`
- 典型目标是基于已知活性配体做相似性筛选

3. hybrid
- 同时有 `receptor` 和 `reference_ligand`
- 典型目标是结合受体结构和参考配体做联合筛选

配体输入只选一种：

- `ligand_index`
- `ligand_dir`

如果用户同时给了两种来源，先收敛成一种再运行。

## 快速入口

优先使用脚本入口：

```bash
python3 scripts/run_unidock_case.py \
  --mode docking \
  --receptor /path/to/receptor.pdbqt \
  --ligand-index /path/to/ligand_index.txt \
  --center-x 32.79 --center-y 38.34 --center-z 58.49 \
  --size-x 28 --size-y 28 --size-z 28 \
  --search-mode <用户确认的模式> \
  --output-dir /path/to/results
```

如果用户只有配体目录：

```bash
python3 scripts/make_ligand_index.py /path/to/ligands /path/to/ligand_index.txt
```

结果汇总入口：

```bash
python3 scripts/analyze_unidock_results.py /path/to/results /path/to/docking_results.csv --top-n 50
```

## 环境与构建

本 skill 默认依赖这台机器上的本地安装事实，不要凭空假设新机器布局。

- 先尝试直接运行 `/path/to/UniDock-Pro/build/udp`
- 如果直接运行失败，再尝试 `conda activate unidock-pro`
- 如果 `conda activate` 不方便，再回退到 `/path/to/conda-envs/unidock-pro`

如果二进制不存在或不可执行，优先按 `references/local-setup.md` 中的本机构建步骤重建。

## 防呆规则

- 强制显式传入 `--search_mode`
- 如果用户没有明确指定 `fast`、`balance` 或 `detail`，必须先询问，再运行；不要根据任务规模或习惯自动选
- 文档里常见的 `--ligand_directory` 不要直接照搬；当前源码真实参数是 `--ligand_dir`
- 源码接受 `balance`/`balanced` 与 `detail`/`detailed`，与用户确认时统一使用规范写法 `fast`、`balance`、`detail`
- hybrid 模式里的 `reference_ligand` 必须是与受体对应的共晶姿态；如果用户没有明确说明，先提醒这个前提
- 批量运行时总是传入新的输出目录，避免把不同任务的 `*_out.pdbqt` 混在一起

## 输出约定

交付时优先说明这些内容：

- 实际运行模式
- 实际调用方式：直跑二进制、`conda activate unidock-pro`，还是环境前缀回退
- 输出目录
- 生成的 `*_out.pdbqt`
- 汇总 CSV 路径
- 任何关键前提，例如 hybrid 模式共晶参考配体的假设

## 资源

- 本机路径、环境和文档偏差：`references/local-setup.md`
- 三类任务的命令模板和输出约定：`references/workflows.md`
- 统一运行入口：`scripts/run_unidock_case.py`
- 配体目录转索引：`scripts/make_ligand_index.py`
- 结果排序与 CSV 汇总：`scripts/analyze_unidock_results.py`
