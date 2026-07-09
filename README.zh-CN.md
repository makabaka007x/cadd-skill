# CADD Skill Collection

English version: [README.md](README.md)

这个仓库提供可复用的 Codex/Claude 风格 skill，面向 CADD/AIDD 工作流，覆盖分子对接、虚拟筛选、分子动力学、增强采样、蛋白设计、AlphaFold3 结果分析，以及公开化学/生物数据库查询。

这些 skill 是给 Agent 使用的说明和少量辅助脚本，不是完整软件安装器。支持 skill 的 Agent 应先读取对应 `SKILL.md`，检查用户的真实输入、路径和运行环境，再适配执行或打包可复现工作流。

## 快速选择

| 任务 | Skill | 适合场景 | 典型输出 |
| --- | --- | --- | --- |
| Amber MD 准备或分析 | `amber-md-expert` | Amber/AmberTools、拓扑准备、cpptraj、MM/GBSA、PBSA、续跑检查 | MD 运行目录、分析脚本、图片、总结说明 |
| GROMACS 常规 MD | `gmx-workflow-packer` | EM、NVT、NPT、production MD、GROMACS 运行打包 | 常规 MD bundle，含 `mdp/`、`run.sh`、`state.yaml`、分析说明 |
| GROMACS tREMD/REST2 | `gmx-workflow-packer` | tREMD、REST2/HREX、PLUMED partial tempering、demux、交换效率分析 | replica 运行包、HREX 预检结果、后处理脚本 |
| 本地 HDOCK 对接 | `hdock` | 蛋白-蛋白或蛋白-核酸 HDOCKlite case | `hdock.out`、复合物模型、日志、运行摘要 |
| HADDOCK 对接 | `haddock` | active/passive residues、AIR restraints、信息驱动对接 | HADDOCK 项目、约束文件、cluster summary、模型排名 |
| GPU 虚拟筛选 | `unidock-pro` | UniDock-Pro classical docking、similarity search、hybrid docking | ligand index、对接输出、排序 CSV、搜索框和模式说明 |
| RFdiffusion3 设计 | `rfdiffusion3` | Foundry/RFD3 binder、核酸 binder、小分子 binder、enzyme scaffold | RFD3 输入、smoke test 说明、设计输出、QC/后处理模板 |
| AlphaFold3 结果分析 | `af-analysis` | AF3 Server `fold_*.zip`、本地 AF3 输出、PAE/界面指标 | 排名表、CSV/Markdown summary、PAE 图、界面指标 |
| PubChem 查询 | `pubchem-pug-skill` | 化合物性质、描述、assay summary、substance | 精简 PubChem 摘要，或按需保存 raw payload |
| ChEMBL 查询 | `chembl-skill` | activity、molecule、target、mechanism、文本搜索 | 精简活性或靶点摘要 |
| BindingDB 查询 | `bindingdb-skill` | 按 PDB、UniProt 或相似性查询靶点-配体结合记录 | 精简结合证据摘要 |
| RCSB PDB 查询 | `rcsb-pdb-skill` | PDB metadata、结构搜索、FASTA 下载 | 结构 metadata、链和来源总结 |
| UniProt 查询 | `uniprot-skill` | UniProtKB、UniRef、UniParc、FASTA、注释 | 蛋白身份、序列、功能注释摘要 |
| ChEBI 查询 | `chebi-skill` | 化学身份、ontology、结构 metadata | 精简 ChEBI 化合物/ontology 摘要 |

## 仓库结构

```text
skills/
  af-analysis/
  amber-md-expert/
  bindingdb-skill/
  chebi-skill/
  chembl-skill/
  gmx-workflow-packer/
  haddock/
  hdock/
  pubchem-pug-skill/
  rcsb-pdb-skill/
  rfdiffusion3/
  unidock-pro/
  uniprot-skill/
```

每个 skill 都有必需的 `SKILL.md`，并可能带有 `scripts/`、`references/`、`assets/` 或 `agents/`。使用时先读 `SKILL.md`，再按任务需要读取具体引用的脚本或文档。

## 安装

克隆仓库：

```bash
mkdir -p ~/repos
cd ~/repos
git clone https://github.com/makabaka007x/cadd-skill.git
cd cadd-skill
```

