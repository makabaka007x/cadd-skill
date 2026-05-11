---
name: amber-md-expert
description: 把 Amber 分子动力学任务从本地准备整理为可直接上传并在超算提交的运行目录。用于 Amber 或 AmberTools、pdb4amber、tleap、antechamber、parmchk2、pmemd、cpptraj、MMPBSA 或 PBSA、REMD、膜蛋白或隐式溶剂体系、Zn 或非标准残基、contact 分析、DSSP 或 DSSPplot，以及任何“本地建模后打包到超算，一次 sbatch 就能跑”的场景。
---

# Amber 分子动力学专家

## 概述

用这个 skill 把 Amber 工作整理成“本地准备到超算直跑”的可复用流程。
默认目标不是只解释 Amber，而是给用户留下一个可以直接上传并提交的运行目录。

## 默认工作流

先把请求归到下面三类入口之一：

1. 原始结构准备
- 适用于用户只有蛋白、配体、复合物或残基文件，还没有最终 Amber 拓扑和坐标。
- 在本地使用 `pdb4amber`、`antechamber`、`parmchk2` 和 `tleap` 完成准备。
- 本地 AmberTools 命令默认假设运行在 `AmberTools25` 环境中，优先使用
  `conda activate AmberTools25`。
- 然后打包成可直接上传到超算的任务目录。

2. 已有 Amber 拓扑打包
- 适用于用户已经有 `.top/.prmtop/.parm7` 和 `.crd/.inpcrd/.rst7`。
- 跳过本地建模。
- 直接打包成超算可运行目录。

3. 仅分析后处理
- 适用于用户已经有轨迹，或者想做 cpptraj、MMPBSA、contact、DSSP/DSSPplot。
- 默认按需生成分析包，而不是预先塞进每个上传目录。

除非请求明确属于其他分支，否则优先走标准蛋白-配体显式溶剂流程。

## 打包规则

准备超算任务目录时，遵循这些默认规则：

- 先适配当前集群。
- 主流程优先使用 `gpu4090` 单卡 `pmemd.cuda` 脚本。
- 优先创建新的任务目录，而不是直接修改标准模板。
- 任务目录命名采用 `project_stage`，例如 `proj1_explicit_gpu`。
- 可直接运行的文件放在任务根目录。
- 追溯来源文件放在 `prep/`。
- 生成 `UPLOAD_AND_RUN.md`，写清上传、提交和续跑说明。
- 可以给出 `scp` 或 `rsync` 命令模板，但不要真的执行上传。
- 默认不要往 `run.sh` 或其他提交脚本里添加 `#SBATCH --time`。
- 当前超算环境默认七天终止任务，因此除非用户明确要求，否则沿用集群默认时间限制。
- 当前学校超算的 CPU 分区至少包括 `cpu6348` 和 `cpu8358`；常规单节点 CPU 分析或 CPU rescue 优先用 `cpu6348`，REMD 或高核数 CPU 模板可用 `cpu8358`。

在需要稳定打包时，使用 `scripts/create_run_dir.py`。
更新上传说明时，使用 `scripts/render_upload_manifest.py`。
把目录当成“已就绪”之前，先运行 `scripts/validate_amber_task.py`。

## 力场与模板选择

在锁定流程之前，先用自然语言推荐当前体系最合适的力场和水模型组合。
可以用模板作为默认值，但不要静默假设每次都是同一个科学选择。

优先参考：

- 标准工作流和默认模板：
  `references/core-workflow.md`
- 力场与水模型建议：
  `references/force-fields-and-water-models.md`
- Zn、核酸、非标准残基、糖基化样特殊成键：
  `references/special-cases-nonstandard-zn-glyco-nucleic.md`

打包时使用这些模板目录：

- `assets/templates/standard-explicit/`
- `assets/templates/implicit-solvent/`
- `assets/templates/remd/`
- `assets/templates/membrane/`
- `assets/templates/nonstandard/`
- `assets/templates/zn/`

## 位置约束规则

在显式溶剂预平衡阶段，默认目标是先让溶剂和离子重排，再让主体逐步放开。

- 默认 `ntr` 应约束溶质重原子，而不是水和离子。
- 不要把 `(:WAT|Na+|Cl-)` 这类 mask 解释成“约束 DNA”；它实际选中的是溶剂或离子。
- 写补集 mask 时优先显式加括号，例如 `!(:WAT,Na+,Cl-)` 或 `!(:WAT|:Na+|:Cl-)`，避免取反范围歧义。
- 对“只有核酸 + 水 + 单价离子”的显式溶剂体系，可优先用 `!(:WAT,Na+,Cl-) & !@H=` 约束核酸重原子。
- 如果体系里还有蛋白、配体、二价金属或其他辅因子，不要直接套用上面的核酸 mask，先按真实要固定的主体重写。

## 时长确认规则

在把一个 MD 目录视为“可提交运行”之前，必须停下来确认时长。
这是用户的硬性偏好。

在写入最终生产级 `.in` 文件，或把目录交付为已完成之前：

- 汇总 minimization 的级数和步数。
- 汇总 heat 时长。
- 汇总 NVT 时长。
- 汇总每个 NPT 阶段时长。
- 汇总 production 时长。
- 同时展示人可读时长和 Amber 参数，例如 `nstlim`、`dt`。
- 明确询问用户是保留还是修改当前方案。

如果请求里已经给了明确时长，也要先复述一遍并做最终确认，然后再视为完成。

用 `scripts/summarize_timescales.py` 生成整洁的阶段汇总。
详细规则见 `references/timescale-confirmation-policy.md`。

## 续跑与安全规则

在续跑或扩展已有任务之前：

- 检查 restart 链条。
- 检查 `ntx` 和 `irest`。
- 检查提交脚本是否读取了正确的 restart 文件。
- 除非用户明确要求覆盖，否则优先生成新的输出文件名。

可配合 `scripts/validate_amber_task.py` 和
`references/restarts-and-job-control.md` 使用。

## 分析默认策略

不要把分析脚本自动塞进每个上传包。
把分析策略保留在 skill 中，等用户明确要分析时再生成分析包。

默认最小 cpptraj 分析包只保留：

- `autoimage`
- `rms first @CA`
- `strip :WAT|(:Na+|:Cl-)`
- 输出去水去离子轨迹 `md-nW.xtc`
- 输出第一帧 `md-first.pdb`
- 输出最后一帧 `md-last.pdb`

生成最小分析包时：

- 写出 `analysis.sh`
- 写出 `cpptraj.in`
- 在运行时自动识别最后一帧，而不是硬编码

使用 `scripts/generate_analysis_bundle.py` 时：

- `minimal` 用于最小轨迹处理和首末帧导出
- `contact` 用于复制 contact 分析辅助脚本
- `dsspplot` 用于复制 DSSP 和绘图辅助脚本

参考：

- `references/analysis-cpptraj-mmpbsa.md`
- `references/analysis-contact-dssp.md`
- `assets/templates/analysis-minimal/`
- `assets/templates/contact/`
- `assets/templates/dsspplot/`

## 高级分支

当请求明显属于下面场景时，不要继续沿用标准显式溶剂流程：

- 隐式溶剂
- REMD
- 膜蛋白
- Zn 配位
- 非标准残基
- 核酸
- contact 分析
- DSSP 或 DSSPplot

只加载该分支需要的 reference 和 template 子目录。
不要一次性读入无关资源。
