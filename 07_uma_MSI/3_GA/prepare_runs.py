#!/usr/bin/env python3
"""
Flexible Run Configuration Generator
Supports different numbers of metal atoms with MxOy naming convention
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict

# Base configuration
BASE_DIR = Path(__file__).parent
CONFIGS_DIR = BASE_DIR / 'configs'

# Default metals and slabs
DEFAULT_METALS = ['Pt', 'Au', 'Pd', 'Rh', 'Ni', 'Ru', 'Os', 'Ir']
DEFAULT_SLABS = [
    'Al2O3', 'CaO', 'CeO2', 'MgO', 'SiO2',
    'SnO2', 'TiO2_anatase', 'TiO2_rutile', 'ZnO', 'ZrO2'
]


def create_run_config(
    metal: str,
    slab: str,
    n_metal: int,
    n_oxide: int = 0,
    base_dir: Path = None
) -> Dict:
    """
    Create a single run configuration

    Parameters:
    -----------
    metal : str
        Metal element symbol
    slab : str
        Oxide slab name
    n_metal : int
        Number of metal atoms
    n_oxide : int
        Number of additional oxide atoms (default 0)
    base_dir : Path
        Base directory for output

    Returns:
    --------
    config : dict
        Run configuration
    """
    if base_dir is None:
        base_dir = BASE_DIR

    # Create MxOy naming
    atom_config = f"M{n_metal}"
    if n_oxide > 0:
        atom_config += f"O{n_oxide}"

    # Output directory using flat structure
    output_dir = base_dir / f"runs_{atom_config}" / f"{metal}_{slab}"

    config = {
        'metal': metal,
        'slab': slab,
        'n_metal': n_metal,
        'n_oxide': n_oxide,
        'atom_config': atom_config,
        'run_name': f"{atom_config}_{metal}_{slab}",
        'output_dir': str(output_dir),
        'log_file': str(base_dir / 'logs' / f"{atom_config}_{metal}_{slab}.log")
    }

    return config


def generate_campaign(
    metals: List[str],
    slabs: List[str],
    n_metal: int,
    n_oxide: int = 0,
    output_file: str = None
) -> Dict:
    """
    Generate campaign configuration for multiple runs

    Parameters:
    -----------
    metals : list
        List of metal symbols
    slabs : list
        List of oxide slab names
    n_metal : int
        Number of metal atoms
    n_oxide : int
        Number of additional oxide atoms
    output_file : str
        Output file for campaign config

    Returns:
    --------
    campaign : dict
        Campaign configuration
    """
    runs = []

    for metal in metals:
        for slab in slabs:
            run_config = create_run_config(metal, slab, n_metal, n_oxide)
            runs.append(run_config)

    campaign = {
        'campaign_id': f"M{n_metal}O{n_oxide}",
        'n_metal': n_metal,
        'n_oxide': n_oxide,
        'metals': metals,
        'slabs': slabs,
        'total_runs': len(runs),
        'runs': runs
    }

    if output_file:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(campaign, f, indent=2)
        print(f"✓ Campaign saved to: {output_path}")

    return campaign


def main():
    parser = argparse.ArgumentParser(
        description='Generate GA run configurations with flexible atom numbers'
    )
    parser.add_argument(
        '--n-metal', type=int, required=True,
        help='Number of metal atoms (e.g., 30, 45, 60)'
    )
    parser.add_argument(
        '--n-oxide', type=int, default=0,
        help='Number of additional oxide atoms (default: 0)'
    )
    parser.add_argument(
        '--metals', type=str, nargs='+',
        default=DEFAULT_METALS,
        help='Metal symbols to include'
    )
    parser.add_argument(
        '--slabs', type=str, nargs='+',
        default=DEFAULT_SLABS,
        help='Oxide slabs to include'
    )
    parser.add_argument(
        '--single', action='store_true',
        help='Generate single run config instead of campaign'
    )
    parser.add_argument(
        '--metal', type=str,
        help='Single metal for individual run'
    )
    parser.add_argument(
        '--slab', type=str,
        help='Single slab for individual run'
    )
    parser.add_argument(
        '--output', type=str,
        help='Output file path'
    )

    args = parser.parse_args()

    print(f"\n{'='*70}")
    print(f"GA RUN CONFIGURATION GENERATOR")
    print(f"{'='*70}")

    if args.single:
        # Generate single run configuration
        if not args.metal or not args.slab:
            print("❌ Error: --metal and --slab required for single run")
            return

        config = create_run_config(
            args.metal, args.slab, args.n_metal, args.n_oxide
        )

        print(f"Run configuration: {config['run_name']}")
        print(f"  Metal: {args.metal} ({args.n_metal} atoms)")
        print(f"  Slab: {args.slab}")
        print(f"  Output: {config['output_dir']}")

        if args.output:
            with open(args.output, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✓ Config saved to: {args.output}")
        else:
            print(json.dumps(config, indent=2))

    else:
        # Generate campaign configuration
        campaign = generate_campaign(
            args.metals, args.slabs, args.n_metal, args.n_oxide,
            args.output
        )

        atom_config = f"M{args.n_metal}O{args.n_oxide}"
        print(f"Campaign: {atom_config}")
        print(f"  Metals: {len(args.metals)} - {', '.join(args.metals)}")
        print(f"  Slabs: {len(args.slabs)} - {', '.join(args.slabs[:3])}...")
        print(f"  Total runs: {campaign['total_runs']}")
        print(f"  Output structure: runs_{atom_config}/{{metal}}_{{slab}}/")

        # Create directory structure
        for run in campaign['runs'][:3]:  # Show first 3 as examples
            print(f"    → {run['run_name']}")
        if len(campaign['runs']) > 3:
            print(f"    ... and {len(campaign['runs']) - 3} more")

    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()