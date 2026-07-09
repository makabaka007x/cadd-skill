---
name: af-analysis
description: Analyze AlphaFold3 prediction outputs with the af-analysis Python package. Use for AlphaFold Server fold_*.zip files, local AF3 output directories containing model structures and JSON files, ipTM_d0, pDockQ, mpDockQ, LIS, PAE matrices, ranking AF3 models, or generating AF3 interface-quality summaries and plots.
---

# AlphaFold3 深度分析 (af-analysis)

## 安装

`af-analysis` 包已安装 (v0.1.5)。如需要重新安装：

```bash
pip install af-analysis
```

依赖包：`cmcrameri`, `ipywidgets`, `mdanalysis`, `nglview`, `numpy`, `pandas`, `pdb_numpy`, `scikit-learn`, `seaborn`, `tqdm`

## 触发条件

- 工作目录包含 `fold_*.zip` 文件（AlphaFold Server 输出）
- 或工作目录包含 AlphaFold3 本地运行的输出目录（含 `.cif`/`.pdb` + `json` 文件）
- 需要深度分析 PPI 预测质量（超越基础 IPTM 排序）

## 使用方法

### 1. 快速 Ranking 分析

生成按 ipTM 排序的对比表格（输出到终端）：

```bash
python /path/to/cadd-skill/skills/af-analysis/af3_ranking.py --input .
```

输出到文件：

```bash
# Markdown 格式
python /path/to/cadd-skill/skills/af-analysis/af3_ranking.py --input . --output af3_ranking.md --format markdown

# CSV 格式（可用 Excel 打开）
python /path/to/cadd-skill/skills/af-analysis/af3_ranking.py --input . --output af3_ranking.csv --format csv

# 同时输出两种格式
python /path/to/cadd-skill/skills/af-analysis/af3_ranking.py --input . --output af3_ranking --format both
```

### 2. 深度分析单个样本

```bash
python /path/to/cadd-skill/skills/af-analysis/af3_deepanalyze.py --zip fold_target_complex.zip --output target_complex_analysis/
```

输出包括：
- `analysis_summary.txt` - 分析报告
- `pae_matrix.png` - PAE 矩阵热图

## 输出指标说明

| 指标 | 说明 | 质量判断 |
|------|------|----------|
| **ipTM** | 接口预测模板分数 (AlphaFold3 原生) | >0.4 高质量，0.2-0.4 中等，<0.2 低质量 |
| **ipTM_d0** | 基于 Dunbrack 实验室方法的改进 ipTM | 更可靠的 PPI 质量指标 |
| **pTM** | 整体预测模板分数 | 越高越好 |
| **pDockQ** | 蛋白 - 蛋白相互作用质量评分 | >0.23 可能是生物复合物，>0.49 高质量 |
| **mpDockQ** | 多链 pDockQ | 适用于多聚体复合物 |
| **Chain Pair PAE Min** | 链间最小 PAE | <10 表示界面可靠 |
| **LIS** | 局部相互作用评分 | 补充评估界面质量 |

## 示例输出

### Ranking 表格

```markdown
| 排名 | 项目名称 | ipTM | ipTM_d0 | pDockQ | PTM | Chain Pair PAE Min |
|------|----------|------|---------|--------|-----|-------------------|
| 1 | target_partner_1 | 0.49 | 0.52 | 0.61 | 0.52 | 3.66 |
| 2 | target_partner_2 | 0.42 | 0.45 | 0.53 | 0.45 | 3.82 |
| 3 | low_confidence_pair | 0.16 | 0.18 | 0.12 | 0.57 | 25.62 |
```

### 深度分析报告

包含：
- PAE 矩阵热图（链内 + 链间）
- pLDDT 分布图
- 3D 结构可视化（使用 NGLView）
- 界面残基分析

## Python API 使用示例

```python
from af_analysis import Data
from af_analysis.analysis import ipTM_d0, pdockq, mpdockq

# 加载数据
data = Data(directory=".", format="af3_webserver")

# 计算高级指标
ipTM_d0(data)
pdockq(data)
mpdockq(data)

# 查看结果
print(data.df[["query", "ipTM", "ipTM_d0_A_B", "pDockQ", "mpDockQ"]])

# 绘制 PAE 矩阵
data.plot_pae(index=0)

# 显示 3D 结构
data.show_3d(index=0)
```

## 注意事项

1. **zip 文件处理**: 脚本会自动解压 zip 文件到临时目录进行分析
2. **数据格式**: af-analysis 包期望特定命名格式，脚本会自动处理转换
3. **可视化依赖**: NGLView 需要在 Jupyter 环境中使用
4. **内存使用**: 大批量分析时注意内存占用，建议分批处理

## 与 af3-ranking 的区别

| 特性 | af3-ranking (旧) | af-analysis (新) |
|------|-----------------|-----------------|
| 实现方式 | Shell + jq | Python + af-analysis 包 |
| 指标 | IPTM, PTM, PAE | ipTM, ipTM_d0, pDockQ, mpDockQ, LIS |
| 可视化 | 无 | PAE 热图、pLDDT 分布、3D 结构 |
| 输出格式 | Markdown/CSV | Markdown/CSV + 图表 + 报告 |
| 适用场景 | 快速筛查 | 深度分析 |

## 参考文献

- [AlphaFold3 Nature Paper](https://www.nature.com/articles/s41586-024-07487-w)
- [af-analysis GitHub](https://github.com/samuelmurail/af_analysis)
- [ipSAE/Dunbrack 方法](https://www.biorxiv.org/content/10.1101/2025.01.07.631673v1)
- [pDockQ](https://www.nature.com/articles/s41467-022-28865-w)
