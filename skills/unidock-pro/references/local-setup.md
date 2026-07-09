# UniDock-Pro 本地安装模板

## 路径

- 仓库路径：`/path/to/UniDock-Pro`
- 主二进制：`/path/to/UniDock-Pro/build/udp`
- Conda 环境路径：`/path/to/conda-envs/unidock-pro`
- 示例目录：`/path/to/UniDock-Pro/example`
- 现成结果目录：`/path/to/UniDock-Pro/results`

## 环境判定

先用 `conda info --envs` 或等效命令确认目标机器是否有：

- `unidock-pro` -> `/path/to/conda-envs/unidock-pro`

优先采用下面的探测顺序：

1. 直接运行 `/path/to/UniDock-Pro/build/udp`
2. `source ~/miniconda3/etc/profile.d/conda.sh && conda activate unidock-pro`
3. 回退到环境前缀 `/path/to/conda-envs/unidock-pro`

## 构建与重建

如果 `build/udp` 缺失或不可运行，按下面顺序处理：

```bash
cd /path/to/UniDock-Pro
source ~/miniconda3/etc/profile.d/conda.sh
conda activate unidock-pro
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j"$(nproc)"
```

如果 CUDA 不在默认路径，再补：

```bash
cmake -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCUDA_TOOLKIT_ROOT_DIR=/usr/local/cuda
```

## 文档与源码偏差

当前仓库有一个重要偏差必须记住：

- README 和教程文档里经常写 `--ligand_directory`
- 当前源码 `src/main/main.cpp` 注册的真实参数是 `--ligand_dir`

因此写脚本和最终命令时一律用：

```bash
--ligand_dir /path/to/ligands
```

不要直接照抄 `--ligand_directory`。

## 真实模式判定

源码逻辑按参数存在情况区分模式：

- 有 `receptor`、没有 `reference_ligand` -> pure docking
- 没有 `receptor`、有 `reference_ligand` -> similarity searching
- 同时有 `receptor` 和 `reference_ligand` -> hybrid

## search_mode 规则

源码接受这些值：

- `fast`
- `balance`
- `balanced`
- `detail`
- `detailed`

和用户确认时只使用三种规范写法：

- `fast`
- `balance`
- `detail`

如果用户没有明确指定哪一种：

- 必须先问
- 不要根据“大规模筛选通常用 fast”之类经验直接代选
