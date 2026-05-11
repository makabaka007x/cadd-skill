# 本地到超算打包

## 目标

把 Amber 工作整理成“本地准备、上传一个目录、在超算提交一个脚本”的工作形态。

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
- `run_slurm-4090.sh`

## 当前集群默认值

- 主队列：`gpu4090`
- 主引擎：`pmemd.cuda`
- 主提交流程：单 GPU，一次 `sbatch`
- 分析队列偏好：CPU
- 当前学校超算可见的 CPU 分区包括 `cpu6348` 和 `cpu8358`
- 常规单节点 CPU 分析或 CPU rescue 默认优先 `cpu6348`
- REMD 或高核数 CPU 工作流可按模板使用 `cpu8358`
- 提交脚本默认不写 `#SBATCH --time`
- 当前超算默认七天停止任务，除非用户明确要求，否则不要额外设置时长限制

## 打包行为

- 优先生成新的任务目录
- 把 `leap.in` 和其他准备文件保留在 `prep/`
- 不自动上传
- 可以生成 `scp` 或 `rsync` 命令模板
- 可以生成清晰的提交命令
- 复制或生成 `run.sh`、`run_slurm-4090.sh` 这类脚本时，默认保持“无 `#SBATCH --time`”状态

## 推荐辅助脚本

- `scripts/create_run_dir.py`
- `scripts/render_upload_manifest.py`
- `scripts/validate_amber_task.py`
