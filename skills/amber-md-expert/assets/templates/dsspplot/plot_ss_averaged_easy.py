#!/usr/bin/env python3
"""
蛋白质二级结构分析可视化脚本（Nature期刊标准版本）
生成：图1堆叠图、图2热图、图3多子图、图5统计图
特点：更大字号、无网格线、300 DPI
"""

import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Patch

# ========== Nature期刊标准配置（增大字号，300 DPI）==========
plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size': 10,
    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'axes.linewidth': 1.0,
    'xtick.major.width': 1.0,
    'ytick.major.width': 1.0,
    'lines.linewidth': 1.5,
    'patch.linewidth': 1.0,
    'figure.dpi': 300,           # 改为300 DPI
    'savefig.dpi': 300,          # 改为300 DPI
    'savefig.format': 'tiff',
    'savefig.bbox': 'tight',
    'pdf.fonttype': 42,
    'ps.fonttype': 42,
})

# Nature色盲友好配色
NATURE_COLORS = {
    'beta_sheet': '#E69F00',    # 橙色
    'helix': '#0072B2',         # 蓝色
    'turn': '#009E73',          # 绿色
    'bend': '#CC79A7',          # 紫色
    'coil': '#999999',          # 灰色
}

# ========== 残基编号配置 ==========
NUMBERING_CONFIG = {
    'mode': 'custom',
    'start': 306,
    'step': 1,
    'chain_id': 'A',
    'offset': 0,
}

# ========== 读取数据 ==========
print("正在读取 ss_summary.dat...")
data = np.loadtxt('ss_summary.dat', comments='#')

total_residues = len(data)
chain_length = total_residues // 2

print(f"检测到总残基数: {total_residues}")
print(f"单链长度: {chain_length}")

# 分割并平均两条链
chain1_data = data[:chain_length, 1:]
chain2_data = data[chain_length:chain_length*2, 1:]
averaged_ss = (chain1_data + chain2_data) / 2.0

# ========== 生成残基编号 ==========
mode = NUMBERING_CONFIG['mode']

if mode == 'default':
    residues = np.arange(1, chain_length + 1)
    residue_labels = [str(int(r)) for r in residues]
    print(f"编号模式: 默认 (1-{chain_length})")
elif mode == 'custom':
    start = NUMBERING_CONFIG['start']
    step = NUMBERING_CONFIG['step']
    residues = np.arange(start, start + chain_length * step, step)
    residue_labels = [str(int(r)) for r in residues]
    print(f"编号模式: 自定义 ({residues[0]}-{residues[-1]}, 步长={step})")
elif mode == 'offset':
    offset = NUMBERING_CONFIG['offset']
    residues = data[:chain_length, 0].astype(int) + offset
    residue_labels = [str(int(r)) for r in residues]
    print(f"编号模式: 原始编号 + 偏移量({offset})")
elif mode == 'chain':
    chain_id = NUMBERING_CONFIG['chain_id']
    residues = np.arange(1, chain_length + 1)
    residue_labels = [f'{chain_id}{i}' for i in residues]
    print(f"编号模式: 链标识 ({chain_id}1-{chain_id}{chain_length})")
elif mode == 'original':
    residues = data[:chain_length, 0]
    residue_labels = [str(int(r)) for r in residues]
    print(f"编号模式: 原始文件编号")

# ========== 合并二级结构 ==========
extended = averaged_ss[:, 0]
bridge = averaged_ss[:, 1]
helix_310 = averaged_ss[:, 2]
alpha = averaged_ss[:, 3]
pi = averaged_ss[:, 4]
turn = averaged_ss[:, 5]
bend = averaged_ss[:, 6]

# 合并
beta_sheet = extended + bridge
helix = helix_310 + alpha + pi
coil = 1.0 - (beta_sheet + helix + turn + bend)
coil = np.maximum(coil, 0)

ss_labels = ['β-sheet', 'Helix', 'Turn', 'Bend', 'Coil']
colors = [NATURE_COLORS['beta_sheet'], NATURE_COLORS['helix'], 
          NATURE_COLORS['turn'], NATURE_COLORS['bend'], NATURE_COLORS['coil']]
structures = [beta_sheet, helix, turn, bend, coil]

