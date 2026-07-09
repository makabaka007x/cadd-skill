# 本地到集群打包

## 目标

把 Amber 工作整理成“本地准备、上传一个目录、在目标机器上提交一个脚本”的工作形态。

## 默认目录结构

- 根目录：只放可直接运行的文件
- `prep/`：放追溯来源和准备阶段输入
- `UPLOAD_AND_RUN.md`：放上传、提交和续跑说明

标准显式溶剂工作流的根目录通常应包含：

- `complex-amber.top`
- `complex-amber.crd`
- `min1.in`、`min2.in`、`min3.in`
- `heat.in`、`nvt.in`、`npt1.in`、`npt2.in`、`npt3.in`、`npt4.in`
- `md.in`
- `run_slurm_gpu.sh`

## 集群配置原则

- 主引擎通常为 `pmemd.cuda` 或 `pmemd.MPI`，按目标机器实际安装选择。
- GPU/CPU partition、QOS、module、account、wall-time 都必须由用户或集群文档确认。
- 模板中的 `#SBATCH` 值只是占位示例，交付前要替换为目标集群可用值。
- 分析任务通常使用 CPU 队列，但不要假设具体队列名。
- 不要把某个机构的资源策略写进公开默认值。

## 打包行为

- 优先生成新的任务目录
- 把 `leap.in` 和其他准备文件保留在 `prep/`
- 不自动上传
- 可以生成 `scp` 或 `rsync` 命令模板
- 可以生成清晰的提交命令
- 复制或生成 `run.sh`、`run_slurm_gpu.sh` 这类脚本时，保留清晰的资源占位说明

## 推荐辅助脚本

- `scripts/create_run_dir.py`
- `scripts/render_upload_manifest.py`
- `scripts/validate_amber_task.py`
