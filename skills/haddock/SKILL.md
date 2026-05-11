---
name: haddock
description: HADDOCK 2.5 生物分子对接辅助工具 - 运行对接模拟、分析结果、管理约束文件、创建项目
license: Proprietary
---

# HADDOCK 2.5 Skill

## 概述

HADDOCK (High Ambiguity Driven biomolecular DOCKing) 是一个信息驱动的生物分子对接软件，用于预测蛋白质 - 蛋白质、蛋白质 - 核酸、蛋白质 - 小分子等复合物的三维结构。

### 用户环境

```bash
# HADDOCK 安装路径
HADDOCK_DIR=/path/to/haddock2.5

# 激活环境
conda activate haddock2.5
cd $HADDOCK_DIR
source haddock_configure.sh

# 运行对接
haddock2.5
```

### 系统配置

- **CPU**: 24 核
- **并行模式**: 批量并行 (batchmode=True)
- **任务批量**: it0=10, it1=5, water=5

---

## 快速开始

### 基本命令

```
/haddock run <example_name>     # 运行示例
/haddock status                 # 查看运行状态
/haddock analyze <run_dir>      # 分析结果
/haddock clean <run_dir>        # 清理结果
/haddock env                    # 检查环境
/haddock examples               # 列出所有示例
/haddock project new <name>     # 创建新项目
/haddock param set <key> <val>  # 修改参数
/haddock restrain create <type> # 创建约束文件
```

### 运行第一个对接

```bash
/haddock run protein-protein
```

这将：
1. 检查并激活 haddock2.5 环境
2. 进入 protein-protein 示例目录
3. 应用补丁并启动对接
4. 后台运行并显示日志

---

## 命令参考

### 1. `/haddock env` - 环境管理

**功能**: 检查、激活或显示 HADDOCK 环境状态

```bash
/haddock env                    # 完整检查并激活
/haddock env check              # 仅检查状态
/haddock env info               # 显示环境信息
```

**输出示例**:
```
[✓] Conda 环境：haddock2.5 已激活
[✓] HADDOCK 目录：/path/to/haddock2.5
[✓] CNS 可执行文件：存在
[✓] 配置文件：haddock_configure.sh 已加载
```

---

### 2. `/haddock examples` - 示例管理

**功能**: 列出、描述或运行内置示例

```bash
/haddock examples                    # 列出所有示例
/haddock examples detail <name>      # 显示示例详情
/haddock examples run <name>         # 运行指定示例
/haddock examples clean              # 清理所有示例结果
```

**可用示例列表**:

| 示例名称 | 对接类型 | 系统 | 数据源 |
|---------|---------|------|--------|
| protein-protein | 蛋白 - 蛋白 | E2A-HPR | CSP |
| protein-dna | 蛋白-DNA | 3CRO | 足迹 |
| protein-ligand | 蛋白 - 小分子 | 神经氨酸酶 | 结合位点 |
| protein-peptide | 蛋白 - 多肽 | 1NX1 | AIR |
| protein-peptide-ensemble | 集合平均 PRE | SUMO-DAXX | PRE |
| protein-protein-em | 冷冻电镜 | 核糖体 | EMDB 1884 |
| protein-protein-rdc | RDC 约束 | 双泛素 | RDC |
| protein-protein-pcs | PCS 约束 | EPS-Hot | PCS |
| protein-protein-dani | DANI 约束 | E2A-HPR | DANI |
| protein-trimer | 同源三聚体 | 1QU9 | WHISCY |
| protein-tetramer-CG | 粗粒化四聚体 | 3GD8 | C4 对称 |
| solvated-docking | 溶剂化对接 | Barnase-Barstar | WHISCY |
| protein-refine-pcs | PCS 优化 | - | PCS |
| refine-complex | 复合物优化 | - | - |
| protein-ligand-shape | 形状约束 | BACE_1 | 模板 |

---

### 3. `/haddock run` - 运行对接

**功能**: 启动 HADDOCK 对接运行

```bash
/haddock run <example_name>         # 运行内置示例
/haddock run --project <name>       # 运行自定义项目
/haddock run --dir <path>           # 运行指定目录
/haddock run --dry                  # 预演（不实际运行）
```

**运行流程**:
1. 环境检查
2. 进入目录
3. 应用补丁（如需要）
4. 启动 haddock2.5
5. 显示实时日志

**确认提示**:
```
即将运行：protein-protein 示例
预计时间：4-12 小时
模型数量：it0=1000, it1=200, water=200
是否继续？[y/N]
```

---

### 4. `/haddock status` - 查看状态

**功能**: 监控运行进度和状态

