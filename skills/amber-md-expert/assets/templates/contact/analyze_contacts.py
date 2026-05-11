#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import pandas as pd
import re
from collections import defaultdict

def parse_contacts_file(filepath):
    """
    解析 contacts.tsv 文件
    返回：DataFrame 和 总帧数
    """
    total_frames = None
    data = []
    
    with open(filepath, 'r') as f:
        for line in f:
            # 解析总帧数
            if line.startswith("# total_frames:"):
                match = re.search(r'total_frames:(\d+)', line)
                if match:
                    total_frames = int(match.group(1))
                continue
            
            # 跳过注释
            if line.startswith("#"):
                continue
            
            # 解析数据行
            parts = line.strip().split('\t')
            if len(parts) >= 4:
                frame = int(parts[0])
                interaction_type = parts[1]
                atom1 = parts[2]
                atom2 = parts[3]
                
                # 解析残基信息
                res1 = parse_residue(atom1)
                res2 = parse_residue(atom2)
                
                data.append({
                    'frame': frame,
                    'type': interaction_type,
                    'atom1': atom1,
                    'atom2': atom2,
                    'res1': res1,
                    'res2': res2,
                    'res_pair': f"{res1}--{res2}"
                })
    
    df = pd.DataFrame(data)
    return df, total_frames

def parse_residue(atom_str):
    """
    从原子字符串提取残基信息
    例如: "X:GLN:32:CB" -> "GLN32"
    """
    parts = atom_str.split(':')
    if len(parts) >= 3:
        resname = parts[1]
        resid = parts[2]
        return f"{resname}{resid}"
    return atom_str

def classify_interaction(interaction_type):
    """
    将getcontacts的相互作用类型分类
    
    GetContacts定义：
    - hp: hydrophobic
    - sb: salt bridge  
    - pc: pi-cation
    - ps: pi-stacking (π-π平行堆积)
    - ts: T-stacking (π-π T型堆积)
    - vdw: van der Waals
    - hb: hydrogen bond (总称)
      - hbbb: backbone-backbone H-bond
      - hbsb: sidechain-backbone H-bond
      - hbss: sidechain-sidechain H-bond
    """
    itype = interaction_type.lower()
    
    # 氢键细分
    if itype == 'hbbb':
        return 'H-bond (BB-BB)'
    elif itype == 'hbsb':
        return 'H-bond (SC-BB)'
    elif itype == 'hbss':
        return 'H-bond (SC-SC)'
    elif itype == 'hb':
        return 'H-bond (general)'
    
    # 盐桥
    elif itype == 'sb':
        return 'Salt bridge'
    
    # π-π相互作用
    elif itype == 'ps':
        return 'π-stacking'
    elif itype == 'ts':
        return 'T-stacking'
    
    # π-阳离子
    elif itype == 'pc':
        return 'π-cation'
    
    # 疏水
    elif itype == 'hp':
        return 'Hydrophobic'
    
    # 范德华
    elif itype == 'vdw':
        return 'Van der Waals'
    
    return 'Other'

def get_interaction_group(category):
    """
    将细分类型归入主要类别
    用于汇总统计
    """
    if 'H-bond' in category:
        return 'Hydrogen bond'
    elif category in ['π-stacking', 'T-stacking']:
        return 'π-π interaction'
    elif category == 'Salt bridge':
        return 'Salt bridge'
    elif category == 'π-cation':
        return 'π-cation'
    elif category == 'Hydrophobic':
        return 'Hydrophobic'
    elif category == 'Van der Waals':
        return 'Van der Waals'
    return 'Other'

