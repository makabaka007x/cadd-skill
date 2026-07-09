# tREMD 核心工作流

## 定位

这个参考只服务标准 GROMACS 温度 REMD。
REST2 v2 见 [rest2-workflow.md](rest2-workflow.md)。这里的目标是把标准温度 REMD 整理成稳定、可复用、适合目标机器投递的运行包。

## 工作流来源

标准流程可以概括为：

1. 本地准备体系
- `pdb2gmx`
- `editconf`
- `solvate`
- `genion`
- `EM`

2. 生成温度梯度
- 根据 `Tmin/Tmax`
- 结合蛋白原子数和水分子数
- 先得到一个经验梯度，再短跑检查交换率

3. `step1` 多副本预平衡
- 每个副本有独立温度
- 顺序执行 `PR -> NVT -> NPT`
- 结束后只保留后续需要的坐标

4. `step2` 生成正式生产 `tpr`
- 每个副本都从自己的 `4NPT.gro` 继续
- 统一前缀为 `5MD`

5. `run.sh` 正式多副本交换
- 使用 `gmx_mpi mdrun -multidir`
- 分段续跑
- 依赖 checkpoint 接力

6. demux 与交换效率分析
- 从 `5MD.log` 提取交换历史
- 生成 `replica_index.xvg`
- 重新组织轨迹
- 分析交换率、walk、RTT、residence time

## 集群配置

### GPU 阶段

- `partition=<gpu-partition>`
- `qos=<gpu-qos>`
- `cpus-per-task=4`
- 主要用于 `step1` 和 `step2`

### CPU 阶段

- `partition=<cpu-partition>`
- `qos=<cpu-qos>`
- `cpus-per-task=1`
- `max_total_tasks=<cluster-limit>`
- 主要用于正式 `run.sh`

正式多副本 CPU 作业模板：

```bash
#SBATCH -p <cpu-partition>
#SBATCH --qos=<cpu-qos>
#SBATCH -N 1
#SBATCH --ntasks-per-node=<replica-count>
#SBATCH --cpus-per-task=1
```

如果 replica 数超过集群或 QOS 限制，先减少 replica 数，或让用户确认已经获得更高资源限制后再改配置。
默认模板使用 8-replica 手动温度表示例。真实项目仍应先短跑检查交换率。

### 模块与可执行

- 模块：使用目标机器真实可用的 GROMACS 模块名。
- 可执行：`gmx` 或 `gmx_mpi`，按模块实际提供的命令设置。

## 必须修正的旧问题

### 1. 不再沿用旧的温度循环写法

旧版 `step2.sh` 使用逗号字符串直接 `for temp in $T`，这会把整串字符串当成一个 shell 词，容易把温度循环写错。

当前工作流必须：

- 先把温度表转换成真正的列表
- 或直接写成 YAML/CSV
- 再逐个副本渲染温度

### 2. 不再在正式 run 脚本里使用 `-maxh`

续跑逻辑应建立在：

- `-cpi`
- `-append`
- `state.yaml`
- 分段总步数控制

而不是依赖 `-maxh`。

### 3. 不再使用不稳定目录命名

旧版目录有 `equ_0`、`MD_0` 这样的命名。
当前工作流要统一改成：

- `replica_00`
- `replica_01`
- `replica_02`

避免多位数目录在 glob 展开时顺序错乱。

## 默认科学设定

### 标准蛋白

- 力场：`amber99sb-ildn`
- 水模型：`TIP3P`

### 蛋白配体

- 蛋白：`amber99sb-ildn`
- 水模型：`TIP3P`
- 配体：`ACPYPE/GAFF`

依赖缺失时只给安装建议，不自动安装。

## 何时停下来提醒用户

出现下面任一情况时，不要假装已经自动解决：

- 用户要求 REST2 但当前 GROMACS 只有 `-plumed` 没有 `-hrex`
- 用户要求 HREMD 或复杂 lambda 交换
- 用户要求 IDP/PTM 专用采样策略
- 用户没有任何能通向 `1EM.gro + topol.top` 的输入
- 用户要求自动安装 ACPYPE 或 AmberTools
- 用户要求生产脚本加入固定 `#SBATCH --time`
