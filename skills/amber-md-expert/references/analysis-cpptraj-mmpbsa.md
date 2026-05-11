# 分析：Cpptraj 与 MMPBSA

## 默认最小分析包

不要把分析脚本预先塞进每个上传目录。只有用户明确提出分析需求时再生成。

最小 cpptraj 分析包应只保留：

- `autoimage`
- `rms first @CA`
- `strip :WAT|(:Na+|:Cl-)`
- `trajout md-nW.xtc`
- `trajout md-first.pdb`
- `trajout md-last.pdb`

最后一帧必须在运行时自动解析，不能写死。

使用 `scripts/generate_analysis_bundle.py --mode minimal`。

## MMPBSA 或 PBSA

只有在用户明确要求时才生成 MMPBSA 或 PBSA 输入。
确保下面这些拓扑和轨迹关系清晰：

- 去水后的 complex 拓扑
- receptor 拓扑
- ligand 拓扑
- 对应的轨迹

如果这些拓扑的来源关系不清楚，先停下来澄清。
