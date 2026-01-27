#!/usr/bin/env python3
"""
GA Runner - Execute GA for single metal on ALL oxide slabs
Processes all 10 oxide slabs sequentially for one metal
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
        description='Run GA for single metal on all oxide slabs'
    )
    parser.add_argument(
        '--metal', type=str, required=True,
        choices=['Pt', 'Au', 'Pd', 'Rh', 'Ni', 'Ru', 'Os', 'Ir'],
        help='Metal element symbol'
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

    # All oxide slabs (small slab test set - 10 materials)
    ALL_SLABS = ['Al2O3', 'CaO', 'CeO2', 'MgO', 'SiO2', 'SnO2',
                 'TiO2_anatase', 'TiO2_rutile', 'ZnO', 'ZrO2']

    # Load configurations
    config_dir = Path(args.config_dir)

    with open(config_dir / 'metals_config.json', 'r') as f:
        metals_config = json.load(f)

    with open(config_dir / 'ga_params.json', 'r') as f:
        params_config = json.load(f)

    # Validate metal
    if args.metal not in metals_config['metals']:
        print(f"❌ Error: Metal '{args.metal}' not found in configuration")
        sys.exit(1)

    # Campaign header
    print(f"\n{'='*70}")
    print(f"🧬 GA CAMPAIGN: {args.metal} on ALL OXIDE SLABS")
    print(f"{'='*70}")
    print(f"Metal: {args.metal} ({args.n_metal} atoms)")
    print(f"Slabs: {len(ALL_SLABS)}")
    print(f"Total runs: {len(ALL_SLABS)}")
    print(f"Output: {args.output_base}")
    print(f"Device: {args.device}")
    print(f"{'='*70}\n")

    # Load UMA calculator once (reuse for all slabs)
    print("Loading UMA calculator (will be reused for all slabs)...")
    uma_calc = load_uma_calculator(
        checkpoint_path=params_config['uma_model']['checkpoint_path'],
        device=args.device
    )
    print()

    # Track results
    all_results = []
    start_campaign = datetime.now()

    # Process each slab
    for slab_idx, slab_name in enumerate(ALL_SLABS, 1):
        print(f"\n{'#'*70}")
        print(f"# SLAB {slab_idx}/{len(ALL_SLABS)}: {args.metal} on {slab_name}")
        print(f"{'#'*70}\n")

        # Setup output directory
        output_dir = Path(args.output_base) / f"{args.metal}_{slab_name}"

        # Check if already completed
        summary_file = output_dir / f"{args.metal}_summary.json"
        if summary_file.exists():
            print(f"⏭️  Skipping {args.metal}_{slab_name} (already completed)")
            with open(summary_file, 'r') as f:
                all_results.append(json.load(f))
            continue

        try:
            # Load oxide slab
            print(f"Loading oxide slab: {slab_name}...")
            slab = load_oxide_slab(slab_name)
            print()

            # Run GA
            print(f"Running GA optimization...")
            summary = run_single_ga(
                slab=slab,
                metal_symbol=args.metal,
                n_metal=args.n_metal,
                uma_calc=uma_calc,
                ga_params=params_config['ga_parameters'],
                placement_config=params_config['placement'],
                output_dir=output_dir
            )

            all_results.append(summary)
            print(f"✅ Completed: {args.metal} on {slab_name}")
            print(f"   Best energy: {summary['best_energy']:.4f} eV")

        except Exception as e:
            print(f"❌ Error processing {args.metal} on {slab_name}:")
            print(f"   {e}")
            import traceback
            traceback.print_exc()
            continue

    # Campaign summary
    end_campaign = datetime.now()
    total_duration = (end_campaign - start_campaign).total_seconds()

    print(f"\n{'='*70}")
    print(f"✅ CAMPAIGN COMPLETE: {args.metal}")
    print(f"{'='*70}")
    print(f"Completed: {len(all_results)}/{len(ALL_SLABS)} slabs")
    print(f"Total duration: {total_duration/3600:.2f} hours")

    if all_results:
        best_result = min(all_results, key=lambda r: r['best_energy'])
        print(f"\n🏆 Best result for {args.metal}:")
        print(f"   Slab: {best_result['slab']}")
        print(f"   Energy: {best_result['best_energy']:.4f} eV")
        print(f"   Per atom: {best_result['best_energy_per_metal']:.4f} eV/atom")

    # Save campaign summary
    campaign_summary = {
        'metal': args.metal,
        'n_metal': args.n_metal,
        'total_slabs': len(ALL_SLABS),
        'completed': len(all_results),
        'total_duration_hours': total_duration / 3600,
        'timestamp': start_campaign.isoformat(),
        'results': all_results
    }

    campaign_file = Path(args.output_base) / f"{args.metal}_campaign_summary.json"
    with open(campaign_file, 'w') as f:
        json.dump(campaign_summary, f, indent=2)

    print(f"\n Campaign summary: {campaign_file}")
    print(f"{'='*70}\n")

    return 0 if len(all_results) == len(ALL_SLABS) else 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
