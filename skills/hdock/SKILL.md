---
name: hdock
description: 在本地 HDOCKlite 环境中运行蛋白-蛋白或蛋白-核酸对接，并生成 `hdock.out` 与复合物模型。用于用户提到 HDOCK/HDOCKlite、`hdock`、`createpl`、受体/配体 PDB、`rsite.txt`、`lsite.txt`、`restr.txt`、结合位点约束、对接结果打包，或希望把当前仓库整理成可复用 HDOCK 工作流的场景。
---

# HDOCK 本地对接

把任务默认理解为“交付一个能复现的本地 HDOCK case 目录”，而不是只解释命令行。
优先留下可直接检查的输出目录、日志和模型文件。

## 默认工作流

先把请求归到下面两类之一：

1. 从受体/配体 PDB 开始做完整对接
- 输入通常是两个 PDB 文件。
- 可选加入 `rsite.txt`、`lsite.txt` 或 `restr.txt` 做约束。
- 先运行 `hdock` 生成 `hdock.out`，再运行 `createpl` 生成复合物模型。

2. 已经有 `.out` 文件，只需要导出模型
- 直接使用已有 `hdock.out` 或同类输出。
- 跳过 docking，调用 `createpl` 生成 `models.pdb`。

默认优先使用 `scripts/run_hdock_case.py`，因为它会：

- 自动定位 `hdock` 和 `createpl`
- 把输入复制进 case 目录
- 保存 stdout/stderr 日志
- 生成 `run-summary.json`

## 输入检查

开始前先确认：

- 受体和配体是否为 PDB
- 是否需要位点约束或残基约束
- 用户要的是原始打分结果、聚类后的 top pose，还是复合物模型
- 输出目录是否应该新建，避免覆盖已有结果

如果用户没有明确要求覆盖，优先创建新的 case 目录。

## 约束文件规则

只在用户明确提供或确认需要时传入约束文件。

- `rsite.txt`：受体位点残基列表
- `lsite.txt`：配体位点残基列表
- `restr.txt`：受体-配体约束

当前仓库里 `rsite.txt` 的示例内容是 `A:843`，因此位点文件至少支持“一行一个链:残基号”的格式。
如果用户的约束文件格式不清楚，先检查现有文件内容，不要凭空生成。

## 推荐命令路径

完整对接默认命令链：

```bash
python3 skills/hdock/scripts/run_hdock_case.py receptor.pdb ligand.pdb \
  --output-dir runs/case1 \
  --nmax 20
```

如果只从已有 `.out` 导出模型：

```bash
python3 skills/hdock/scripts/run_hdock_case.py \
  --hdock-out test.out \
  --output-dir runs/from-out \
  --nmax 20
```

如果 skill 不在 HDOCK 仓库内部，先指定二进制位置：

```bash
HDOCK_BIN_DIR=/path/to/HDOCKlite-v1.1 \
python3 skills/hdock/scripts/run_hdock_case.py receptor.pdb ligand.pdb --output-dir runs/case1
```

## 输出约定

交付时优先说明这些文件：

- `hdock.out`：原始 docking 输出
- `models.pdb`：`createpl` 导出的模型
- `inputs/`：复制后的输入文件
- `hdock.stdout.log` / `hdock.stderr.log`
- `createpl.stdout.log` / `createpl.stderr.log`
- `run-summary.json`

如果用户只要求原始打分，不要额外声称模型已经过生物学验证。

## 资源

- 命令和文件约定：`references/command-reference.md`
- 稳定执行脚本：`scripts/run_hdock_case.py`