```bash
/haddock status                 # 当前运行状态
/haddock status <run_dir>       # 指定目录状态
/haddock status --watch         # 实时监控
/haddock status --tail          # 显示日志尾部
```

**输出示例**:
```
运行目录：run1
当前阶段：water (3/3)
进度：156/200 模型 (78%)
已用时间：3h 24m
预计剩余：45m
当前能量：Evdw=-42.3, Eelec=-298.1, EAIR=-18.5
```

---

### 5. `/haddock analyze` - 结果分析

**功能**: 分析对接结果，生成统计报告

```bash
/haddock analyze                        # 分析当前 run1
/haddock analyze <run_dir>              # 分析指定目录
/haddock analyze --full                 # 完整分析（包括 RMSD）
/haddock analyze --cluster              # 仅聚类分析
/haddock analyze --energy               # 仅能量分析
/haddock analyze --report               # 生成报告文件
```

**分析内容**:
- 聚类统计（簇大小、排名）
- RMSD 分析（i-RMSD, l-RMSD）
- 能量项统计（VdW, 静电，去溶剂化，AIR）
- HADDOCK 评分排序

**输出示例**:
```
=== 聚类统计 ===
簇 1: 89 模型 (44.5%) - HADDOCK 评分：-92.3 ± 11.2
簇 2: 45 模型 (22.5%) - HADDOCK 评分：-85.1 ± 9.8
簇 3: 33 模型 (16.5%) - HADDOCK 评分：-78.4 ± 12.1

=== 最佳模型 ===
结构 1: cluster_1/model_1.pdb
  HADDOCK 评分：-105.2
  VdW: -48.3 | 静电：-312.5 | AIR: -24.1
  i-RMSD: 1.2Å | l-RMSD: 2.1Å
```

---

### 6. `/haddock clean` - 清理结果

**功能**: 删除运行生成的文件和目录

```bash
/haddock clean                    # 清理当前 run1
/haddock clean <run_dir>          # 清理指定目录
/haddock clean --all              # 清理所有 run* 目录
/haddock clean --dry              # 预演（显示将删除的内容）
```

**确认提示**:
```
将删除:
- run1/structures/ (约 2.5GB)
- run1/analysis/ (约 150MB)
- run1/haddock.out

保留:
- run1/run.cns
- run1/run.param

是否继续？[y/N]
```

---

### 7. `/haddock project` - 项目管理

**功能**: 创建、配置和管理自定义对接项目

```bash
/haddock project new <name>           # 创建新项目
/haddock project list                 # 列出所有项目
/haddock project info <name>          # 显示项目信息
/haddock project delete <name>        # 删除项目
```

**创建项目流程**:
```bash
/haddock project new my_complex
```

1. 创建目录结构：
   ```
   ~/haddock_projects/my_complex/
   ├── pdb/           # PDB 文件
   ├── restraints/    # 约束文件
   ├── run/           # 运行目录
   └── analysis/      # 分析结果
   ```

2. 生成模板文件：
   - `run.param.template`
   - `air.tbl.template`

3. 准备 PDB 文件（可选）:
   - 移除水分子
   - 添加氢原子
   - 修复缺失残基

---

### 8. `/haddock param` - 参数调整

**功能**: 修改 HADDOCK 运行参数

```bash
/haddock param list                 # 列出所有参数
/haddock param show <key>           # 显示参数详情
/haddock param set <key> <value>    # 设置参数
/haddock param reset                # 恢复默认值
```

**常用参数**:

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `init_struc` | 1000 | it0 刚体模型数 |
| `it0_struc` | 200 | it1 半柔性模型数 |
| `water_struc` | 200 | water 优化模型数 |
| `clust_struc` | 4 | 聚类大小 |
| `iniseed` | 917 | 随机种子 |
| `em_kscale` | 15000 | EM 约束力常数 |
| `amb_cool1` | 10.0 | AIR 约束能量常数 |

**示例**:
```bash
/haddock param set init_struc 500     # 减少采样加速
/haddock param set iniseed 1234       # 改变随机种子
/haddock param set water_struc 0      # 跳过 water 阶段
```

---

### 9. `/haddock restrain` - 约束文件管理

**功能**: 创建和编辑约束文件

```bash
/haddock restrain create air          # 创建 AIR 约束
/haddock restrain create rdc          # 创建 RDC 约束
/haddock restrain create pcs          # 创建 PCS 约束
/haddock restrain create dani         # 创建 DANI 约束
/haddock restrain edit <file>         # 编辑约束文件
/haddock restrain validate <file>     # 验证约束格式
```

**AIR 约束模板**:
```
! 活性残基 (结合界面)
assign (resid 45 and segid A) (resid 100 and segid B) 2.0 2.0 0.0

! 被动残基 (表面活性)
assign (resid 46 and segid A) (resid 101 and segid B) 2.0 2.0 0.0
```

