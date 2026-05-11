# REST2 / HREMD 边界说明

这个 skill 现在支持两条主路径：

- `sampling.mode=tremd`
- `sampling.mode=rest2`

REST2 的当前实现是 v2 能力驱动路线：

- `grompp -pp` 生成 processed topology
- 在 `[ atoms ]` section 给 hot atom types 加 `_`
- `plumed partial_tempering scale` 生成每个 replica 的缩放拓扑
- 如果 `mdrun -h` 同时有 `-hrex` 和 `-plumed`，才使用 `mdrun -multidir ... -hrex -plumed plumed.dat -dlb no` 正式交换
- 如果只有 `-plumed` 没有 `-hrex`，只生成 REST2 拓扑准备/预检包，并阻断生产提交

详细流程见 [rest2-workflow.md](rest2-workflow.md)。

## 仍然不要自动完成的情况

如果用户请求下面内容，先停下来说明需要人工审查：

- 不是 PLUMED `partial_tempering` 的手工 Hamiltonian 缩放
- CHARMM CMAP 或其他已知对 `partial_tempering` 敏感的力场项
- 同时改变拓扑、温度、lambda、压力的复杂 HREX 组合
- PTM、金属中心、共价配体、膜体系等需要专门验证的 hot region
- 要求自动安装或重新编译 GROMACS/PLUMED

这些情况可以继续做打包框架，但必须把“需要人工检查/试跑验证”写进输出说明。
