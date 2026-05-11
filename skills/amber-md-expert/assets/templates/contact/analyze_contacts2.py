import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

def parse_contacts_file(filename):
    """解析contacts.tsv文件"""
    frames = []
    interaction_types = []
    atom1_list = []
    atom2_list = []
    
    with open(filename, 'r') as f:
        for line in f:
            # 跳过注释行
            if line.startswith('#'):
                continue
            
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                frames.append(int(parts[0]))
                interaction_types.append(parts[1])
                atom1_list.append(parts[2])
                atom2_list.append(parts[3] if len(parts) > 3 else '')
    
    df = pd.DataFrame({
        'frame': frames,
        'interaction_type': interaction_types,
        'atom_1': atom1_list,
        'atom_2': atom2_list
    })
    
    return df

def categorize_interactions(df, merge_hbond=False):
    """
    将相互作用分类
    merge_hbond: 是否合并氢键类型
    """
    df = df.copy()
    
    # 创建interaction_category列
    df['interaction_category'] = df['interaction_type'].copy()
    
    # 合并π-stacking (ps) 和 T-stacking (ts) 为 pi-pi
    df.loc[df['interaction_type'].isin(['ps', 'ts']), 'interaction_category'] = 'pi-pi'
    
    # 如果需要，合并氢键类型
    if merge_hbond:
        df.loc[df['interaction_type'].isin(['hbbb', 'hbsb', 'hbss', 'hb']), 'interaction_category'] = 'hbound'
    
    return df

def get_interaction_name(short_name, detailed=False):
    """获取相互作用的全称"""
    if detailed:
        name_mapping = {
            'hb': 'Hydrogen Bond',
            'hbbb': 'HBond BB-BB',
            'hbsb': 'HBond SC-BB',
            'hbss': 'HBond SC-SC',
            'hbound': 'Hydrogen Bond (All)',
            'sb': 'Salt Bridge',
            'pc': 'Pi-Cation',
            'pi-pi': 'Pi-Pi Interaction',
            'vdw': 'Van der Waals',
            'hp': 'Hydrophobic',
            'hc': 'Hydrophobic',
            'wb': 'Water Bridge',
            'wb2': 'Extended Water Bridge'
        }
    else:
        name_mapping = {
            'hb': 'Hydrogen Bond',
            'hbbb': 'HBond BB-BB',
            'hbsb': 'HBond SC-BB',
            'hbss': 'HBond SC-SC',
            'hbound': 'Hydrogen Bond',
            'sb': 'Salt Bridge',
            'pc': 'Pi-Cation',
            'pi-pi': 'Pi-Pi Interaction',
            'vdw': 'Van der Waals',
            'hp': 'Hydrophobic',
            'hc': 'Hydrophobic',
            'wb': 'Water Bridge',
            'wb2': 'Extended Water Bridge'
        }
    return name_mapping.get(short_name, short_name.upper())

def count_interactions_per_frame(df):
    """统计每帧中各类相互作用的数量"""
    # 获取所有帧
    all_frames = range(df['frame'].min(), df['frame'].max() + 1)
    
    # 按frame和interaction_category分组计数
    interaction_counts = df.groupby(['frame', 'interaction_category']).size().reset_index(name='count')
    
    # 透视表
    pivot_table = interaction_counts.pivot(index='frame', columns='interaction_category', values='count')
    
    # 重新索引以包含所有帧（即使某帧没有某类相互作用）
    pivot_table = pivot_table.reindex(all_frames, fill_value=0)
    
    # 确保所有值都是整数，没有NaN
    pivot_table = pivot_table.fillna(0).astype(int)
    
    return pivot_table