安装所有 skill 到 Codex skill root：

```bash
mkdir -p ~/.codex/skills
for skill_dir in skills/*; do
  [ -f "$skill_dir/SKILL.md" ] && rsync -a "$skill_dir" ~/.codex/skills/
done
```

只安装单个 skill：

```bash
mkdir -p ~/.codex/skills
rsync -a skills/gmx-workflow-packer ~/.codex/skills/
```

如果使用 Claude 风格的本地 skill root，把同样目录复制到当前启用的 Claude skill 目录：

```bash
mkdir -p ~/.claude/skills
rsync -a skills/unidock-pro ~/.claude/skills/
```

检查 skill 列表：

```bash
find skills -maxdepth 2 -name SKILL.md | sort
```

如果本地有 skill validator：

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/gmx-workflow-packer
```

## 联合调用示例

下面是给支持 skill 的 Agent 的 prompt，不是 shell 命令。

### 虚拟筛选

先用数据库 skill 明确靶点和配体集合，再用 UniDock-Pro 对接：

```text
Use $uniprot-skill and $rcsb-pdb-skill to confirm the target identity, available structures, chain IDs, and co-crystal ligands. Then use $chembl-skill, $bindingdb-skill, and $pubchem-pug-skill to collect known ligands and activity evidence. Build a ligand library, run $unidock-pro classical docking against the prepared receptor, and return a ranked CSV with the assumptions for the search box and search_mode.
```

对接后的补充注释：

```text
Use $bindingdb-skill and $chembl-skill to annotate the top 50 UniDock-Pro hits with known target or analog evidence, then summarize which hits are novel versus already supported by binding data.
```

### 分子对接

对接前先核对序列和结构来源：

```text
Use $uniprot-skill to confirm the protein sequence and domain boundaries, then use $rcsb-pdb-skill to identify suitable template structures. If this is protein-protein or protein-nucleic-acid docking, run $hdock and export the top models. If active/passive residues or AIR restraints are available, prepare a $haddock project and rank the resulting clusters.
```

配体身份核对：

```text
Use $pubchem-pug-skill and $chebi-skill to confirm the ligand identity, synonyms, charge-relevant metadata, and structure identifiers before preparing the docking inputs.
```

### 分子动力学模拟

先核对结构/数据库来源，再选择 Amber 或 GROMACS：

```text
Use $rcsb-pdb-skill and $uniprot-skill to verify the source structure, chain IDs, mutations, missing residues, and sequence coverage. Then use $amber-md-expert to prepare an Amber explicit-solvent MD package with restart checks and basic cpptraj analysis.
```

GROMACS 常规 MD：

```text
Use $gmx-workflow-packer to build a conventional GROMACS MD bundle from this prepared topol.top and 1EM.gro. Generate EM/NVT/NPT/production MDP files, a resumable run.sh, state.yaml, UPLOAD_AND_RUN.md, and basic analysis notes.
```

GROMACS 增强采样：

```text
Use $gmx-workflow-packer to prepare a tREMD bundle for this GROMACS system, estimate or validate the temperature ladder, create step1/step2/run.sh, and include demux plus exchange-efficiency analysis scripts. If I ask for REST2, first check whether the target GROMACS/PLUMED module supports both -plumed and -hrex.
```

### AF3 到设计或 MD 筛选

```text
Use $af-analysis to rank these AlphaFold3 fold_*.zip files by ipTM_d0, pDockQ, mpDockQ, and PAE. For the best-supported interface, prepare either an $amber-md-expert or $gmx-workflow-packer MD package for stability checks, and keep all conclusions limited to prediction confidence until experimental or simulation evidence exists.
```

## 公开使用说明

- 把 `/path/to/...`、`<cpu-partition>`、`<gpu-qos>` 这类占位路径改成目标机器真实配置。
- 数据库 skill 默认返回精简摘要；只有用户明确要求时才保存 raw API payload。
- 不要提交私人 home 目录、WSL mount 路径、集群账号、token、API key、密码、私钥或未公开课题数据。
- 昂贵的 docking、MD、筛选或蛋白设计任务前，先跑小规模 smoke test。
- docking score、AF3 置信度指标和设计输出只能作为优先级证据，不能直接当作实验验证。
