# 核心工作流

## 标准显式溶剂路线

除非请求明确指向 REMD、膜蛋白、隐式溶剂、Zn 配位或其他特殊化学体系，否则优先走这条路线。

## 准备顺序

本地准备阶段默认使用新的 conda 环境：

- `conda activate AmberTools25`

只有在用户明确说明使用别的环境时，才改用其他环境名。

1. 必要时先用 `pdb4amber` 清洗 PDB。
2. 用 `antechamber` 和 `parmchk2` 处理配体参数。
3. 用 `tleap` 构建加水体系。
4. 打包成超算可运行目录。
5. 校验文件链和提交脚本。
6. 在把目录视为已完成前确认时长。

## 已有 Amber 文件路线

当 `.top` 和 `.crd` 已经存在时：

1. 跳过结构准备。
2. 把拓扑和坐标复制到选定模板族中。
3. 如果用户手里有 `leap.in`、PDB 或配体参数文件，把它们保留到 `prep/` 里以便追溯。
4. 校验运行链条，再汇总时长。

## 默认模板

- 标准显式溶剂：`assets/templates/standard-explicit/`
- 隐式溶剂：`assets/templates/implicit-solvent/`
- REMD：`assets/templates/remd/`
- 膜蛋白：`assets/templates/membrane/`

## 下一步参考

- 力场选择：`force-fields-and-water-models.md`
- 续跑逻辑：`restarts-and-job-control.md`
- 时长确认：`timescale-confirmation-policy.md`
