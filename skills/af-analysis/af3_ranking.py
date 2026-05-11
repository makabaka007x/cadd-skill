#!/usr/bin/env python3
# coding: utf-8
"""
AlphaFold3 PPI Ranking 分析脚本

使用 af-analysis 包对 AlphaFold3 预测结果进行深度分析并排序。
支持两种输入格式：
1. AlphaFold Server zip 文件 (fold_*.zip)
2. 本地运行输出的目录结构

Author: Claude Code
Date: 2026-03-31
"""

import os
import sys
import argparse
import tempfile
import zipfile
import shutil
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm.auto import tqdm

try:
    from af_analysis import Data
    from af_analysis.analysis import ipTM_d0, pdockq, mpdockq, compute_iptm_d0_values, get_pae
    AF_ANALYSIS_AVAILABLE = True
except ImportError as e:
    AF_ANALYSIS_AVAILABLE = False
    print(f"Warning: af-analysis package not available: {e}")
    print("Falling back to basic JSON parsing...")


def extract_zip(zip_path, extract_dir):
    """Extract zip file to directory."""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)
    return extract_dir


def process_zip_files(input_dir, output_file=None):
    """Process AlphaFold Server zip files."""
    zip_files = list(Path(input_dir).glob("fold_*.zip"))

    if not zip_files:
        print("No fold_*.zip files found in the input directory.")
        return pd.DataFrame()

    print(f"Found {len(zip_files)} zip files to process...")

    all_results = []

    for zip_path in tqdm(zip_files, desc="Processing zip files"):
        try:
            # Extract to temp directory
            with tempfile.TemporaryDirectory() as temp_dir:
                extract_zip(zip_path, temp_dir)

                # Find extracted files
                cif_files = list(Path(temp_dir).glob("*.cif"))
                if not cif_files:
                    print(f"  Warning: No .cif files found in {zip_path}")
                    continue

                # Extract project name from zip filename
                project_name = zip_path.stem
                if project_name.startswith("fold_"):
                    project_name = project_name[5:]

                # Find summary JSON for model 0 (best ranking)
                summary_json = Path(temp_dir) / f"{zip_path.stem}_summary_confidences_0.json"
                if not summary_json.exists():
                    # Try to find any summary json
                    summary_jsons = list(Path(temp_dir).glob("*_summary_confidences_*.json"))
                    if summary_jsons:
                        summary_json = summary_jsons[0]
                    else:
                        print(f"  Warning: No summary JSON found in {zip_path}")
                        continue

                # Parse JSON data
                import json
                with open(summary_json, 'r') as f:
                    json_data = json.load(f)

                # Extract key metrics
                iptm = json_data.get('iptm', None)
                ptm = json_data.get('ptm', None)
                ranking_score = json_data.get('ranking_score', None)

                # Try to get chain_pair_pae_min
                chain_pair_pae_min = None
                if 'chain_pair_pae_min' in json_data:
                    pae_data = json_data['chain_pair_pae_min']
                    if isinstance(pae_data, list) and len(pae_data) > 1:
                        chain_pair_pae_min = pae_data[0][1] if isinstance(pae_data[0], list) else pae_data[1]

                # Try to get chain_ptm
                chain_ptm = None
                if 'chain_ptm' in json_data:
                    chain_ptm = json_data['chain_ptm']

                result = {
                    'project': project_name,
                    'zip_file': str(zip_path),
                    'iptm': iptm,
                    'ptm': ptm,
                    'ranking_score': ranking_score,
                    'chain_pair_pae_min': chain_pair_pae_min,
                    'chain_ptm': '/'.join(map(str, chain_ptm)) if chain_ptm else None,
                    'ipTM_d0': None,  # Will be computed if af-analysis is available
                    'pDockQ': None,
                    'model': 0
                }

                # Compute advanced metrics if af-analysis is available
                if AF_ANALYSIS_AVAILABLE:
                    try:
                        # Load full data JSON for PAE matrix
                        full_data_json = Path(temp_dir) / f"{zip_path.stem}_full_data_0.json"
                        if full_data_json.exists():
                            with open(full_data_json, 'r') as f:
                                full_data = json.load(f)

                            # Extract PAE matrix
                            if 'pae' in full_data:
                                pae_matrix = np.array(full_data['pae'])

                                # Extract chain info from cif file
                                cif_path = str(cif_files[0])
                                try:
                                    import pdb_numpy
                                    model = pdb_numpy.Coor(cif_path)

                                    # Get chain information
                                    chain_ids = list(set(model.chain))
                                    chain_lengths = [np.sum(model.chain == c) for c in chain_ids]
                                    chain_types = ['protein'] * len(chain_ids)  # Simplified assumption

                                    # Compute ipTM_d0
                                    iptm_d0_vals = compute_iptm_d0_values(
                                        pae_matrix, chain_ids, chain_lengths, chain_types
                                    )
                                    if iptm_d0_vals and len(iptm_d0_vals) > 0:
                                        result['ipTM_d0'] = iptm_d0_vals[0] if isinstance(iptm_d0_vals, list) else iptm_d0_vals
                                except Exception as e:
                                    print(f"    Warning: Could not compute advanced metrics: {e}")
                    except Exception as e:
                        print(f"    Warning: af-analysis computation failed: {e}")

                all_results.append(result)

        except Exception as e:
            print(f"  Error processing {zip_path}: {e}")
            continue

    if not all_results:
        return pd.DataFrame()

    df = pd.DataFrame(all_results)

    # Sort by iptm (descending)
    if 'iptm' in df.columns:
        df = df.sort_values(by='iptm', ascending=False, na_position='last')
        df['rank'] = range(1, len(df) + 1)

    return df


