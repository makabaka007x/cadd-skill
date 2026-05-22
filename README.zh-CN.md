# Auto CADD Skill Collection

English version: [README.md](README.md)

这个仓库收集可复用的 Codex/Claude 风格 skills，面向 CADD/AIDD 工作流，包括分子动力学、分子对接、GPU 虚拟筛选、蛋白设计和 AlphaFold3 结果分析。

这个仓库的定位是 Agent 使用手册和可迁移 skill 包。这里的 skill 不是完整的软件安装器，而是为 Agent 提供可复用的操作说明、辅助脚本、模板和安全检查，帮助把科研需求落成可复现的工作流或运行目录。

## 快速选择表

当你知道要做什么，但不确定该调用哪个 skill 时，先看这张表。

| 你想做什么 | 使用 | 可以这样问 Agent | 典型输出 |
| --- | --- | --- | --- |
| 准备或打包 Amber MD 体系 | `amber-md-expert` | `/amber-md-expert 帮我把这个体系打包成可上传超算运行的 Amber MD 目录` | Amber 运行目录、输入文件、提交脚本、分析和续跑说明。 |
| 分析 Amber 轨迹或结合能 | `amber-md-expert` | `/amber-md-expert 帮我分析这条轨迹并汇总 RMSD、contacts 和 MM/GBSA` | 轨迹指标、表格、图片，以及证据边界清楚的分析报告。 |
| 运行本地 HDOCK 对接 | `hdock` | `/hdock 帮我用这些 receptor 和 ligand PDB 文件跑对接` | `hdock.out`、复合物模型、复制后的输入、日志和运行摘要。 |
| 创建或分析 HADDOCK 项目 | `haddock` | `/haddock 帮我用这些结构和约束创建一个 HADDOCK 项目` | HADDOCK 项目文件、约束文件、运行结果、cluster summary 和模型排名。 |
| 用 GPU 筛选配体库 | `unidock-pro` | `/unidock-pro 帮我用这个 receptor 筛选这个 ligand library，并给 top hits 排名` | ligand index、UniDock-Pro 输出、排序 CSV，以及模式和搜索框假设说明。 |
| 用 RFD3 做蛋白或 binder 设计 | `rfdiffusion3` | `/rfdiffusion3 帮我检查 chain 和残基编号后，为这个靶标设计 binder` | RFD3 设计结果、可选 MPNN/RF3 后处理配置和 QC 说明。 |
| 排序或检查 AlphaFold3 预测结果 | `af-analysis` | `/af-analysis 帮我给这些 AF3 结果排名，并生成 PAE 和界面指标` | Markdown/CSV 排名、ipTM_d0/pDockQ/mpDockQ 指标、PAE 图和分析摘要。 |

## 仓库结构

```text
skills/
  amber-md-expert/
  hdock/
  haddock/
  unidock-pro/
  rfdiffusion3/
  af-analysis/
```

每个列出的 skill 都有自己的 `SKILL.md`，并可能带有 `scripts/`、`references/`、`assets/`、`templates/` 或 `agents/` 等辅助目录。使用时先读对应 skill 的 `SKILL.md`，再按任务需要读取具体脚本或参考文档。

## 克隆到本地教程

当你想先获得一个本地可编辑副本，再安装到 Codex 或 Claude 的 skill 目录时，按下面流程操作。

1. 确认 Git 可用。

```bash
git --version
```

2. 选择一个工作目录并克隆仓库。

```bash
mkdir -p ~/repos
cd ~/repos
git clone https://github.com/makabaka007x/cadd-skill.git
cd cadd-skill
```

3. 确认 skill 目录存在。

```bash
ls skills
find skills -maxdepth 2 -name SKILL.md | sort
```

4. 后续从 GitHub 拉取更新。

```bash
cd ~/repos/cadd-skill
git pull --ff-only
```

5. 如果你已经配置好 GitHub SSH key，也可以用 SSH 克隆。

```bash
git clone git@github.com:makabaka007x/cadd-skill.git
```

只读使用时 HTTPS 最简单；如果你需要向仓库 push 修改，SSH 更方便。

## 安装到 Agent Skill 目录

把所有文档化的 skills 安装到 Codex skill root：

```bash
cd ~/repos/cadd-skill
mkdir -p ~/.codex/skills
for skill_name in amber-md-expert hdock haddock unidock-pro rfdiffusion3 af-analysis; do
  rsync -a "skills/$skill_name" ~/.codex/skills/
done
```

