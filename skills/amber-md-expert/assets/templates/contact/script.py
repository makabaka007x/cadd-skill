#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import re
import sys

# -------------------- Parsing helpers --------------------

def read_skip_comments(path):
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.lstrip().startswith("#")]
    if not lines:
        raise ValueError("No data after skipping comment lines in: %s" % path)
    from io import StringIO
    return pd.read_csv(StringIO("".join(lines)), sep=None, engine="python", header=None)

def parse_resid(s):
    """
    从残基标识中提取残基号
    支持: "ARG:245", "245", "A:ARG:245" 等
    """
    s = str(s).strip()
    
    # 提取最后的数字
    m = re.search(r'(\d+)$', s)
    if m:
        return int(m.group(1))
    
    # 如果有冒号分隔，取最后一段
    if ':' in s:
        parts = s.split(':')
        for part in reversed(parts):
            try:
                return int(part)
            except ValueError:
                continue
    
    return None

def load_freq_file(path):
    """读取频率文件"""
    df = read_skip_comments(path)
    
    if df.shape[1] == 3:
        df.columns = ["residue_1", "residue_2", "freq"]
    elif df.shape[1] >= 4:
        df = df.iloc[:, [0, 1, -1]]
        df.columns = ["residue_1", "residue_2", "freq"]
    else:
        raise ValueError("Unexpected column count in frequency file.")
    
    # 解析残基号
    df["i_resid"] = df["residue_1"].apply(parse_resid)
    df["j_resid"] = df["residue_2"].apply(parse_resid)
    df["freq"] = pd.to_numeric(df["freq"], errors="coerce").clip(0, 1)
    
    df = df.dropna(subset=["i_resid", "j_resid", "freq"]).copy()
    df["i_resid"] = df["i_resid"].astype(int)
    df["j_resid"] = df["j_resid"].astype(int)
    
    return df

# -------------------- PDB residue names --------------------

def load_pdb_resnames_no_chain(pdb_path):
    """
    从PDB提取残基名（忽略链ID）
    返回 resid -> resname 的映射
    """
    resid_to_name = {}
    with open(pdb_path, "r", encoding="utf-8") as f:
        for line in f:
            if not (line.startswith("ATOM  ") or line.startswith("HETATM")):
                continue
            if len(line) < 26:
                continue
            
            resname = line[17:20].strip()
            try:
                resid = int(line[22:26])
            except ValueError:
                continue
            
            if re.fullmatch(r"[A-Za-z0-9]{3}", resname):
                resid_to_name[resid] = resname.upper()
    
    return resid_to_name

# -------------------- Interchain filtering --------------------

def filter_interchain_contacts(df, range1, range2):
    """
    筛选链间接触
    range1: (start1, end1) - 第一条链的残基范围
    range2: (start2, end2) - 第二条链的残基范围
    """
    start1, end1 = range1
    start2, end2 = range2
    
    # 链1 <-> 链2 的接触
    cond1 = df["i_resid"].between(start1, end1) & \
            df["j_resid"].between(start2, end2)
    
    cond2 = df["j_resid"].between(start1, end1) & \
            df["i_resid"].between(start2, end2)
    
    df = df[cond1 | cond2].copy()
    
    # 规范方向：i为链1，j为链2
    swap = cond2.loc[df.index]
    tmp = df.loc[swap, "i_resid"].copy()
    df.loc[swap, "i_resid"] = df.loc[swap, "j_resid"].values
    df.loc[swap, "j_resid"] = tmp.values
    
    return df

# -------------------- Mapping --------------------

def build_residue_mapping(topo_range, real_range):
    """
    构建残基编号映射
    topo_range: getcontacts中的残基范围 (1, 31)
    real_range: 真实序列编号 (244, 274)
    """
    topo_start, topo_end = topo_range
    real_start, real_end = real_range
    
    topo_list = list(range(topo_start, topo_end + 1))
    real_list = list(range(real_start, real_end + 1))
    
    if len(topo_list) != len(real_list):
        raise ValueError(f"Range mismatch: {len(topo_list)} vs {len(real_list)}")
    
    return dict(zip(topo_list, real_list))

# -------------------- Labels --------------------

def build_labels(pdb_resnames, topo_range, real_range, label_format="short"):
    """
    构建残基标签
    label_format:
      - "short": ARG244
      - "real": 244
      - "topo": 1
    """
    mapping = build_residue_mapping(topo_range, real_range)
    labels = []
    
    for topo_id in range(topo_range[0], topo_range[1] + 1):
        real_id = mapping[topo_id]
        resname = pdb_resnames.get(topo_id, "UNK")
        
        if label_format == "real":
            labels.append(str(real_id))
        elif label_format == "topo":
            labels.append(str(topo_id))
        else:  # short
            labels.append(f"{resname}{real_id}")
    
    return labels, mapping

# -------------------- Matrix --------------------