def calculate_statistics(df, total_frames):
    """计算统计信息"""
    
    # 为每个相互作用分类
    df['category'] = df['type'].apply(classify_interaction)
    df['group'] = df['category'].apply(get_interaction_group)
    
    # 统计1：按主要类别统计
    group_stats = df.groupby('group').agg({
        'frame': 'count',
        'res_pair': 'nunique'
    }).rename(columns={
        'frame': 'total_contacts',
        'res_pair': 'unique_pairs'
    })
    group_stats = group_stats.sort_values('total_contacts', ascending=False)
    
    # 统计2：按细分类型统计
    category_stats = df.groupby('category').agg({
        'frame': 'count',
        'res_pair': 'nunique'
    }).rename(columns={
        'frame': 'total_contacts',
        'res_pair': 'unique_pairs'
    })
    category_stats = category_stats.sort_values('total_contacts', ascending=False)
    
    # 统计3：每种类型的残基对及其频率
    pair_stats = {}
    for cat in df['category'].unique():
        cat_df = df[df['category'] == cat]
        pair_freq = cat_df.groupby('res_pair')['frame'].count()
        pair_freq = (pair_freq / total_frames * 100).sort_values(ascending=False)
        pair_stats[cat] = pair_freq
    
    # 统计4：主要类别的残基对
    group_pair_stats = {}
    for grp in df['group'].unique():
        grp_df = df[df['group'] == grp]
        pair_freq = grp_df.groupby('res_pair')['frame'].count()
        pair_freq = (pair_freq / total_frames * 100).sort_values(ascending=False)
        group_pair_stats[grp] = pair_freq
    
    # 统计5：原始类型统计
    raw_type_stats = df.groupby('type').agg({
        'frame': 'count',
        'res_pair': 'nunique'
    }).rename(columns={
        'frame': 'total_contacts',
        'res_pair': 'unique_pairs'
    })
    raw_type_stats = raw_type_stats.sort_values('total_contacts', ascending=False)
    
    return group_stats, category_stats, pair_stats, group_pair_stats, raw_type_stats

def print_summary(group_stats, category_stats, pair_stats, group_pair_stats, 
                 raw_type_stats, total_frames, top_n=10):
    """打印统计摘要"""
    
    print("=" * 80)
    print("CONTACT STATISTICS SUMMARY")
    print("=" * 80)
    print(f"Total frames analyzed: {total_frames:,}\n")
    
    # 主要类别统计
    print("-" * 80)
    print("1. MAIN INTERACTION CATEGORIES")
    print("-" * 80)
    print(f"{'Category':<25} {'Total':<12} {'Unique':<10} {'Avg/Frame':<12} {'%':<8}")
    print("-" * 80)
    total_all = group_stats['total_contacts'].sum()
    for grp, row in group_stats.iterrows():
        avg_per_frame = row['total_contacts'] / total_frames
        pct = row['total_contacts'] / total_all * 100
        print(f"{grp:<25} {row['total_contacts']:<12,} {row['unique_pairs']:<10} "
              f"{avg_per_frame:<12.3f} {pct:>6.2f}%")
    print()
    
    # 细分类型统计
    print("-" * 80)
    print("2. DETAILED INTERACTION TYPES")
    print("-" * 80)
    print(f"{'Type':<25} {'Total':<12} {'Unique':<10} {'Avg/Frame':<12} {'%':<8}")
    print("-" * 80)
    for cat, row in category_stats.iterrows():
        avg_per_frame = row['total_contacts'] / total_frames
        pct = row['total_contacts'] / total_all * 100
        print(f"{cat:<25} {row['total_contacts']:<12,} {row['unique_pairs']:<10} "
              f"{avg_per_frame:<12.3f} {pct:>6.2f}%")
    print()
    
    # 原始类型统计
    print("-" * 80)
    print("3. RAW INTERACTION CODES")
    print("-" * 80)
    print(f"{'Code':<10} {'Total':<12} {'Unique':<10} {'Description':<40}")
    print("-" * 80)
    
    type_descriptions = {
        'hp': 'Hydrophobic',
        'sb': 'Salt bridge',
        'pc': 'π-cation',
        'ps': 'π-stacking (parallel)',
        'ts': 'T-stacking (perpendicular π-π)',
        'vdw': 'Van der Waals',
        'hb': 'Hydrogen bond (general)',
        'hbbb': 'H-bond: backbone-backbone',
        'hbsb': 'H-bond: sidechain-backbone',
        'hbss': 'H-bond: sidechain-sidechain'
    }
    
    for itype, row in raw_type_stats.iterrows():
        desc = type_descriptions.get(itype, 'Unknown')
        print(f"{itype:<10} {row['total_contacts']:<12,} {row['unique_pairs']:<10} {desc:<40}")
    print()
    
    # 重点类型的Top残基对
    print("-" * 80)
    print("4. TOP RESIDUE PAIRS BY INTERACTION TYPE")
    print("-" * 80)
    
    target_groups = ['Hydrogen bond', 'Salt bridge', 'π-π interaction', 
                     'Hydrophobic', 'π-cation']
    
    for grp in target_groups:
        if grp in group_pair_stats and len(group_pair_stats[grp]) > 0:
            print(f"\n{grp.upper()}:")
            print(f"{'Residue Pair':<35} {'Frequency':<12} {'Frames':<10}")
            print("-" * 60)
            for res_pair, freq in group_pair_stats[grp].head(top_n).items():
                frames = int(freq * total_frames / 100)
                print(f"{res_pair:<35} {freq:>7.2f}% {frames:>10,}")
    
    # 氢键细分
    print("\n" + "-" * 80)
    print("5. HYDROGEN BOND SUBTYPES")
    print("-" * 80)
    
    hbond_types = ['H-bond (BB-BB)', 'H-bond (SC-BB)', 'H-bond (SC-SC)']
    for hb_type in hbond_types:
        if hb_type in pair_stats and len(pair_stats[hb_type]) > 0:
            print(f"\n{hb_type}:")
            print(f"{'Residue Pair':<35} {'Frequency':<12} {'Frames':<10}")
            print("-" * 60)
            for res_pair, freq in pair_stats[hb_type].head(top_n).items():
                frames = int(freq * total_frames / 100)
                print(f"{res_pair:<35} {freq:>7.2f}% {frames:>10,}")
    
    # π-π相互作用细分
    print("\n" + "-" * 80)
    print("6. π-π INTERACTION SUBTYPES")
    print("-" * 80)
    
    pi_types = ['π-stacking', 'T-stacking']
    for pi_type in pi_types:
        if pi_type in pair_stats and len(pair_stats[pi_type]) > 0:
            print(f"\n{pi_type}:")
            print(f"{'Residue Pair':<35} {'Frequency':<12} {'Frames':<10}")
            print("-" * 60)
            for res_pair, freq in pair_stats[pi_type].head(top_n).items():
                frames = int(freq * total_frames / 100)
                print(f"{res_pair:<35} {freq:>7.2f}% {frames:>10,}")

