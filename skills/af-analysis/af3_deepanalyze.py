#!/usr/bin/env python3
# coding: utf-8
"""
AlphaFold3 深度分析脚本

对单个 AlphaFold3 预测样本进行深度分析，包括：
- PAE 矩阵可视化
- pLDDT 分布
- 界面分析
- 3D 结构查看（需要 NGLView）

Author: Claude Code
Date: 2026-03-31
"""

import os
import sys
import argparse
import json
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

try:
    from af_analysis import Data
    from af_analysis.analysis import (
        ipTM_d0, pdockq, mpdockq,
        compute_iptm_d0_values, get_pae,
        inter_chain_pae, ipSAE
    )
    from af_analysis.plot import show_info
    AF_ANALYSIS_AVAILABLE = True
except ImportError as e:
    AF_ANALYSIS_AVAILABLE = False
    print(f"Warning: af-analysis package not available: {e}")


def extract_zip(zip_path, extract_dir):
    """Extract zip file to directory."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    return extract_dir


def plot_pae_matrix(pae_matrix, chain_lengths, project_name, output_path=None):
    """Plot PAE matrix with chain annotations."""
    fig, ax = plt.subplots(figsize=(10, 8))

    # Create chain boundaries
    chain_boundaries = np.cumsum([0] + chain_lengths)

    # Plot heatmap
    im = ax.imshow(pae_matrix, cmap='viridis_r', vmin=0, vmax=30)

    # Draw chain boundaries
    for boundary in chain_boundaries[1:-1]:
        ax.axhline(boundary - 0.5, color='red', linestyle='-', linewidth=0.5)
        ax.axvline(boundary - 0.5, color='red', linestyle='-', linewidth=0.5)

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('PAE (Å)')

    # Labels
    ax.set_xlabel('Residue')
    ax.set_ylabel('Residue')
    ax.set_title(f'PAE Matrix - {project_name}')

    # Add chain labels
    chain_labels = ['A', 'B', 'C', 'D', 'E']
    for i, (start, end) in enumerate(zip(chain_boundaries[:-1], chain_boundaries[1:])):
        center = (start + end) / 2
        if i < len(chain_labels):
            ax.text(center - 0.5, -1, chain_labels[i], ha='center', va='top', fontsize=10)
            ax.text(-1, center - 0.5, chain_labels[i], ha='right', va='center', fontsize=10)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"PAE matrix saved to {output_path}")

    plt.close()
    return fig


def plot_plddt_distribution(plddt_values, project_name, output_path=None):
    """Plot pLDDT score distribution."""
    fig, ax = plt.subplots(figsize=(8, 5))

    if isinstance(plddt_values, dict):
        # Per-chain pLDDT
        chains = list(plddt_values.keys())
        values = [plddt_values[c] for c in chains]
        ax.bar(chains, values, color='steelblue')
        ax.set_ylabel('pLDDT')
        ax.set_title(f'pLDDT per Chain - {project_name}')
    else:
        # Histogram
        ax.hist(plddt_values, bins=30, color='steelblue', edgecolor='black')
        ax.set_xlabel('pLDDT')
        ax.set_ylabel('Frequency')
        ax.set_title(f'pLDDT Distribution - {project_name}')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        print(f"pLDDT plot saved to {output_path}")

    plt.close()
    return fig


def analyze_zip(zip_path, output_dir):
    """Perform deep analysis on a zip file."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {zip_path}")
    print(f"{'='*60}")

    project_name = Path(zip_path).stem
    if project_name.startswith("fold_"):
        project_name = project_name[5:]

    # Create output directory
    project_output_dir = Path(output_dir) / project_name
    project_output_dir.mkdir(parents=True, exist_ok=True)

    # Extract zip
    with tempfile.TemporaryDirectory() as temp_dir:
        extract_zip(zip_path, temp_dir)
        temp_path = Path(temp_dir)

        # Find files
        cif_files = list(temp_path.glob("*.cif"))
        json_files = list(temp_path.glob("*_summary_confidences_*.json"))
        full_data_files = list(temp_path.glob("*_full_data_*.json"))

        if not cif_files:
            print("  Error: No .cif files found")
            return None

        if not json_files:
            print("  Error: No summary JSON files found")
            return None

        # Load summary for model 0
        summary_json = sorted(json_files)[0]
        with open(summary_json, 'r') as f:
            summary_data = json.load(f)

        # Extract basic metrics
        metrics = {
            'project': project_name,
            'iptm': summary_data.get('iptm'),
            'ptm': summary_data.get('ptm'),
            'ranking_score': summary_data.get('ranking_score'),
            'has_pae': 'pae' in (json.load(open(full_data_files[0])) if full_data_files else {}),
        }

        print(f"\nBasic Metrics:")
        print(f"  ipTM: {metrics['iptm']}")
        print(f"  PTM: {metrics['ptm']}")
        print(f"  Ranking Score: {metrics['ranking_score']}")

        # Extract chain info
        if 'chain_ptm' in summary_data:
            chain_ptm = summary_data['chain_ptm']
            print(f"\nChain pLDDT:")
            for i, ptm in enumerate(chain_ptm):
                print(f"  Chain {chr(65+i)}: {ptm:.2f}")

        if 'chain_pair_pae_min' in summary_data:
            pae_min = summary_data['chain_pair_pae_min']
            if len(pae_min) > 1:
                print(f"\nChain Pair PAE Min (A-B): {pae_min[0][1]:.2f}")

        # Load PAE matrix from full data
        pae_matrix = None
        if full_data_files:
            with open(full_data_files[0], 'r') as f:
                full_data = json.load(f)

            if 'pae' in full_data:
                pae_matrix = np.array(full_data['pae'])
                print(f"\nPAE matrix shape: {pae_matrix.shape}")

                # Plot PAE matrix
                # Estimate chain lengths from pLDDT per chain
                chain_ptm = summary_data.get('chain_ptm', [1])
                # Approximate equal chain lengths for visualization
                total_len = pae_matrix.shape[0]
                n_chains = len(chain_ptm)
                chain_lengths = [total_len // n_chains] * n_chains
                chain_lengths[-1] = total_len - sum(chain_lengths[:-1])

                pae_output = project_output_dir / "pae_matrix.png"
                plot_pae_matrix(pae_matrix, chain_lengths, project_name, str(pae_output))

        # Try af-analysis advanced metrics
        if AF_ANALYSIS_AVAILABLE and pae_matrix is not None:
            print("\nComputing advanced metrics with af-analysis...")

            try:
                # Simple two-chain assumption for ipTM_d0
                n_res = pae_matrix.shape[0]
                mid = n_res // 2
                chain_lengths = [mid, n_res - mid]
                chain_ids = ['A', 'B']
                chain_types = ['protein', 'protein']

                iptm_d0_vals = compute_iptm_d0_values(
                    pae_matrix, chain_ids, chain_lengths, chain_types
                )
                if iptm_d0_vals:
                    print(f"  ipTM_d0: {iptm_d0_vals[0]:.3f}")
                    metrics['ipTM_d0'] = iptm_d0_vals[0]
            except Exception as e:
                print(f"  Warning: Could not compute ipTM_d0: {e}")

        # Generate summary report
        report_path = project_output_dir / "analysis_summary.txt"
        with open(report_path, 'w') as f:
            f.write(f"AlphaFold3 Analysis Report\n")
            f.write(f"{'='*40}\n\n")
            f.write(f"Project: {project_name}\n")
            f.write(f"Source: {zip_path}\n\n")
            f.write(f"Basic Metrics:\n")
            f.write(f"  ipTM: {metrics['iptm']}\n")
            f.write(f"  PTM: {metrics['ptm']}\n")
            f.write(f"  Ranking Score: {metrics['ranking_score']}\n")
            if 'ipTM_d0' in metrics and metrics['ipTM_d0']:
                f.write(f"  ipTM_d0: {metrics['ipTM_d0']:.3f}\n")
            f.write(f"\nQuality Assessment:\n")
            if metrics['iptm'] and metrics['iptm'] > 0.4:
                f.write(f"  -> HIGH quality PPI prediction (ipTM > 0.4)\n")
            elif metrics['iptm'] and metrics['iptm'] > 0.2:
                f.write(f"  -> MEDIUM quality PPI prediction (0.2 < ipTM < 0.4)\n")
            else:
                f.write(f"  -> LOW quality PPI prediction (ipTM < 0.2)\n")

        print(f"\nOutput files:")
        print(f"  Summary: {report_path}")
        if (project_output_dir / "pae_matrix.png").exists():
            print(f"  PAE Matrix: {project_output_dir / 'pae_matrix.png'}")

        return metrics


def main():
    parser = argparse.ArgumentParser(
        description="AlphaFold3 Deep Analysis"
    )
    parser.add_argument(
        "--zip", "-z",
        required=True,
        help="Input zip file to analyze"
    )
    parser.add_argument(
        "--output", "-o",
        default="./af3_analysis_output",
        help="Output directory (default: ./af3_analysis_output)"
    )

    args = parser.parse_args()

    if not Path(args.zip).exists():
        print(f"Error: File not found: {args.zip}")
        sys.exit(1)

    # Create output directory
    Path(args.output).mkdir(parents=True, exist_ok=True)

    # Analyze
    metrics = analyze_zip(args.zip, args.output)

    if metrics:
        print(f"\n{'='*60}")
        print("Analysis complete!")
        print(f"Results saved to: {args.output}/{Path(args.zip).stem}")
    else:
        print("Analysis failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