def process_directories(input_dir, output_file=None):
    """Process local AlphaFold3 output directories."""
    # Look for directories containing .cif files
    # Skip .claude and other hidden directories
    target_dirs = []

    for item in Path(input_dir).iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            cif_files = list(item.glob("*.cif"))
            if cif_files:
                target_dirs.append(item)

    if not target_dirs:
        print("No directories with .cif files found.")
        return pd.DataFrame()

    print(f"Found {len(target_dirs)} directories to process...")

    all_results = []

    for dir_path in tqdm(target_dirs, desc="Processing directories"):
        try:
            cif_files = list(dir_path.glob("*.cif"))
            if not cif_files:
                continue

            # Extract project name
            project_name = dir_path.name

            # Find summary JSON
            summary_jsons = list(dir_path.glob("*_summary_confidences_*.json"))
            if not summary_jsons:
                summary_jsons = list(dir_path.glob("*summary_confidences*.json"))

            if not summary_jsons:
                print(f"  Warning: No summary JSON found in {dir_path}")
                continue

            # Use model 0 or first available
            summary_json = sorted(summary_jsons)[0]

            import json
            with open(summary_json, 'r') as f:
                json_data = json.load(f)

            result = {
                'project': project_name,
                'directory': str(dir_path),
                'iptm': json_data.get('iptm', None),
                'ptm': json_data.get('ptm', None),
                'ranking_score': json_data.get('ranking_score', None),
                'chain_pair_pae_min': None,
                'chain_ptm': None,
                'ipTM_d0': None,
                'pDockQ': None,
            }

            # Extract chain_pair_pae_min
            if 'chain_pair_pae_min' in json_data:
                pae_data = json_data['chain_pair_pae_min']
                if isinstance(pae_data, list) and len(pae_data) > 1:
                    result['chain_pair_pae_min'] = pae_data[0][1] if isinstance(pae_data[0], list) else pae_data[1]

            # Extract chain_ptm
            if 'chain_ptm' in json_data:
                chain_ptm = json_data['chain_ptm']
                result['chain_ptm'] = '/'.join(map(str, chain_ptm)) if isinstance(chain_ptm, list) else str(chain_ptm)

            all_results.append(result)

        except Exception as e:
            print(f"  Error processing {dir_path}: {e}")
            continue

    if not all_results:
        return pd.DataFrame()

    df = pd.DataFrame(all_results)

    # Sort by iptm (descending)
    if 'iptm' in df.columns:
        df = df.sort_values(by='iptm', ascending=False, na_position='last')
        df['rank'] = range(1, len(df) + 1)

    return df