只安装单个 skill：

```bash
cd ~/repos/cadd-skill
mkdir -p ~/.codex/skills
rsync -a skills/unidock-pro ~/.codex/skills/
```

对于 Claude 风格的本地 skill root，把同样的目录复制到当前启用的 Claude skill 目录，例如：

```bash
cd ~/repos/cadd-skill
mkdir -p ~/.claude/skills
rsync -a skills/unidock-pro ~/.claude/skills/
```

如果本机有 validator，可以验证复制后的 skill：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/unidock-pro
```

如果没有 validator，至少确认目标 skill 目录包含 `SKILL.md`，YAML frontmatter 格式有效，并且没有写入机器私有路径。

## Skill 详细介绍

下面的示例是面向 Agent 的交互式调用方式，适合 Codex、Claude 或其他支持 skill 的 Agent。它们不是 shell 命令。Agent 应读取对应 `SKILL.md`，内部选择合适的辅助脚本，并在完成后报告实际执行了什么。

### `amber-md-expert`

**类别：** 分子动力学和 Amber 工作流打包。

**它能做什么：** 这个 skill 把 Amber 或 AmberTools 相关任务整理成可复现的本地或超算运行流程。它覆盖结构准备、拓扑生成、显式或隐式溶剂 MD、续跑逻辑、cpptraj 分析、MM/GBSA 或 PBSA、contact 分析，以及可上传超算的运行目录。

**什么时候用：** 用户提到 Amber、AmberTools、pdb4amber、tleap、antechamber、parmchk2、pmemd、cpptraj、MMPBSA.py、PBSA、REMD、膜体系、锌离子或非标准残基、核酸、DSSP、contact 分析，或者需要把 MD 任务打包到集群运行。

**常见输入：** 原始 PDB 或复合物结构、配体文件、已有 `prmtop`/`inpcrd`/`rst7`、轨迹、restart 文件、力场选择、模拟时长要求，以及目标集群限制。

**常见流程：** 先判断任务入口是原始结构准备、已有 Amber 拓扑打包，还是仅做后处理；再选择力场和水模型；生成或整理运行目录；补充上传和续跑说明；最后验证运行脚本和时间尺度，确认后再交付。

**Agent 交互式示例：**

- `/amber-md-expert 帮我把这个 Amber 体系打包成可上传超算运行的目录`
- `/amber-md-expert 帮我为这个蛋白-配体复合物准备显式溶剂 Amber 流程`
- `/amber-md-expert 帮我分析这条轨迹，汇总 RMSD、RoG、contacts 和 MM/GBSA`
- `/amber-md-expert 帮我检查这个 Amber restart 链能不能安全续跑`

**主要输出：** 结构化运行目录、准备文件、MD 输入文件、提交脚本、分析脚本、restart/续跑说明，以及用于超算打包时的 `UPLOAD_AND_RUN.md` 类说明文件。

**注意事项：** 力场和水模型是科学选择，不应被当成固定默认值。生产模拟时长必须在最终交付前确认。HPC partition、QOS、module 和 wall-time 策略都需要按目标集群调整。

### `hdock`

**类别：** 本地 HDOCKlite 对接。

**它能做什么：** 这个 skill 用于运行并打包可复现的 HDOCKlite 对接 case，适合蛋白-蛋白或蛋白-核酸体系。它可以运行 `hdock`，用 `createpl` 导出模型，保存日志，并生成便于检查的运行摘要。

**什么时候用：** 用户提到 HDOCK、HDOCKlite、`hdock`、`createpl`、受体/配体 PDB、`rsite.txt`、`lsite.txt`、`restr.txt`、结合位点约束，或希望从已有 `hdock.out` 生成复合物模型。

**常见输入：** 受体 PDB、配体 PDB、可选位点/约束文件、可选已有 `hdock.out`、输出目录，以及需要导出的模型数量。

**常见流程：** 检查受体和配体输入；判断是完整运行 docking，还是只从已有 `.out` 导出模型；由 Agent 内部调用合适的 wrapper；检查日志和 `run-summary.json`；报告生成的模型和原始打分结果。

**Agent 交互式示例：**

- `/hdock 帮我用 receptor.pdb 和 ligand.pdb 跑对接，并导出 top 20 模型`
- `/hdock 帮我用已有的 rsite.txt 和 lsite.txt 作为约束跑这个 docking case`
- `/hdock 帮我从这个 hdock.out 生成复合物模型`
- `/hdock 帮我把这个 HDOCK case 整理成输入、日志、分数和模型都清楚的结果目录`

**主要输出：** `hdock.out`、`models.pdb`、复制后的输入文件、stdout/stderr 日志，以及 `run-summary.json`。

**注意事项：** 约束文件只应在用户提供或科学上有依据时使用。原始 docking 分数不能等同于生物学验证。

### `haddock`

**类别：** HADDOCK 2.5 信息驱动对接。

**它能做什么：** 这个 skill 帮助创建、运行和分析 HADDOCK 2.5 项目，适用于蛋白-蛋白、蛋白-核酸、蛋白-小分子、多肽和约束驱动的对接工作流。

**什么时候用：** 用户提到 HADDOCK、HADDOCK 2.5、AIR restraints、ambiguous interaction restraints、对接示例、项目创建、CNS/HADDOCK 环境检查，或 HADDOCK cluster/score 分析。

**常见输入：** 分子 PDB、active/passive residues、AIR 或约束文件、HADDOCK 参数选择、项目名称，以及本地 HADDOCK 安装路径。

**常见流程：** 检查 HADDOCK 环境；创建或选择项目；准备约束和参数；运行对应示例或自定义项目；分析 cluster、score、可用时的 FCC/iRMSD，以及 top models。

**Agent 交互式示例：**

- `/haddock 帮我用这两个 PDB 创建一个蛋白-蛋白 HADDOCK 项目`
- `/haddock 帮我根据这些 active/passive residues 准备 AIR 约束`
- `/haddock 帮我运行 protein-DNA 示例并总结输出`
- `/haddock 帮我分析这个 HADDOCK run 目录并给 cluster 排名`

**主要输出：** HADDOCK 运行目录、参数文件、约束文件、cluster summary、score table，以及筛选出的 top models。

**注意事项：** HADDOCK 依赖 proprietary/local install。公开版 skill 使用占位路径，不能替代已经配置好的授权或本地环境。

### `unidock-pro`

**类别：** GPU 虚拟筛选。

**它能做什么：** 这个 skill 用于运行 UniDock-Pro 的 classical docking、ligand similarity searching 和 hybrid docking 工作流，并提供配体索引、批量运行和结果排序脚本。

**什么时候用：** 用户提到 UniDock-Pro、`udp`、GPU 虚拟筛选、`receptor.pdbqt`、`reference_ligand`、`ligand_index`、`ligand_dir`、`search_mode`、对接打分排序或批量筛选。

**常见输入：** docking/hybrid 模式需要 receptor PDBQT；similarity/hybrid 模式需要 reference ligand；还需要 ligand directory 或 ligand index、搜索框中心和尺寸、显式 search mode，以及输出目录。

**常见流程：** 判断任务属于 docking、similarity 还是 hybrid；如果只有配体目录，先建立 ligand index；确认搜索框和 `search_mode`；由 Agent 内部运行 wrapper；把 `*_out.pdbqt` 汇总成排序 CSV。

**Agent 交互式示例：**

- `/unidock-pro 帮我用这个 receptor 和 ligand library 做 classical docking，并输出 top 50 排名`
- `/unidock-pro 帮我给这个 ligand 目录建立 ligand index`
- `/unidock-pro 帮我用这个 reference ligand 做相似性搜索`
- `/unidock-pro 帮我用这个 receptor 和共晶 reference ligand 做 hybrid docking`

**主要输出：** UniDock-Pro 输出 PDBQT、日志、排序 CSV，以及实际运行模式和关键假设说明。

**注意事项：** `search_mode` 必须显式确认。hybrid 模式下 reference ligand 应与受体结合位点和构象假设匹配。不要把不同筛选任务的结果混在同一个输出目录里。

### `rfdiffusion3`

**类别：** 基于 Foundry/RFdiffusion3 的蛋白设计。

**它能做什么：** 这个 skill 用于验证和运行 RosettaCommons Foundry/RFdiffusion3 工作流，覆盖环境检查、checkpoint 路径、官方 demo smoke test、设计输入准备，以及下游后处理模板。

**什么时候用：** 用户提到 RFdiffusion3、RFD3、Foundry、rc-foundry、RF3、ProteinMPNN、LigandMPNN、checkpoint 下载、binder 设计、核酸 binder、小分子 binder、酶 scaffold、partial diffusion，或 RFD3 JSON/YAML 设计输入。

**常见输入：** 已配置的 Foundry/RFD3 环境、checkpoint 目录、目标 PDB/CIF、chain ID、残基编号、可选 ligand 名称、设计 JSON/YAML、输出目录，以及 GPU 限制。

**常见流程：** 先检查真实环境；验证 Python、torch/CUDA、Foundry CLI 和 checkpoint；昂贵 GPU 任务前先跑小 demo 或 smoke test；基于结构检查结果准备设计输入；必要时先使用低显存首轮设置；用户需要时再做 MPNN/RF3/QC 后处理。

**Agent 交互式示例：**

- `/rfdiffusion3 帮我检查这台机器能不能用现有 checkpoint 跑 RFdiffusion3`
- `/rfdiffusion3 帮我准备一个 smoke test，并说明环境是否可用`
- `/rfdiffusion3 帮我检查 chain ID 和残基编号后，为这个靶标设计 binder`
- `/rfdiffusion3 帮我为这些 RFD3 design 准备 MPNN 和 RF3 后处理`

**主要输出：** RFD3 设计结果、可选轨迹、设计 metadata、MPNN/RF3 后处理配置，以及 QC summary。

**注意事项：** 写设计输入前必须检查 chain ID、残基编号和 ligand residue name。GPU 显存和软件包版本差异会影响哪些官方教程字段可用。

### `af-analysis`

**类别：** AlphaFold3 输出分析。

**它能做什么：** 这个 skill 使用 `af-analysis` Python 包分析 AlphaFold3 Server zip 或本地 AF3 输出目录，重点是 ranking 和界面质量指标，而不仅是基础 ipTM。

**什么时候用：** 用户提到 AlphaFold3 Server `fold_*.zip`、本地 AF3 输出目录、ipTM_d0、pDockQ、mpDockQ、LIS、PAE matrix、PPI 质量排序，或 AF3 结果比较。

**常见输入：** 一个或多个 `fold_*.zip` 文件、本地 AF3 输出目录、输出路径，以及希望生成的表格或图形格式。

**常见流程：** 先对目录做快速 ranking；导出 Markdown 或 CSV；对重点样本做深度分析；检查 PAE 和界面指标；生物学解释必须受限于预测置信度。

**Agent 交互式示例：**

- `/af-analysis 帮我给这个目录下所有 AlphaFold3 fold_*.zip 做排名`
- `/af-analysis 帮我分析这个 AF3 结果，生成 PAE 图和界面指标`
- `/af-analysis 帮我用 ipTM_d0、pDockQ、mpDockQ 和 PAE 比较这些 AF3 模型`
- `/af-analysis 帮我把 ranking 表同时导出成 Markdown 和 CSV`

**主要输出：** ranking table、CSV/Markdown summary、PAE heatmap、analysis summary，以及可选的 notebook 风格 3D 可视化支持。

**注意事项：** 基于 NGLView 的 3D 可视化需要 Jupyter 兼容环境。AF3 置信度指标适合优先级排序，不能直接作为实验证据。

## 本地配置说明

这个公开仓库使用占位路径，例如：

- `/path/to/haddock2.5`
- `/path/to/UniDock-Pro`
- `/path/to/conda-envs/unidock-pro`
- `/path/to/conda-envs/foundry-py312`
- `/path/to/foundry/checkpoints`
- `/path/to/foundry/workspace`

运行任何工作流前，都需要把相关 `SKILL.md`、reference、config 或脚本参数改成当前机器的真实配置。集群 partition、QOS、GPU 限制、CPU 限制、module 名称和 wall-time 策略都只是示例，不能直接当作所有机器通用配置。

## 公开使用和安全说明

- 不要提交私人 home 目录、WSL mount 路径、集群账号、token、API key、密码或私钥内容。
- 仓库里的脚本是工作流辅助工具，不是完整环境安装器。
- 在昂贵的 docking、MD、筛选或蛋白设计任务前，先跑小规模验证或 smoke test。
- 科学结论必须受方法限制约束：docking score、AF3 置信度指标和设计输出是优先级证据，不是实验验证。