# 验证
total_check = beta_sheet + helix + turn + bend + coil
print(f"\n数据验证: 总和范围 = [{total_check.min():.6f}, {total_check.max():.6f}]")
if np.allclose(total_check, 1.0, atol=1e-5):
    print("✓ 验证通过: 每个残基所有二级结构之和 = 1")

# ========== 图1：堆叠面积图 ==========
print("\n正在生成图1：堆叠面积图...")
fig = plt.figure(figsize=(7.2, 3.5))

if mode == 'chain':
    x_pos = np.arange(len(residues))
    plt.stackplot(x_pos, beta_sheet, helix, turn, bend, coil,
                  labels=ss_labels, colors=colors, alpha=0.9)
    plt.xlim(0, len(residues)-1)
    plt.xticks(x_pos[::5], [residue_labels[i] for i in range(0, len(residue_labels), 5)])
else:
    plt.stackplot(residues, beta_sheet, helix, turn, bend, coil,
                  labels=ss_labels, colors=colors, alpha=0.9)
    plt.xlim(residues[0], residues[-1])

plt.xlabel('Residue number', fontsize=12)
plt.ylabel('Probability', fontsize=12)
plt.legend(loc='upper right', fontsize=10, frameon=True, edgecolor='black', 
           fancybox=False, framealpha=1)
plt.ylim(0, 1)

ax = plt.gca()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout(pad=0.3)
plt.savefig('Fig1_ss_stackplot.tiff', dpi=300, bbox_inches='tight')
plt.savefig('Fig1_ss_stackplot.pdf', dpi=300, bbox_inches='tight')
print("✓ 已保存: Fig1_ss_stackplot.tiff & .pdf")
plt.close()

# ========== 图2：热图 ==========
print("正在生成图2：热图...")
ss_matrix_merged = np.vstack([beta_sheet, helix, turn, bend, coil])

fig = plt.figure(figsize=(7.2, 2.8))
ax = sns.heatmap(ss_matrix_merged, 
                 cmap='YlOrRd',
                 cbar_kws={'label': 'Probability', 'shrink': 0.8},
                 yticklabels=ss_labels,
                 xticklabels=[residue_labels[i] if i % 5 == 0 else '' 
                             for i in range(len(residue_labels))],
                 vmin=0, vmax=1, 
                 linewidths=0,
                 square=False)

# 调整colorbar字号
cbar = ax.collections[0].colorbar
cbar.ax.tick_params(labelsize=10, width=1.0)
cbar.outline.set_linewidth(1.0)
cbar.set_label('Probability', fontsize=12)

plt.xlabel('Residue number', fontsize=12)
plt.ylabel('Secondary structure', fontsize=12)
plt.xticks(fontsize=10)
plt.yticks(rotation=0, fontsize=10)
plt.tight_layout(pad=0.3)
plt.savefig('Fig2_ss_heatmap.tiff', dpi=300, bbox_inches='tight')
plt.savefig('Fig2_ss_heatmap.pdf', dpi=300, bbox_inches='tight')
print("✓ 已保存: Fig2_ss_heatmap.tiff & .pdf")
plt.close()

# ========== 图3：多子图折线图 ==========
print("正在生成图3：多子图折线图...")
fig, axes = plt.subplots(5, 1, figsize=(7.2, 7), sharex=True)

if mode == 'chain':
    x_pos = np.arange(len(residues))
    x_data = x_pos
else:
    x_data = residues

for i, (ax, struct, label, color) in enumerate(zip(axes, structures, ss_labels, colors)):
    # 填充区域
    ax.fill_between(x_data, 0, struct, color=color, alpha=0.7, linewidth=0)
    # 绘制线条
    ax.plot(x_data, struct, color=color, linewidth=1.5)
    
    # Y轴标签
    ax.set_ylabel(label, fontsize=11, fontweight='bold')
    ax.set_ylim(0, 1)
    
    # 移除顶部和右侧边框
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    # 设置X轴范围
    if mode == 'chain':
        ax.set_xlim(0, len(residues)-1)
    else:
        ax.set_xlim(residues[0], residues[-1])
    
    # 标注最大值（红色星号）
    if np.max(struct) > 0.4:
        max_idx = np.argmax(struct)
        ax.plot(x_data[max_idx], struct[max_idx], 
               'r*', markersize=8, markeredgecolor='black', markeredgewidth=0.5)

