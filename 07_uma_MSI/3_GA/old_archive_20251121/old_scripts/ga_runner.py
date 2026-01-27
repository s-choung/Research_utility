#!/usr/bin/env python3
"""
GA Runner - Execute GA for single metal-slab combination
Reads job configuration and runs optimization
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# Import main GA functions
sys.path.insert(0, str(Path(__file__).parent))
from ga_metal_oxide import (
    load_oxide_slab, load_uma_calculator, run_single_ga
)


def main():
    parser = argparse.ArgumentParser(
        description='Run GA for metal deposition on oxide slab'
    )
    parser.add_argument(
        '--metal', type=str, required=True,
        choices=['Pt', 'Au', 'Pd', 'Rh', 'Ni', 'Ru', 'Os', 'Ir'],
        help='Metal element symbol'
    )
    parser.add_argument(
        '--slab', type=str, required=True,
        choices=['Al2O3', 'CaO', 'CeO2', 'MgO', 'SiO2', 'SnO2',
                'TiO2_anatase', 'TiO2_rutile', 'ZnO', 'ZrO2'],
        help='Oxide slab name'
    )
    parser.add_argument(
        '--n-metal', type=int, default=45,
        help='Number of metal atoms to deposit (default: 45)'
    )
    parser.add_argument(
        '--config-dir', type=str,
        default='/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA/configs',
        help='Configuration directory'
    )
    parser.add_argument(
        '--output-base', type=str,
        default='/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA/output',
        help='Base output directory'
    )
    parser.add_argument(
        '--device', type=str, choices=['cuda', 'cpu'], default='cuda',
        help='Device to use for UMA'
    )
    args = parser.parse_args()

    # Load configurations
    config_dir = Path(args.config_dir)

    with open(config_dir / 'metals_config.json', 'r') as f:
        metals_config = json.load(f)

    with open(config_dir / 'slabs_config.json', 'r') as f:
        slabs_config = json.load(f)

    with open(config_dir / 'ga_params.json', 'r') as f:
        params_config = json.load(f)

    # Validate metal
    if args.metal not in metals_config['metals']:
        print(f"❌ Error: Metal '{args.metal}' not found in configuration")
        sys.exit(1)

    # Validate slab
    if args.slab not in slabs_config['slabs']:
        print(f"❌ Error: Slab '{args.slab}' not found in configuration")
        sys.exit(1)

    # Setup output directory
    output_dir = Path(args.output_base) / f"{args.metal}_{args.slab}"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Header
    print(f"\n{'='*70}")
    print(f"🧬 GA OPTIMIZATION JOB")
    print(f"{'='*70}")
    print(f"Metal: {args.metal} ({args.n_metal} atoms)")
    print(f"Slab: {args.slab}")
    print(f"Output: {output_dir}")
    print(f"Device: {args.device}")
    print(f"{'='*70}\n")

    # Check if already completed
    summary_file = output_dir / f"{args.metal}_summary.json"
    if summary_file.exists():
        print(f"⏭️  Job already completed!")
        print(f"   Summary: {summary_file}")
        with open(summary_file, 'r') as f:
            prev_summary = json.load(f)
        print(f"   Best energy: {prev_summary['best_energy']:.4f} eV")
        print(f"   Duration: {prev_summary['duration_hours']:.2f} hours")
        print(f"\nTo rerun, delete: {summary_file}\n")
        sys.exit(0)

    # Load oxide slab
    print("Step 1: Loading oxide slab...")
    slab = load_oxide_slab(args.slab)

    # Load UMA calculator
    print("\nStep 2: Loading UMA calculator...")
    uma_calc = load_uma_calculator(
        checkpoint_path=params_config['uma_model']['checkpoint_path'],
        device=args.device
    )

    # Run GA
    print("\nStep 3: Running GA optimization...")
    start_campaign = datetime.now()

    try:
        summary = run_single_ga(
            slab=slab,
            metal_symbol=args.metal,
            n_metal=args.n_metal,
            uma_calc=uma_calc,
            ga_params=params_config['ga_parameters'],
            placement_config=params_config['placement'],
            output_dir=output_dir
        )

        # Final report
        end_campaign = datetime.now()
        total_duration = (end_campaign - start_campaign).total_seconds()

        print(f"\n{'='*70}")
        print(f"✅ JOB COMPLETE")
        print(f"{'='*70}")
        print(f"Metal: {args.metal} ({args.n_metal} atoms)")
        print(f"Slab: {args.slab}")
        print(f"Best energy: {summary['best_energy']:.4f} eV")
        print(f"Per metal atom: {summary['best_energy_per_metal']:.4f} eV/atom")
        print(f"Total duration: {total_duration/3600:.2f} hours")
        print(f"Structures evaluated: {summary['total_structures']}")
        print(f"Output directory: {output_dir}")
        print(f"{'='*70}\n")

        return 0

    except Exception as e:
        print(f"\n❌ ERROR during GA execution:")
        print(f"{e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
