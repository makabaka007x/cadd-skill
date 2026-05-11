# 分析：Contact 与 DSSP

## Contact 分析

当用户要做以下内容时，进入 contact 分支：

- 每帧接触数统计
- 不同接触类型的统计
- 残基对频率分析
- contact 热图

内置辅助文件在 `assets/templates/contact/`。
用 `scripts/generate_analysis_bundle.py --mode contact` 生成。

## DSSP 与 DSSPplot

当用户要做以下内容时，进入 DSSP 分支：

- 用 `secstruct` 提取 Amber 二级结构
- 处理 `ss_summary.dat` 风格结果
- 用 DSSPplot 辅助脚本绘制二级结构图

内置辅助文件在 `assets/templates/dsspplot/`。
用 `scripts/generate_analysis_bundle.py --mode dsspplot` 生成。

## 默认分析拆分

- 主上传包：默认不带分析脚本
- 按需分析包：最小 cpptraj，再按需要追加 contact 或 DSSP 辅助文件