---

## 三阶段对接流程

### it0 - 刚体对接

```
目的：全局搜索所有可能的结合模式
模型数：1000
时间：~2-4 小时
输出：run1/structures/it0/
```

### it1 - 半柔性优化

```
目的：允许界面侧链柔性，诱导契合
模型数：200（从 it0 选择）
时间：~4-8 小时
输出：run1/structures/it1/
```

### water - 水优化

```
目的：显式溶剂中精确优化，水桥稳定
模型数：200（从 it1 选择）
时间：~8-16 小时
输出：run1/structures/water/
```

---

## 运行自定义对接项目

### 步骤 1: 创建项目

```bash
/haddock project new my docking
```

### 步骤 2: 准备 PDB 文件

```bash
# 将 PDB 文件复制到项目目录
cp /path/to/protein_A.pdb ~/haddock_projects/my_docking/pdb/
cp /path/to/protein_B.pdb ~/haddock_projects/my_docking/pdb/
```

### 步骤 3: 生成参数文件

```bash
/haddock param generate --project my_docking
```

### 步骤 4: 定义约束（可选）

```bash
/haddock restrain create air --project my_docking
```

### 步骤 5: 运行对接

```bash
/haddock run --project my_docking
```

---

## 故障排除

### 常见问题

#### 1. `haddock2.5: command not found`

**解决**:
```bash
conda activate haddock2.5
source haddock_configure.sh
```

#### 2. CNS 执行错误

**检查**:
```bash
ls -la $HADDOCK_DIR/cns1.3/cns.*
```

**修复**:
```bash
chmod +x $HADDOCK_DIR/cns1.3/cns.*
```

#### 3. 内存不足

**解决**: 减少采样数
```bash
/haddock param set init_struc 500
/haddock param set it0_struc 100
```

#### 4. 运行太慢

**解决**:
- 检查并行配置
- 减少 water 阶段模型数
- 考虑跳过 water 阶段

#### 5. Patch 应用失败

**手动应用**:
```bash
cd run1
patch -p0 -i ../run.cns.patch
```

---

## 结果解读

### HADDOCK 评分

```
HADDOCK 评分 = w_vdw*E_vdw + w_elec*E_elec + w_desolv*E_desolv + w_AIR*E_AIR

常见 water 阶段权重:
- w_vdw = 1.0
- w_elec = 0.2
- w_desolv = 1.0
- w_AIR = 0.1 或 1.0（以 run.cns 为准）
```

实际分析时，**必须以当前 run 的 `run.cns` 权重为准**，不要机械套用默认值。

### 当前版本推荐分析流程（蛋白-核酸）

当前版本建议把 HADDOCK 分析拆成两层：

1. **官方脚本基线**
   - `ana_structures.csh`
   - `ana_clusters.csh`
   - `ana_clusters.csh -best 4`
   - `ana_clusters.csh -best 10` 作为可选扩展
2. **扩展分析**
   - `contact frequency`
   - `contact map`
   - `score-vs-FCC`
   - `score-vs-interface-RMSD`
   - `score_boxplots`
   - `energy_boxplots`
   - `MD shortlist`
   - `cluster-grouped PDB export`

### 为什么默认保留 `full + best4`

- `full-cluster average` 是官方 cluster 统计的基本口径，必须保留
- `best4` 用来检验“大簇是否被尾部较差模型拖分”，默认建议保留
- `best10` 是稳健性扩展项，不是每次都必须跑

一个容易混淆的点是：

- `bar/error bar/boxplot` 只能改变 **full-cluster 数据的展示方式**
- `best4` 改变的是 **cluster 代表分数的统计口径**

所以，`bar/boxplot` **不能替代** `best4`。

### 当前版本图层级建议

**正文优先**

- `cluster/contact map`
- `aptamer_contact_frequency`
- `score-vs-FCC`
- `score-vs-interface-RMSD`
- `score_boxplots`

**补充材料优先**

- `cluster_convergence`
- `protein_contact_frequency`
- `energy_boxplots`

### 图的解释口径

#### 1. `score-vs-FCC`

- 用于看主要 cluster family 的分离程度
- 主文默认展示 **top 5 clusters**
- 如需更紧凑的稿件版，可再收缩到 **top 3 clusters**
- 其余模型统一归为 `Other`
- 这类图是 **contact-based similarity diagnostic**
- 它**不等同于** canonical HADDOCK `score-vs-RMSD`

#### 2. `score-vs-interface-RMSD`

