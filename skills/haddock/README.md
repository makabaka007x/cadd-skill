# HADDOCK Skill 快速参考

## 命令速查

| 命令 | 功能 | 示例 |
|------|------|------|
| `/haddock env` | 环境检查 | `/haddock env` |
| `/haddock examples` | 列出示例 | `/haddock examples` |
| `/haddock run` | 运行对接 | `/haddock run protein-protein` |
| `/haddock status` | 查看状态 | `/haddock status` |
| `/haddock analyze` | 分析结果 | `/haddock analyze run1` |
| `/haddock clean` | 清理结果 | `/haddock clean run1` |
| `/haddock project` | 项目管理 | `/haddock project new my_docking` |
| `/haddock param` | 参数调整 | `/haddock param set init_struc 500` |
| `/haddock restrain` | 约束文件 | `/haddock restrain create air` |

## 环境激活

```bash
conda activate haddock2.5
cd /path/to/haddock2.5
source haddock_configure.sh
```

## 示例目录

```
/path/to/haddock2.5/examples/
├── protein-protein          # 蛋白 - 蛋白 (E2A-HPR)
├── protein-dna              # 蛋白-DNA (3CRO)
├── protein-ligand           # 蛋白 - 小分子
├── protein-peptide          # 蛋白 - 多肽
├── protein-protein-em       # 冷冻电镜
├── protein-protein-rdc      # RDC 约束
└── ...
```

## 运行流程

```
it0 (刚体) → it1 (半柔性) → water (水优化)
  1000 模型     200 模型        200 模型
  ~2-4 小时     ~4-8 小时      ~8-16 小时
```

## 结果位置

```
run1/
├── structures/
│   ├── it0/          # 刚体模型
│   ├── it1/          # 半柔性模型
│   └── water/        # 最终模型
│       └── cluster_1/  # 最佳簇
└── haddock.out       # 运行日志
```

## 辅助脚本

```bash
# 使用辅助脚本
~/.claude/skills/haddock/scripts/haddock.sh <command>

# 示例
./haddock.sh env              # 检查环境
./haddock.sh examples         # 列出示例
./haddock.sh run protein-protein  # 运行
./haddock.sh status run1      # 状态
```
