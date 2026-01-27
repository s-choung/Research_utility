#!/usr/bin/env python3
"""
Simplified GA Runner with flexible atom numbers and flat structure
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scripts.ga_metal_oxide import (
    load_oxide_slab, load_uma_calculator, run_single_ga
)


def run_ga_job(config_file: str = None, **kwargs):
    """
    Run a single GA job from config file or parameters

    Parameters:
    -----------
    config_file : str
        Path to configuration file (JSON)
    **kwargs : dict
        Direct parameters if not using config file
        Required: metal, slab, n_metal
        Optional: n_oxide, output_dir, device

    Returns:
    --------
    results : dict
        GA optimization results
    """
    # Load configuration
    if config_file:
        with open(config_file, 'r') as f:
            config = json.load(f)
    else:
        config = kwargs

    # Required parameters
    metal = config['metal']
    slab = config['slab']
    n_metal = config['n_metal']
    n_oxide = config.get('n_oxide', 0)
    device = config.get('device', 'cuda')

    # Create atom configuration string
    atom_config = f"M{n_metal}"
    if n_oxide > 0:
        atom_config += f"O{n_oxide}"

    # Output directory
    if 'output_dir' in config:
        output_dir = Path(config['output_dir'])
    else:
        output_dir = Path.cwd() / f"runs_{atom_config}" / f"{metal}_{slab}"

    output_dir.mkdir(parents=True, exist_ok=True)

    # Load configurations
    base_dir = Path(__file__).parent
    config_dir = base_dir / 'configs'

    with open(config_dir / 'ga_params.json', 'r') as f:
        params_config = json.load(f)

    ga_params = params_config['ga_parameters']
    placement_config = params_config['placement']
    uma_checkpoint = params_config['uma_model']['checkpoint_path']

    # Header
    print(f"\n{'='*70}")
    print(f"🧬 GA OPTIMIZATION: {atom_config}")
    print(f"{'='*70}")
    print(f"Configuration: {atom_config}_{metal}_{slab}")
    print(f"Metal: {metal} ({n_metal} atoms)")
    print(f"Slab: {slab}")
    print(f"Output: {output_dir}")
    print(f"Device: {device}")
    print(f"{'='*70}\n")

    # Check if already completed
    summary_file = output_dir / f'{metal}_summary.json'
    if summary_file.exists():
        print(f"✓ Job already completed: {summary_file}")
        with open(summary_file, 'r') as f:
            return json.load(f)

    # Load UMA calculator
    uma_calc = load_uma_calculator(
        checkpoint_path=uma_checkpoint,
        device=device
    )

    # Load oxide slab
    oxide_slab = load_oxide_slab(slab)
    oxide_slab.info['material'] = slab

    # Update n_metal in params if different from config
    params_config['ga_parameters']['n_metal'] = n_metal

    # Run GA optimization
    results = run_single_ga(
        slab=oxide_slab,
        metal_symbol=metal,
        n_metal=n_metal,
        uma_calc=uma_calc,
        ga_params=ga_params,
        placement_config=placement_config,
        output_dir=output_dir
    )

    # Add atom configuration to results
    results['atom_config'] = atom_config
    results['n_oxide'] = n_oxide

    # Update summary file with new info
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"✅ OPTIMIZATION COMPLETE: {atom_config}_{metal}_{slab}")
    print(f"{'='*70}\n")

    return results


def run_campaign(campaign_file: str, max_jobs: int = None):
    """
    Run multiple GA jobs from campaign file

    Parameters:
    -----------
    campaign_file : str
        Path to campaign configuration file
    max_jobs : int
        Maximum number of jobs to run (None = all)

    Returns:
    --------
    results : list
        List of all job results
    """
    with open(campaign_file, 'r') as f:
        campaign = json.load(f)

    print(f"\n{'='*70}")
    print(f"🚀 GA CAMPAIGN: {campaign['campaign_id']}")
    print(f"{'='*70}")
    print(f"Total runs: {campaign['total_runs']}")
    if max_jobs:
        print(f"Running: {min(max_jobs, campaign['total_runs'])} jobs")
    print(f"{'='*70}\n")

    results = []
    runs = campaign['runs'][:max_jobs] if max_jobs else campaign['runs']

    for idx, run_config in enumerate(runs, 1):
        print(f"\n{'#'*70}")
        print(f"# JOB {idx}/{len(runs)}: {run_config['run_name']}")
        print(f"{'#'*70}\n")

        try:
            result = run_ga_job(**run_config)
            results.append(result)
        except Exception as e:
            print(f"❌ Error in {run_config['run_name']}: {e}")
            continue

    # Save campaign results
    campaign_results = {
        'campaign_id': campaign['campaign_id'],
        'completed_runs': len(results),
        'total_runs': len(runs),
        'results': results
    }

    results_file = Path(campaign_file).parent / f"{campaign['campaign_id']}_results.json"
    with open(results_file, 'w') as f:
        json.dump(campaign_results, f, indent=2)

    print(f"\n{'='*70}")
    print(f"✅ CAMPAIGN COMPLETE: {campaign['campaign_id']}")
    print(f"Completed: {len(results)}/{len(runs)} runs")
    print(f"Results: {results_file}")
    print(f"{'='*70}\n")

    return results


def main():
    parser = argparse.ArgumentParser(
        description='Run GA optimization with flexible configurations'
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        '--single', action='store_true',
        help='Run single GA job'
    )
    mode.add_argument(
        '--campaign', type=str,
        help='Run campaign from config file'
    )
    mode.add_argument(
        '--config', type=str,
        help='Run single job from config file'
    )

    # Single job parameters
    parser.add_argument('--metal', type=str, help='Metal symbol')
    parser.add_argument('--slab', type=str, help='Oxide slab name')
    parser.add_argument('--n-metal', type=int, help='Number of metal atoms')
    parser.add_argument('--n-oxide', type=int, default=0, help='Number of oxide atoms')
    parser.add_argument('--device', type=str, default='cuda', help='Device (cuda/cpu)')
    parser.add_argument('--output-dir', type=str, help='Output directory')

    # Campaign parameters
    parser.add_argument('--max-jobs', type=int, help='Maximum jobs to run in campaign')

    args = parser.parse_args()

    if args.campaign:
        # Run campaign
        run_campaign(args.campaign, args.max_jobs)

    elif args.config:
        # Run single job from config
        run_ga_job(args.config)

    elif args.single:
        # Run single job from command line
        if not all([args.metal, args.slab, args.n_metal]):
            print("❌ Error: --metal, --slab, and --n-metal required for single job")
            sys.exit(1)

        # Build kwargs, excluding None values
        kwargs = {
            'metal': args.metal,
            'slab': args.slab,
            'n_metal': args.n_metal,
            'n_oxide': args.n_oxide,
            'device': args.device
        }
        if args.output_dir is not None:
            kwargs['output_dir'] = args.output_dir

        run_ga_job(**kwargs)


if __name__ == '__main__':
    main()