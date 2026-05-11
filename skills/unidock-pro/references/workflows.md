# UniDock-Pro 工作流模板

## 推荐原则

优先使用 `scripts/run_unidock_case.py`，只在脚本不能覆盖需求时才直接手写 `udp` 命令。
批量任务总是显式传入输出目录，并为每个任务新建独立目录。
`search_mode` 每次都要由用户明确指定；如果用户没说，就先问，不要默认代选。

## 1. Pure Docking

适用条件：

- 有受体 `receptor.pdbqt`
- 没有 `reference_ligand`

优先入口：

```bash
python3 scripts/run_unidock_case.py \
  --mode docking \
  --receptor /path/to/receptor.pdbqt \
  --ligand-index /path/to/ligand_index.txt \
  --center-x 32.79 --center-y 38.34 --center-z 58.49 \
  --size-x 28 --size-y 28 --size-z 28 \
  --search-mode <用户确认的模式> \
  --output-dir /path/to/results_docking
```

直接命令模板：

```bash
/path/to/UniDock-Pro/build/udp \
  --receptor /path/to/receptor.pdbqt \
  --ligand_index /path/to/ligand_index.txt \
  --center_x 32.79 --center_y 38.34 --center_z 58.49 \
  --size_x 28 --size_y 28 --size_z 28 \
  --search_mode <用户确认的模式> \
  --dir /path/to/results_docking
```

## 2. Similarity Searching

适用条件：

- 有 `reference_ligand`
- 没有 `receptor`

优先入口：

```bash
python3 scripts/run_unidock_case.py \
  --mode similarity \
  --reference-ligand /path/to/ref.pdbqt \
  --ligand-index /path/to/ligand_index.txt \
  --center-x 0 --center-y 0 --center-z 0 \
  --size-x 20 --size-y 20 --size-z 20 \
  --search-mode <用户确认的模式> \
  --output-dir /path/to/results_similarity
```

直接命令模板：

```bash
/path/to/UniDock-Pro/build/udp \
  --reference_ligand /path/to/ref.pdbqt \
  --ligand_index /path/to/ligand_index.txt \
  --center_x 0 --center_y 0 --center_z 0 \
  --size_x 20 --size_y 20 --size_z 20 \
  --search_mode <用户确认的模式> \
  --dir /path/to/results_similarity
```

## 3. Hybrid

适用条件：

- 同时有 `receptor`
- 同时有 `reference_ligand`

关键前提：

- `reference_ligand` 必须是与该受体对应的共晶姿态

优先入口：

```bash
python3 scripts/run_unidock_case.py \
  --mode hybrid \
  --receptor /path/to/receptor.pdbqt \
  --reference-ligand /path/to/xtal_ref.pdbqt \
  --ligand-index /path/to/ligand_index.txt \
  --center-x 32.79 --center-y 38.34 --center-z 58.49 \
  --size-x 28 --size-y 28 --size-z 28 \
  --search-mode <用户确认的模式> \
  --output-dir /path/to/results_hybrid
```

直接命令模板：

```bash
/path/to/UniDock-Pro/build/udp \
  --receptor /path/to/receptor.pdbqt \
  --reference_ligand /path/to/xtal_ref.pdbqt \
  --ligand_index /path/to/ligand_index.txt \
  --center_x 32.79 --center_y 38.34 --center_z 58.49 \
  --size_x 28 --size_y 28 --size_z 28 \
  --search_mode <用户确认的模式> \
  --dir /path/to/results_hybrid
```

## 配体目录与索引

如果用户给的是目录，优先先生成索引：

```bash
python3 scripts/make_ligand_index.py /path/to/ligands /path/to/ligand_index.txt
```

如果必须直接传目录，真实参数是：

```bash
--ligand_dir /path/to/ligands
```

不要用 `--ligand_directory`。

## 输出与分析

运行结束后重点检查：

- 输出目录中的 `*_out.pdbqt`
- 任务是否混用了多个不同筛选模式的结果
- 汇总 CSV 是否只对应这一次运行

推荐分析命令：

```bash
python3 scripts/analyze_unidock_results.py \
  /path/to/results \
  /path/to/docking_results.csv \
  --top-n 50
```

## 常见错误

- 忘记显式设置 `--search_mode`
- 误用 `--ligand_directory` 而不是 `--ligand_dir`
- similarity 任务误传 `receptor`
- hybrid 任务使用了不是共晶姿态的参考配体
- 把多个任务写进同一个输出目录，导致结果混杂