- 默认相对 **major population cluster representative** 计算
- 用于看各模型相对主解的界面几何偏离
- 主文默认也展示 **top 5 clusters**
- 如需更紧凑的稿件版，可再收缩到 **top 3 clusters**
- 若没有实验参考复合物，这张图比 `score-vs-RMSD to native` 更现实

#### 3. `score_boxplots`

- 可以进入正文
- 作用是展示**各体系内部**主要 cluster 的 HADDOCK score 分布与离散度
- **不能**用来支持不同体系间绝对 HADDOCK score 的直接横比
- 主文默认与 `score-vs-FCC` / `score-vs-interface-RMSD` 保持一致，也展示 **top 5 clusters**

#### 4. `energy_boxplots`

- 用于拆解 `Evdw / Eelec / Eair / Edesolv`
- 更适合作为补充图，而不是主结论图

### Contact 的默认定义

当前版本 contact 统计默认定义为：

- 蛋白链 `A` 与核酸链 `B`
- 任意蛋白-核酸**重原子**距离 `<= 4.0 Å`
- 默认基于 `water` 阶段**最低分 top 20 模型**计算接触频率与 contact map

这一定义适合做界面总览；若要区分主簇与替代簇，建议额外画 **cluster-specific contact map**。

### 跨体系比较的底线

对于不同长度、不同约束规模的体系（例如全长 aptamer vs 截短 aptamer），默认遵循：

- 同一 run / 同一 stage 内，不同 cluster 的 HADDOCK score 可以比较
- 不同体系间的**绝对** HADDOCK score 默认**不可直接横比**

跨体系更应优先比较：

- cluster 收敛性
- AIR 违约
- BSA
- 蛋白接触区域
- 核酸接触区域
- binding mode 是否一致

### 按 cluster 分组导出 PDB

当前版本的标准交付里，建议把 `water` 最终结构按 cluster 复制导出，便于人工看结构、挑 MD 候选和做 PyMOL。

默认目录组织：

```text
analysis_exports/
├── clusters/
│   └── water/
│       ├── cluster_C1/
│       ├── cluster_C2/
│       └── cluster_manifest.csv
└── md_shortlist/
    ├── <system>_C1_modelXX_*.pdb
    └── md_shortlist_manifest.csv
```

默认规则：

- 每个 `cluster_Cn/` 目录复制该簇全部 `water` PDB 副本
- 文件名保留原始模型编号
- `cluster_manifest.csv` 至少包含：
  - `stage`
  - `cluster`
  - `model_id`
  - `score`
  - `pdb_filename`
  - `source_path`
  - `is_representative`
- 代表模型默认取该 cluster 的最低分模型
- `md_shortlist/` 默认再复制每个体系的 2 个 MD 候选代表结构

### Worked Example：RPN10 / `#54` vs `#54(T)`

当前版本的 worked example 固定如下：

- `#54` = full-length aptamer, 76 nt
- `#54(T)` = truncated aptamer, 36 nt
- `#54(T) 1-36 -> #54 21-56`
- 蛋白主界面窗口：`116-135`

推荐默认结论框架：

- `#54(T)`：`C1` 为 major population，`C8` 为 alternative family
- `#54`：`C1` 为主簇，`C4` 用于检验末端参与
- 后续 MD 默认每个体系保留 2 个候选：
  - 1 个主人口簇候选
  - 1 个机制上不同的替代候选

### 质量标准

| 等级 | i-RMSD | l-RMSD | 说明 |
|------|--------|--------|------|
| 高精度 | <1Å | <2Å | 接近晶体结构 |
| 中等 | 1-2Å | 2-5Å | 可接受的预测 |
| 低精度 | >2Å | >5Å | 需要优化 |

---

## 高级功能

### 对称性约束

```cns
! C2 对称
c2sym_distance = 0.0
c2sym_angle = 180.0
```

### 多体对接

```bash
# 在 run.param 中设置
N_COMP=3  # 三体
N_COMP=4  # 四体（最多支持 20）
```

### 粗粒化模式

```bash
# 使用 Martini CG 表示
python $HADDOCK_DIR/cg_tools/aa2cg.py input.pdb > output_CG.pdb
```

---

## 参考文献

1. Dominguez C, et al. JACS 125, 1731-1737 (2003)
2. de Vries SJ, et al. Proteins 69, 726-733 (2007)
3. van Dijk ADJ, et al. NAR 34, 3317-3325 (2006)

## 资源链接

- **官方网站**: https://wenmr.science.uu.nl/haddock2.4
- **用户手册**: https://bonvinlab.org/software/haddock2.4
- **论坛**: https://ask.bioexcel.eu

---

*HADDOCK 2.5 Skill - 最后更新：2026-04-10*