def format_markdown_table(df):
    """Format DataFrame as Markdown table."""
    if df.empty:
        return "No data to display."

    lines = []
    lines.append("| 排名 | 项目名称 | ipTM | ipTM_d0 | PTM | Ranking Score | Chain Pair PAE Min | Chain PTM |")
    lines.append("|------|----------|------|---------|-----|---------------|-------------------|-----------|")

    for _, row in df.iterrows():
        rank = row.get('rank', 'N/A')
        project = row.get('project', 'N/A')
        iptm = f"{row['iptm']:.2f}" if pd.notna(row.get('iptm')) else 'N/A'
        iptm_d0 = f"{row['ipTM_d0']:.2f}" if pd.notna(row.get('ipTM_d0')) else 'N/A'
        ptm = f"{row['ptm']:.2f}" if pd.notna(row.get('ptm')) else 'N/A'
        ranking = f"{row['ranking_score']:.2f}" if pd.notna(row.get('ranking_score')) else 'N/A'
        pae_min = f"{row['chain_pair_pae_min']:.2f}" if pd.notna(row.get('chain_pair_pae_min')) else 'N/A'
        chain_ptm = row.get('chain_ptm', 'N/A')

        lines.append(f"| {rank} | {project} | {iptm} | {iptm_d0} | {ptm} | {ranking} | {pae_min} | {chain_ptm} |")

    return '\n'.join(lines)


def format_csv(df):
    """Format DataFrame as CSV."""
    return df.to_csv(index=False)


def main():
    parser = argparse.ArgumentParser(
        description="AlphaFold3 PPI Ranking Analysis using af-analysis package"
    )
    parser.add_argument(
        "--input", "-i",
        default=".",
        help="Input directory containing zip files or output directories (default: current directory)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: stdout for markdown, af3_ranking.csv for CSV)"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["markdown", "csv", "both"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    parser.add_argument(
        "--zip-only",
        action="store_true",
        help="Only process zip files"
    )
    parser.add_argument(
        "--dir-only",
        action="store_true",
        help="Only process directories"
    )

    args = parser.parse_args()

    # Process data
    if args.zip_only:
        df = process_zip_files(args.input)
    elif args.dir_only:
        df = process_directories(args.input)
    else:
        # Try both, but prioritize zip files (directories may be extracted from zips)
        df_zip = process_zip_files(args.input)
        df_dir = process_directories(args.input)

        if not df_zip.empty and not df_dir.empty:
            # Normalize project names for deduplication (add fold_ prefix if missing)
            def normalize_name(name):
                if not name.startswith('fold_'):
                    return 'fold_' + name
                return name

            df_zip['project_normalized'] = df_zip['project'].apply(normalize_name)
            df_dir['project_normalized'] = df_dir['project'].apply(normalize_name)

            # Remove duplicate projects (prefer zip results over directory results)
            zip_projects = set(df_zip['project_normalized'].tolist())
            df_dir_filtered = df_dir[~df_dir['project_normalized'].isin(zip_projects)]

            if not df_dir_filtered.empty:
                df = pd.concat([df_zip, df_dir_filtered], ignore_index=True)
            else:
                df = df_zip
            # Re-rank combined results
            if 'iptm' in df.columns:
                df = df.sort_values(by='iptm', ascending=False, na_position='last')
                df['rank'] = range(1, len(df) + 1)

            # Drop the normalized column
            df = df.drop(columns=['project_normalized'], errors='ignore')
        elif not df_zip.empty:
            df = df_zip
        else:
            df = df_dir

    if df.empty:
        print("No data to process. Exiting.")
        sys.exit(0)

    # Output results
    if args.format == "markdown":
        md_table = format_markdown_table(df)
        if args.output:
            with open(args.output, 'w') as f:
                f.write(md_table)
            print(f"Markdown table written to {args.output}")
        else:
            print(md_table)

    elif args.format == "csv":
        csv_data = format_csv(df)
        out_file = args.output if args.output else "af3_ranking.csv"
        with open(out_file, 'w') as f:
            f.write(csv_data)
        print(f"CSV written to {out_file}")

    elif args.format == "both":
        # Markdown
        md_table = format_markdown_table(df)
        md_file = args.output + ".md" if args.output else "af3_ranking.md"
        with open(md_file, 'w') as f:
            f.write(md_table)
        print(f"Markdown table written to {md_file}")

        # CSV
        csv_data = format_csv(df)
        csv_file = args.output + ".csv" if args.output else "af3_ranking.csv"
        with open(csv_file, 'w') as f:
            f.write(csv_data)
        print(f"CSV written to {csv_file}")

    # Print summary
    print(f"\nProcessed {len(df)} samples.")
    if 'iptm' in df.columns:
        high_quality = df[df['iptm'] > 0.4].shape[0]
        medium_quality = df[(df['iptm'] >= 0.2) & (df['iptm'] <= 0.4)].shape[0]
        low_quality = df[df['iptm'] < 0.2].shape[0]
        print(f"Quality distribution: High (ipTM>0.4): {high_quality}, Medium (0.2-0.4): {medium_quality}, Low (<0.2): {low_quality}")


if __name__ == "__main__":
    main()