# 最底部子图的X轴标签
axes[-1].set_xlabel('Residue number', fontsize=12)

if mode == 'chain':
    axes[-1].set_xticks(x_pos[::5])
    axes[-1].set_xticklabels([residue_labels[i] for i in range(0, len(residue_labels), 5)])

plt.tight_layout(pad=0.3, h_pad=0.5)
plt.savefig('Fig3_ss_profiles.tiff', dpi=300, bbox_inches='tight')
plt.savefig('Fig3_ss_profiles.pdf', dpi=300, bbox_inches='tight')
print("✓ 已保存: Fig3_ss_profiles.tiff & .pdf")
plt.close()

# ========== 图5：统计柱状图（纵坐标0-50%，百分比格式）==========
from matplotlib.ticker import PercentFormatter

print("正在生成图5：统计柱状图...")
ss_matrix_for_class = np.column_stack([beta_sheet, helix, turn, bend, coil])
ss_avg = np.mean(ss_matrix_for_class, axis=0)

fig = plt.figure(figsize=(4.5, 4))
bars = plt.bar(range(len(ss_labels)), ss_avg, color=colors, alpha=0.9,
               edgecolor='black', linewidth=1.0, width=0.7)
plt.xticks(range(len(ss_labels)), ss_labels, rotation=45, ha='right', fontsize=10)
plt.xlabel('Secondary structure type', fontsize=12)
plt.ylabel('Average probability', fontsize=12)

# 固定纵坐标为0-0.5并显示为百分比
plt.ylim(0, 0.5)

ax = plt.gca()
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)


# 添加数值标签
for i, bar in enumerate(bars):
    height = bar.get_height()
    color = 'red' if height > 0.5 else 'black'
    plt.text(bar.get_x() + bar.get_width()/2., min(height, 0.48),
            f'{height:.2f}', ha='center', va='bottom', 
            fontsize=9, fontweight='bold', color=color)

plt.tight_layout(pad=0.3)
plt.savefig('Fig5_ss_composition.tiff', dpi=300, bbox_inches='tight')
plt.savefig('Fig5_ss_composition.pdf', dpi=300, bbox_inches='tight')
print("✓ 已保存: Fig5_ss_composition.tiff & .pdf")
plt.close()

# ========== 数据摘要 ==========
print("\n" + "="*60)
print("Nature标准图表生成完毕")
print("="*60)
print("文件规格:")
print("  - 格式: TIFF (主) + PDF (备)")
print("  - 分辨率: 300 DPI")
print("  - 字体: Arial (10-12 pt)")
print("  - 配色: Nature色盲友好方案")
print("  - 网格: 无")
print("\n生成的文件:")
print("  1. Fig1_ss_stackplot.tiff/.pdf  - 堆叠面积图")
print("  2. Fig2_ss_heatmap.tiff/.pdf    - 热图")
print("  3. Fig3_ss_profiles.tiff/.pdf   - 多子图折线图 ★新增★")
print("  4. Fig5_ss_composition.tiff/.pdf - 统计柱状图")
print("\n各结构平均占比:")
for label, avg in zip(ss_labels, ss_avg):
    print(f"  {label:12s}: {avg:.3f} ({avg*100:.1f}%)")

# 识别主要结构区域
print(f"\n主要结构区域识别 (概率 > 0.4):")
for i, (label, struct) in enumerate(zip(ss_labels, structures)):
    high_prob_indices = np.where(struct > 0.4)[0]
    if len(high_prob_indices) > 0:
        # 连续区域识别
        regions = []
        start = high_prob_indices[0]
        for j in range(1, len(high_prob_indices)):
            if high_prob_indices[j] != high_prob_indices[j-1] + 1:
                regions.append((start, high_prob_indices[j-1]))
                start = high_prob_indices[j]
        regions.append((start, high_prob_indices[-1]))
        
        region_str = ', '.join([f'{residue_labels[r[0]]}-{residue_labels[r[1]]}' 
                                for r in regions])
        print(f"  {label:12s}: {region_str}")

print("="*60)
