#!/usr/bin/env python3
"""
Collect and Analyze GA Results
Aggregate results from all metal-on-oxide GA optimizations
"""

import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# Configuration
BASE_DIR = Path('/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA')
OUTPUT_BASE = BASE_DIR / 'output'
ANALYSIS_DIR = BASE_DIR / 'analysis'

METALS = ['Pt', 'Au', 'Pd', 'Rh', 'Ni', 'Ru', 'Os', 'Ir']
SLABS = ['Al2O3', 'CaO', 'CeO2', 'MgO', 'SiO2', 'SnO2',
         'TiO2_anatase', 'TiO2_rutile', 'ZnO', 'ZrO2']


def collect_all_results():
    """Collect results from all completed GA runs"""

    results = []

    print("="*70)
    print("COLLECTING GA RESULTS")
    print("="*70)
    print()

    for metal in METALS:
        for slab in SLABS:
            output_dir = OUTPUT_BASE / f'{metal}_{slab}'
            summary_file = output_dir / f'{metal}_summary.json'

            if summary_file.exists():
                with open(summary_file, 'r') as f:
                    data = json.load(f)

                results.append({
                    'metal': metal,
                    'slab': slab,
                    'combination': f'{metal}_{slab}',
                    'best_energy': data['best_energy'],
                    'energy_per_atom': data['best_energy_per_metal'],
                    'n_metal': data['n_metal'],
                    'generations': data['generations'],
                    'structures_evaluated': data['total_structures'],
                    'duration_hours': data['duration_hours'],
                    'timestamp': data['timestamp']
                })
                print(f"✓ {metal}_{slab}: {data['best_energy']:.4f} eV")
            else:
                print(f"⏭️  {metal}_{slab}: Not completed")

    print()
    print("="*70)
    print(f"Collected results: {len(results)}/{len(METALS)*len(SLABS)}")
    print("="*70)
    print()

    return results


def analyze_results(results):
    """Analyze collected results"""

    if not results:
        print("No results to analyze")
        return None

    df = pd.DataFrame(results)

    # Create analysis directory
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)

    # Save raw data
    csv_file = ANALYSIS_DIR / 'all_results.csv'
    df.to_csv(csv_file, index=False)
    print(f"✓ Saved: {csv_file}")

    # Overall statistics
    print("\n" + "="*70)
    print("OVERALL STATISTICS")
    print("="*70)
    print(f"Total completed: {len(df)}")
    print(f"Best overall: {df['best_energy'].min():.4f} eV")
    print(f"Best per atom: {df['energy_per_atom'].min():.4f} eV/atom")
    print(f"Average duration: {df['duration_hours'].mean():.2f} hours")
    print(f"Total GPU hours: {df['duration_hours'].sum():.2f} hours")

    # Best combination
    best_idx = df['best_energy'].idxmin()
    best = df.loc[best_idx]
    print(f"\nBest combination:")
    print(f"  {best['combination']}: {best['best_energy']:.4f} eV")
    print(f"  Per atom: {best['energy_per_atom']:.4f} eV/atom")

    # Analysis by metal
    print("\n" + "="*70)
    print("RESULTS BY METAL")
    print("="*70)

    metal_stats = df.groupby('metal').agg({
        'best_energy': ['min', 'mean', 'std'],
        'energy_per_atom': ['min', 'mean'],
        'duration_hours': 'mean'
    }).round(4)

    print(metal_stats.to_string())

    metal_stats.to_csv(ANALYSIS_DIR / 'metal_statistics.csv')
    print(f"\n✓ Saved: {ANALYSIS_DIR / 'metal_statistics.csv'}")

    # Analysis by slab
    print("\n" + "="*70)
    print("RESULTS BY SLAB")
    print("="*70)

    slab_stats = df.groupby('slab').agg({
        'best_energy': ['min', 'mean', 'std'],
        'energy_per_atom': ['min', 'mean'],
        'duration_hours': 'mean'
    }).round(4)

    print(slab_stats.to_string())

    slab_stats.to_csv(ANALYSIS_DIR / 'slab_statistics.csv')
    print(f"\n✓ Saved: {ANALYSIS_DIR / 'slab_statistics.csv'}")

    # Create pivot table
    pivot = df.pivot(index='metal', columns='slab', values='best_energy')
    pivot_file = ANALYSIS_DIR / 'energy_matrix.csv'
    pivot.to_csv(pivot_file)
    print(f"\n✓ Saved: {pivot_file}")

    # Best for each metal
    print("\n" + "="*70)
    print("BEST SLAB FOR EACH METAL")
    print("="*70)

    best_by_metal = df.loc[df.groupby('metal')['best_energy'].idxmin()]
    for _, row in best_by_metal.iterrows():
        print(f"{row['metal']:3s}: {row['slab']:15s} "
              f"E = {row['best_energy']:8.4f} eV "
              f"({row['energy_per_atom']:6.4f} eV/atom)")

    # Best for each slab
    print("\n" + "="*70)
    print("BEST METAL FOR EACH SLAB")
    print("="*70)

    best_by_slab = df.loc[df.groupby('slab')['best_energy'].idxmin()]
    for _, row in best_by_slab.iterrows():
        print(f"{row['slab']:15s}: {row['metal']:3s} "
              f"E = {row['best_energy']:8.4f} eV "
              f"({row['energy_per_atom']:6.4f} eV/atom)")

    # Summary report
    report = {
        'analysis_date': datetime.now().isoformat(),
        'total_jobs': len(METALS) * len(SLABS),
        'completed_jobs': len(df),
        'completion_rate': len(df) / (len(METALS) * len(SLABS)),
        'best_overall': {
            'combination': best['combination'],
            'metal': best['metal'],
            'slab': best['slab'],
            'energy': float(best['best_energy']),
            'energy_per_atom': float(best['energy_per_atom'])
        },
        'statistics': {
            'min_energy': float(df['best_energy'].min()),
            'max_energy': float(df['best_energy'].max()),
            'mean_energy': float(df['best_energy'].mean()),
            'std_energy': float(df['best_energy'].std()),
            'total_gpu_hours': float(df['duration_hours'].sum()),
            'avg_duration_hours': float(df['duration_hours'].mean())
        }
    }

    report_file = ANALYSIS_DIR / 'summary_report.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"\n✓ Saved: {report_file}")

    return df


def main():
    """Main analysis workflow"""

    # Collect results
    results = collect_all_results()

    if not results:
        print("No completed results found")
        return

    # Analyze
    df = analyze_results(results)

    print("\n" + "="*70)
    print("✅ ANALYSIS COMPLETE")
    print("="*70)
    print(f"Results directory: {ANALYSIS_DIR}")
    print(f"Files created:")
    print(f"  - all_results.csv: Raw data")
    print(f"  - metal_statistics.csv: Statistics by metal")
    print(f"  - slab_statistics.csv: Statistics by slab")
    print(f"  - energy_matrix.csv: Pivot table")
    print(f"  - summary_report.json: Summary report")
    print("="*70)
    print()


if __name__ == '__main__':
    main()