def save_total_contact_number(df, output_file='total_contact_number.dat'):
    """保存每帧的总接触数（所有相互作用求和）"""
    # 获取所有帧范围
    all_frames = range(df['frame'].min(), df['frame'].max() + 1)
    
    # 统计每帧的总接触数
    total_counts = df.groupby('frame').size().reset_index(name='total_contacts')
    
    # 创建完整的帧范围DataFrame
    full_df = pd.DataFrame({'frame': list(all_frames)})
    full_df = full_df.merge(total_counts, on='frame', how='left')
    full_df['total_contacts'] = full_df['total_contacts'].fillna(0).astype(int)
    
    # 计算统计信息
    mean_contacts = full_df['total_contacts'].mean()
    std_contacts = full_df['total_contacts'].std()
    min_contacts = full_df['total_contacts'].min()
    max_contacts = full_df['total_contacts'].max()
    median_contacts = full_df['total_contacts'].median()
    
    # 写入.dat文件
    with open(output_file, 'w') as f:
        f.write(f"# Total Contact Number per frame (All interactions summed)\n")
        f.write(f"# Total frames: {len(full_df)}\n")
        f.write(f"# Statistics:\n")
        f.write(f"#   Mean:   {mean_contacts:.2f}\n")
        f.write(f"#   Std:    {std_contacts:.2f}\n")
        f.write(f"#   Min:    {min_contacts}\n")
        f.write(f"#   Max:    {max_contacts}\n")
        f.write(f"#   Median: {median_contacts:.2f}\n")
        f.write(f"# Columns: frame total_contacts\n")
        f.write("#" + "-" * 50 + "\n")
        for _, row in full_df.iterrows():
            f.write(f"{row['frame']:6d} {row['total_contacts']:6d}\n")
    
    print(f"\n已保存总接触数数据: {output_file}")
    print(f"  平均接触数: {mean_contacts:.2f} ± {std_contacts:.2f}")
    print(f"  范围: {min_contacts} - {max_contacts}")
    
    return full_df

def plot_total_contacts(df, output_file='total_contacts_over_time.png'):
    """绘制总接触数随时间变化的图"""
    # 获取所有帧范围
    all_frames = range(df['frame'].min(), df['frame'].max() + 1)
    
    # 统计每帧的总接触数
    total_counts = df.groupby('frame').size().reset_index(name='total_contacts')
    
    # 创建完整的帧范围DataFrame
    full_df = pd.DataFrame({'frame': list(all_frames)})
    full_df = full_df.merge(total_counts, on='frame', how='left')
    full_df['total_contacts'] = full_df['total_contacts'].fillna(0).astype(int)
    
    # 绘图
    plt.figure(figsize=(12, 6))
    plt.plot(full_df['frame'], full_df['total_contacts'], 
             linewidth=1.5, alpha=0.7, color='#2E86AB')
    
    # 添加移动平均线
    window = 100  # 100帧移动平均
    if len(full_df) >= window:
        moving_avg = full_df['total_contacts'].rolling(window=window, center=True).mean()
        plt.plot(full_df['frame'], moving_avg, 
                linewidth=2, alpha=0.9, color='#A23B72', 
                label=f'{window}-frame Moving Average')
    
    # 添加平均值水平线
    mean_val = full_df['total_contacts'].mean()
    plt.axhline(y=mean_val, color='#F18F01', linestyle='--', 
                linewidth=2, alpha=0.8, label=f'Mean = {mean_val:.1f}')
    
    plt.xlabel('Frame', fontsize=12, fontweight='bold')
    plt.ylabel('Total Contact Number', fontsize=12, fontweight='bold')
    plt.title('Total Contact Number Over Time', fontsize=14, fontweight='bold')
    plt.legend(fontsize=10)
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"已保存总接触数图表: {output_file}")