def save_detailed_report(df, pair_stats, group_pair_stats, total_frames, output_prefix):
    """保存详细报告到文件"""
    
    # 1. 保存主要类别的详细报告
    with open(f"{output_prefix}_summary.txt", 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("DETAILED INTERACTION STATISTICS\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total frames: {total_frames:,}\n\n")
        
        # 主要类别
        for grp in ['Hydrogen bond', 'Salt bridge', 'π-π interaction', 
                   'Hydrophobic', 'π-cation', 'Van der Waals']:
            if grp in group_pair_stats and len(group_pair_stats[grp]) > 0:
                f.write(f"\n{'='*80}\n")
                f.write(f"{grp.upper()}\n")
                f.write(f"{'='*80}\n")
                f.write(f"{'Residue Pair':<40} {'Frequency (%)':<15} {'Frames':<10}\n")
                f.write("-" * 80 + "\n")
                
                for res_pair, freq in group_pair_stats[grp].items():
                    frames = int(freq * total_frames / 100)
                    f.write(f"{res_pair:<40} {freq:>8.2f}% {frames:>15,}\n")
    
    # 2. 保存氢键细分
    with open(f"{output_prefix}_hbond_details.txt", 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("HYDROGEN BOND SUBTYPES\n")
        f.write("=" * 80 + "\n\n")
        
        for hb_type in ['H-bond (BB-BB)', 'H-bond (SC-BB)', 'H-bond (SC-SC)']:
            if hb_type in pair_stats and len(pair_stats[hb_type]) > 0:
                f.write(f"\n{hb_type}\n")
                f.write("-" * 80 + "\n")
                f.write(f"{'Residue Pair':<40} {'Frequency (%)':<15} {'Frames':<10}\n")
                f.write("-" * 80 + "\n")
                
                for res_pair, freq in pair_stats[hb_type].items():
                    frames = int(freq * total_frames / 100)
                    f.write(f"{res_pair:<40} {freq:>8.2f}% {frames:>15,}\n")
    
    # 3. 保存π-π相互作用细分
    with open(f"{output_prefix}_pi_details.txt", 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("π-π INTERACTION SUBTYPES\n")
        f.write("=" * 80 + "\n\n")
        
        for pi_type in ['π-stacking', 'T-stacking']:
            if pi_type in pair_stats and len(pair_stats[pi_type]) > 0:
                f.write(f"\n{pi_type}\n")
                f.write("-" * 80 + "\n")
                f.write(f"{'Residue Pair':<40} {'Frequency (%)':<15} {'Frames':<10}\n")
                f.write("-" * 80 + "\n")
                
                for res_pair, freq in pair_stats[pi_type].items():
                    frames = int(freq * total_frames / 100)
                    f.write(f"{res_pair:<40} {freq:>8.2f}% {frames:>15,}\n")
    
    # 4. 保存CSV格式
    csv_mapping = {
        'Hydrogen bond': 'hydrogen_bond',
        'Salt bridge': 'salt_bridge',
        'π-π interaction': 'pi_pi_interaction',
        'Hydrophobic': 'hydrophobic',
        'π-cation': 'pi_cation'
    }
    
    for grp, filename_part in csv_mapping.items():
        if grp in group_pair_stats and len(group_pair_stats[grp]) > 0:
            filename = f"{output_prefix}_{filename_part}.csv"
            pair_df = group_pair_stats[grp].reset_index()
            pair_df.columns = ['Residue_Pair', 'Frequency_Percent']
            pair_df['Frames'] = (pair_df['Frequency_Percent'] * total_frames / 100).astype(int)
            pair_df.to_csv(filename, index=False)
            print(f"✓ Saved: {filename}")
    
    # 5. 保存氢键和π-π的细分CSV
    for hb_type in ['H-bond (BB-BB)', 'H-bond (SC-BB)', 'H-bond (SC-SC)']:
        if hb_type in pair_stats and len(pair_stats[hb_type]) > 0:
            filename = f"{output_prefix}_hbond_{hb_type.split('(')[1].split(')')[0].replace('-', '_').lower()}.csv"
            pair_df = pair_stats[hb_type].reset_index()
            pair_df.columns = ['Residue_Pair', 'Frequency_Percent']
            pair_df['Frames'] = (pair_df['Frequency_Percent'] * total_frames / 100).astype(int)
            pair_df.to_csv(filename, index=False)
            print(f"✓ Saved: {filename}")
    
    for pi_type in ['π-stacking', 'T-stacking']:
        if pi_type in pair_stats and len(pair_stats[pi_type]) > 0:
            filename = f"{output_prefix}_{pi_type.replace('-', '_').lower()}.csv"
            pair_df = pair_stats[pi_type].reset_index()
            pair_df.columns = ['Residue_Pair', 'Frequency_Percent']
            pair_df['Frames'] = (pair_df['Frequency_Percent'] * total_frames / 100).astype(int)
            pair_df.to_csv(filename, index=False)
            print(f"✓ Saved: {filename}")
    
    print(f"\n✓ Saved: {output_prefix}_summary.txt")
    print(f"✓ Saved: {output_prefix}_hbond_details.txt")
    print(f"✓ Saved: {output_prefix}_pi_details.txt")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze contacts.tsv with proper classification of interaction types",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Interaction Types:
  Hydrogen bonds:
    - hbbb: backbone-backbone
    - hbsb: sidechain-backbone
    - hbss: sidechain-sidechain
  
  π-π interactions:
    - ps: π-stacking (parallel)
    - ts: T-stacking (perpendicular)
  
  Other:
    - sb: Salt bridge
    - pc: π-cation
    - hp: Hydrophobic
    - vdw: Van der Waals

Examples:
  # 基本统计
  python analyze_contacts.py --input contacts.tsv
  
  # 显示Top 20残基对
  python analyze_contacts.py --input contacts.tsv --top 20
  
  # 保存详细报告
  python analyze_contacts.py --input contacts.tsv --out my_report
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='Input contacts.tsv file')
    parser.add_argument('--top', '-n', type=int, default=10,
                       help='Number of top pairs to show (default: 10)')
    parser.add_argument('--out', '-o', default='contact_stats',
                       help='Output prefix for detailed reports')
    
    args = parser.parse_args()
    
    # 读取数据
    print(f"Loading contacts from: {args.input}")
    df, total_frames = parse_contacts_file(args.input)
    
    if total_frames is None:
        print("Warning: Could not find total_frames in header, using unique frames")
        total_frames = df['frame'].nunique()
    
    print(f"Loaded {len(df):,} contact records")
    print(f"Total frames: {total_frames:,}\n")
    
    # 计算统计
    group_stats, category_stats, pair_stats, group_pair_stats, raw_type_stats = \
        calculate_statistics(df, total_frames)
    
    # 打印摘要
    print_summary(group_stats, category_stats, pair_stats, group_pair_stats,
                 raw_type_stats, total_frames, args.top)
    
    # 保存详细报告
    print("\nSaving detailed reports...")
    save_detailed_report(df, pair_stats, group_pair_stats, total_frames, args.out)
    
    print("\n" + "=" * 80)
    print("✓ Analysis complete!")
    print("=" * 80)

if __name__ == '__main__':
    main()