def build_contact_matrix(df, range1, range2, min_freq=0.0):
    """构建接触矩阵"""
    res1_list = list(range(range1[0], range1[1] + 1))
    res2_list = list(range(range2[0], range2[1] + 1))
    
    mat = pd.DataFrame(0.0, index=res1_list, columns=res2_list, dtype=float)
    
    grouped = df.groupby(["i_resid", "j_resid"])["freq"].mean().reset_index()
    if min_freq > 0:
        grouped = grouped[grouped["freq"] >= min_freq]
    
    for _, row in grouped.iterrows():
        i_res = int(row["i_resid"])
        j_res = int(row["j_resid"])
        if i_res in res1_list and j_res in res2_list:
            mat.at[i_res, j_res] = float(row["freq"])
    
    return mat

# -------------------- Plotting --------------------

def plot_heatmap(mat, out_prefix="contact_map", 
                title="Intrachain Residue Contacts",
                cmap="YlOrRd",
                figsize=None,
                dpi=600,
                **kwargs):
    """绘制热图 - 显示所有残基标签"""
    # 论文风格设置
    plt.rcParams.update({
        'font.family': 'Arial',
        'font.size': 8,
        'axes.linewidth': 0.5,
        'xtick.major.width': 0.5,
        'ytick.major.width': 0.5,
        'xtick.major.size': 2.5,
        'ytick.major.size': 2.5,
    })
    
    # 自动计算图形尺寸
    if figsize is None:
        width = max(3.5, len(mat.columns) * 0.15)
        height = max(3.0, len(mat.index) * 0.15)
        figsize = (width, height)
    
    fig, ax = plt.subplots(figsize=figsize)
    
    # 提取参数
    x_rotation = kwargs.get('x_rotation', 90)
    y_rotation = kwargs.get('y_rotation', 0)
    xlabel_fontsize = kwargs.get('xlabel_fontsize', 7)
    ylabel_fontsize = kwargs.get('ylabel_fontsize', 7)
    title_fontsize = kwargs.get('title_fontsize', 9)
    tick_fontsize = kwargs.get('tick_fontsize', 6)
    
    # 绘制热图
    sns.heatmap(
        mat,
        cmap=cmap,
        vmin=0.0,
        vmax=1.0,
        cbar_kws={
            "label": "Contact Frequency",
            "shrink": 0.7,
            "aspect": 20,
            "pad": 0.02
        },
        linewidths=0,
        square=True,
        ax=ax,
        xticklabels=True,  # 显示所有X轴标签
        yticklabels=True   # 显示所有Y轴标签
    )
    
    # 设置标签
    ax.set_xlabel(kwargs.get('xlabel', 'Residue (Chain 2)'), 
                  fontsize=xlabel_fontsize, labelpad=5)
    ax.set_ylabel(kwargs.get('ylabel', 'Residue (Chain 1)'), 
                  fontsize=ylabel_fontsize, labelpad=5)
    ax.set_title(title, fontsize=title_fontsize, fontweight='bold', pad=10)
    
    # 强制显示所有刻度标签
    ax.set_xticks(np.arange(len(mat.columns)) + 0.5)
    ax.set_yticks(np.arange(len(mat.index)) + 0.5)
    ax.set_xticklabels(
        mat.columns,
        rotation=x_rotation,
        ha='center' if x_rotation == 90 else 'right',
        fontsize=tick_fontsize
    )
    ax.set_yticklabels(
        mat.index,
        rotation=y_rotation,
        va='center',
        fontsize=tick_fontsize
    )
    
    # Colorbar
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=7)
    cbar.set_label("Contact Frequency", fontsize=8)
    
    plt.tight_layout()
    
    # 保存
    png = f"{out_prefix}.png"
    pdf = f"{out_prefix}.pdf"
    plt.savefig(png, dpi=dpi, bbox_inches='tight')
    plt.savefig(pdf, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved: {png} (DPI={dpi})")
    print(f"✓ Saved: {pdf}")

# -------------------- Main --------------------

def main():
    ap = argparse.ArgumentParser(
        description="Plot interchain contact heatmap for homodimer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 基本用法（链间接触）
  python script.py --freq resfrequencies.tsv --pdb md-initial.pdb \\
    --chain1_topo 1 31 --chain2_topo 32 62 \\
    --real_resid 244 274

  # 自定义样式
  python script.py --freq resfrequencies.tsv --pdb md-initial.pdb \\
    --chain1_topo 1 31 --chain2_topo 32 62 \\
    --real_resid 244 274 \\
    --min_freq 0.3 --cmap RdPu \\
    --label_format short --tick_fontsize 5
        """
    )
    
    # 必需参数
    ap.add_argument("--freq", required=True, 
                   help="resfrequencies.tsv")
    ap.add_argument("--pdb", required=True, 
                   help="PDB file")
    
    # 残基范围（getcontacts拓扑编号）
    ap.add_argument("--chain1_topo", nargs=2, type=int, default=[1, 31],
                   help="Chain 1 topology range (default: 1 31)")
    ap.add_argument("--chain2_topo", nargs=2, type=int, default=[32, 62],
                   help="Chain 2 topology range (default: 32 62)")
    
    # 真实序列编号
    ap.add_argument("--real_resid", nargs=2, type=int, default=[244, 274],
                   help="Real residue range (default: 244 274)")
    
    # 标签格式
    ap.add_argument("--label_format", choices=["short", "real", "topo"],
                   default="short",
                   help="Label format: short=ARG244, real=244, topo=1")
    
    # 输出
    ap.add_argument("--out", default="contact_map", 
                   help="Output prefix")
    ap.add_argument("--title", default="Intra-chain H-bond Contacts",
                   help="Plot title")
    
    # 过滤和样式
    ap.add_argument("--min_freq", type=float, default=0.0,
                   help="Minimum contact frequency threshold")
    ap.add_argument("--cmap", default="YlOrRd",
                   help="Colormap (YlOrRd, RdPu, Blues, etc.)")
    ap.add_argument("--figsize", nargs=2, type=float, default=None,
                   help="Figure size (width height) in inches")
    ap.add_argument("--dpi", type=int, default=600,
                   help="Output resolution")
    
    # 字体设置
    ap.add_argument("--x_rotation", type=int, default=90,
                   help="X-axis label rotation")
    ap.add_argument("--y_rotation", type=int, default=0,
                   help="Y-axis label rotation")
    ap.add_argument("--xlabel_fontsize", type=int, default=7,
                   help="X-axis label font size")
    ap.add_argument("--ylabel_fontsize", type=int, default=7,
                   help="Y-axis label font size")
    ap.add_argument("--title_fontsize", type=int, default=9,
                   help="Title font size")
    ap.add_argument("--tick_fontsize", type=int, default=6,
                   help="Tick label font size")
    
    args = ap.parse_args()
    
    # 读取数据
    print(f"Loading frequency file: {args.freq}")
    df = load_freq_file(args.freq)
    print(f"Total contact pairs: {len(df)}")
    
    # 筛选链间接触
    chain1_range = tuple(args.chain1_topo)
    chain2_range = tuple(args.chain2_topo)
    
    print(f"\nFiltering interchain contacts:")
    print(f"  Chain 1: residues {chain1_range[0]}-{chain1_range[1]} (topology)")
    print(f"  Chain 2: residues {chain2_range[0]}-{chain2_range[1]} (topology)")
    
    df = filter_interchain_contacts(df, chain1_range, chain2_range)
    
    if df.empty:
        print("\nERROR: No interchain contacts found!", file=sys.stderr)
        print(f"Check your residue ranges:", file=sys.stderr)
        print(f"  --chain1_topo {chain1_range[0]} {chain1_range[1]}", file=sys.stderr)
        print(f"  --chain2_topo {chain2_range[0]} {chain2_range[1]}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Found {len(df)} interchain contact pairs")
    
    # 加载PDB残基名
    print(f"\nLoading PDB: {args.pdb}")
    pdb_resnames = load_pdb_resnames_no_chain(args.pdb)
    print(f"Found {len(pdb_resnames)} residue names in PDB")
    
    # 构建标签
    real_range = tuple(args.real_resid)
    chain1_labels, map1 = build_labels(
        pdb_resnames, chain1_range, real_range, args.label_format
    )
    chain2_labels, map2 = build_labels(
        pdb_resnames, chain2_range, real_range, args.label_format
    )
    
    # 构建矩阵
    print("\nBuilding contact matrix...")
    mat = build_contact_matrix(df, chain1_range, chain2_range, args.min_freq)
    mat.index = chain1_labels
    mat.columns = chain2_labels
    
    non_zero = (mat > 0).sum().sum()
    print(f"Matrix size: {mat.shape[0]} × {mat.shape[1]}")
    print(f"Non-zero contacts: {non_zero}")
    
    if non_zero == 0:
        print("\nWARNING: No contacts above threshold!", file=sys.stderr)
        print(f"Try lowering --min_freq (current: {args.min_freq})", file=sys.stderr)
    
    # 绘图
    print("\nPlotting heatmap...")
    plot_heatmap(
        mat,
        out_prefix=args.out,
        title=args.title,
        cmap=args.cmap,
        figsize=tuple(args.figsize) if args.figsize else None,
        dpi=args.dpi,
        x_rotation=args.x_rotation,
        y_rotation=args.y_rotation,
        xlabel_fontsize=args.xlabel_fontsize,
        ylabel_fontsize=args.ylabel_fontsize,
        title_fontsize=args.title_fontsize,
        tick_fontsize=args.tick_fontsize,
        xlabel=f"Residue name",
        ylabel=f"Residue name"
    )
    
    print("\n✓ Done!")

if __name__ == "__main__":
    main()