def save_individual_interactions(df, output_dir='interaction_data_separate'):
    """保存每种相互作用类型的详细数据为.dat文件"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有帧范围
    all_frames = range(df['frame'].min(), df['frame'].max() + 1)
    
    results = {}
    
    for interaction_type in sorted(df['interaction_category'].unique()):
        # 筛选特定类型的相互作用
        subset = df[df['interaction_category'] == interaction_type].copy()
        
        # 统计每帧的数量
        counts_per_frame = subset.groupby('frame').size().reset_index(name='count')
        
        # 创建完整的帧范围DataFrame
        full_df = pd.DataFrame({'frame': list(all_frames)})
        full_df = full_df.merge(counts_per_frame, on='frame', how='left')
        full_df['count'] = full_df['count'].fillna(0).astype(int)
        
        # 保存为.dat文件
        friendly_name = get_interaction_name(interaction_type).replace(' ', '_').replace('-', '_').lower()
        friendly_name = friendly_name.replace('(', '').replace(')', '')
        output_file = f'{output_dir}/{friendly_name}_per_frame.dat'
        
        # 写入.dat文件，包含注释头
        with open(output_file, 'w') as f:
            f.write(f"# {get_interaction_name(interaction_type, detailed=True)} per frame\n")
            f.write(f"# Total frames: {len(full_df)}\n")
            f.write(f"# Columns: frame count\n")
            for _, row in full_df.iterrows():
                f.write(f"{row['frame']:6d} {row['count']:6d}\n")
        
        results[interaction_type] = full_df
        
        print(f"已保存 {get_interaction_name(interaction_type, detailed=True)}: {output_file}")
    
    return results

def save_hbound_merged(df, output_file='hydrogen_bond_per_frame_merged.dat'):
    """保存合并后的氢键数据"""
    # 获取所有帧范围
    all_frames = range(df['frame'].min(), df['frame'].max() + 1)
    
    # 筛选氢键相互作用
    hbound_subset = df[df['interaction_category'] == 'hbound'].copy()
    
    # 统计每帧的数量
    counts_per_frame = hbound_subset.groupby('frame').size().reset_index(name='count')
    
    # 创建完整的帧范围DataFrame
    full_df = pd.DataFrame({'frame': list(all_frames)})
    full_df = full_df.merge(counts_per_frame, on='frame', how='left')
    full_df['count'] = full_df['count'].fillna(0).astype(int)
    
    # 计算统计信息
    mean_val = full_df['count'].mean()
    std_val = full_df['count'].std()
    min_val = full_df['count'].min()
    max_val = full_df['count'].max()
    median_val = full_df['count'].median()
    
    # 写入.dat文件
    with open(output_file, 'w') as f:
        f.write(f"# Hydrogen Bond (All) per frame\n")
        f.write(f"# Merged from: hbbb, hbsb, hbss\n")
        f.write(f"# Total frames: {len(full_df)}\n")
        f.write(f"# Statistics:\n")
        f.write(f"#   Mean:   {mean_val:.2f}\n")
        f.write(f"#   Std:    {std_val:.2f}\n")
        f.write(f"#   Min:    {min_val}\n")
        f.write(f"#   Max:    {max_val}\n")
        f.write(f"#   Median: {median_val:.2f}\n")
        f.write(f"# Columns: frame count\n")
        for _, row in full_df.iterrows():
            f.write(f"{row['frame']:6d} {row['count']:6d}\n")
    
    print(f"已保存合并氢键数据: {output_file}")
    print(f"  平均氢键数: {mean_val:.2f} ± {std_val:.2f}")

def generate_summary_statistics(pivot_table, output_file='interaction_statistics_separate.dat'):
    """生成统计摘要并保存为.dat文件"""
    stats = pd.DataFrame({
        'Interaction_Type': [get_interaction_name(col, detailed=True) for col in pivot_table.columns],
        'Mean': pivot_table.mean().values,
        'Std': pivot_table.std().values,
        'Min': pivot_table.min().values,
        'Max': pivot_table.max().values,
        'Median': pivot_table.median().values,
        'Total': pivot_table.sum().values
    })
    
    stats = stats.round(2)
    
    # 添加总接触数行
    total_row = pd.DataFrame({
        'Interaction_Type': ['TOTAL (All Interactions)'],
        'Mean': [pivot_table.sum(axis=1).mean()],
        'Std': [pivot_table.sum(axis=1).std()],
        'Min': [pivot_table.sum(axis=1).min()],
        'Max': [pivot_table.sum(axis=1).max()],
        'Median': [pivot_table.sum(axis=1).median()],
        'Total': [pivot_table.sum().sum()]
    })
    
    stats = pd.concat([stats, total_row], ignore_index=True)
    
    # 保存为.dat文件
    with open(output_file, 'w') as f:
        f.write("# Interaction Statistics Summary (Separate)\n")
        f.write("# Columns: Interaction_Type Mean Std Min Max Median Total\n")
        f.write("#" + "-" * 100 + "\n")
        for idx, row in stats.iterrows():
            if idx == len(stats) - 1:  # 总计行
                f.write("#" + "-" * 100 + "\n")
            f.write(f"{row['Interaction_Type']:30s} {row['Mean']:8.2f} {row['Std']:8.2f} "
                   f"{row['Min']:6.0f} {row['Max']:6.0f} {row['Median']:8.2f} {row['Total']:10.0f}\n")
    
    print(f"\n已保存统计摘要: {output_file}")
    print("\n=== 统计摘要 (分开版本) ===")
    print(stats.to_string(index=False))
    
    return stats

# 主程序
if __name__ == '__main__':
    print("=" * 80)
    print("接触分析脚本 - 相互作用随时间变化分析")
    print("=" * 80)
    
    # 读取数据
    print("\n[1/5] 正在读取 contacts.tsv...")
    df_raw = parse_contacts_file('contacts.tsv')
    print(f"      共读取 {len(df_raw)} 条相互作用记录")
    print(f"      帧范围: {df_raw['frame'].min()} - {df_raw['frame'].max()}")
    print(f"      原始相互作用类型: {', '.join(sorted(df_raw['interaction_type'].unique()))}")
    
    # ========== 分开版本（详细氢键分类）==========
    print("\n" + "="*80)
    print("处理分开版本（详细氢键分类: hbbb, hbsb, hbss）")
    print("="*80)
    
    print("\n[2/5] 正在分类相互作用（分开版本）...")
    df_separate = categorize_interactions(df_raw, merge_hbond=False)
    print(f"      相互作用类型: {', '.join(sorted(df_separate['interaction_category'].unique()))}")
    
    print("\n[3/5] 正在统计每帧的相互作用数量（分开版本）...")
    pivot_separate = count_interactions_per_frame(df_separate)
    
    print("\n正在保存各类相互作用的详细数据到 interaction_data_separate/ ...")
    save_individual_interactions(df_separate, 'interaction_data_separate')
    
    print("\n正在生成统计摘要...")
    stats_separate = generate_summary_statistics(pivot_separate, 'interaction_statistics_separate.dat')
    
    # ========== 总接触数 ==========
    print("\n" + "="*80)
    print("计算总接触数（所有相互作用求和）")
    print("="*80)
    
    print("\n[4/5] 正在保存总接触数数据...")
    save_total_contact_number(df_separate, 'total_contact_number.dat')
    
    print("\n正在绘制总接触数图表...")
    plot_total_contacts(df_separate, 'total_contacts_over_time.png')
    
    # ========== 合并版本（仅氢键）==========
    print("\n" + "="*80)
    print("处理合并版本（氢键合并: hbbb + hbsb + hbss → Hbound）")
    print("="*80)
    
    print("\n[5/5] 正在合并氢键数据...")
    df_merged = categorize_interactions(df_raw, merge_hbond=True)
    
    save_hbound_merged(df_merged, 'hydrogen_bond_per_frame_merged.dat')
    
    # 最终总结
    print("\n" + "=" * 80)
    print("处理完成！")
    print("=" * 80)
    print(f"\n生成的文件:")
    print(f"  1. interaction_data_separate/ 文件夹 (各类相互作用详细数据):")
    print(f"     - hbond_bb_bb_per_frame.dat")
    print(f"     - hbond_sc_bb_per_frame.dat")
    print(f"     - hbond_sc_sc_per_frame.dat")
    print(f"     - salt_bridge_per_frame.dat")
    print(f"     - pi_cation_per_frame.dat")
    print(f"     - pi_pi_interaction_per_frame.dat")
    print(f"     - van_der_waals_per_frame.dat")
    print(f"     - hydrophobic_per_frame.dat")
    print(f"  2. hydrogen_bond_per_frame_merged.dat (合并的所有氢键)")
    print(f"  3. interaction_statistics_separate.dat (统计摘要，含总接触数)")
    print(f"  4. total_contact_number.dat (总接触数随时间变化) ★新增★")
    print(f"  5. total_contacts_over_time.png (总接触数图表) ★新增★")
    print("=" * 80)
