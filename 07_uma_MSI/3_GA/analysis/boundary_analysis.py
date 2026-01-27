"""
Analyze support size vs metal distribution to check periodic boundary interactions.
"""
import json
import numpy as np
from pathlib import Path
from ase.io import read
import matplotlib.pyplot as plt

def analyze_boundary_clearance(atoms, metal_symbol):
    """Analyze metal positions relative to cell boundaries."""
    cell = atoms.get_cell()
    a, b = np.linalg.norm(cell[0]), np.linalg.norm(cell[1])

    # Get metal positions (fractional)
    metal_idx = [i for i, s in enumerate(atoms.symbols) if s == metal_symbol]
    if not metal_idx:
        return None

    positions = atoms.positions[metal_idx]
    frac = atoms.get_scaled_positions()[metal_idx]

    # Metal cluster metrics
    xy_center = positions[:, :2].mean(axis=0)
    xy_spread = positions[:, :2].std(axis=0)
    xy_range = np.ptp(positions[:, :2], axis=0)  # max - min

    # Distance to boundaries (in fractional coords, 0 and 1 are boundaries)
    dist_to_0 = frac[:, :2].min(axis=0)  # min distance to x=0, y=0
    dist_to_1 = 1 - frac[:, :2].max(axis=0)  # min distance to x=1, y=1
    min_boundary_dist = np.minimum(dist_to_0, dist_to_1)

    # Convert to Angstroms
    min_boundary_dist_A = min_boundary_dist * np.array([a, b])

    # Check if any metal-metal distance crosses boundary (via minimum image)
    from ase.geometry import get_distances
    _, d_mic = get_distances(positions, positions, cell=cell, pbc=[True, True, False])
    d_no_mic = np.linalg.norm(positions[:, None, :] - positions[None, :, :], axis=-1)

    # If MIC distance < direct distance, interaction crosses boundary
    np.fill_diagonal(d_mic, np.inf)
    np.fill_diagonal(d_no_mic, np.inf)
    boundary_crossing = (d_mic < d_no_mic - 0.1).any()

    return {
        'cell_a': a, 'cell_b': b,
        'n_metal': len(metal_idx),
        'xy_spread': xy_spread.tolist(),
        'xy_range': xy_range.tolist(),
        'min_boundary_dist_frac': min_boundary_dist.tolist(),
        'min_boundary_dist_A': min_boundary_dist_A.tolist(),
        'boundary_crossing': boundary_crossing,
        'cluster_diameter': xy_range.max(),
        'cell_min_dim': min(a, b),
        'coverage_ratio': xy_range.max() / min(a, b)
    }

def main():
    base = Path("/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA/runs_M40")
    results = []

    for run_dir in sorted(base.iterdir()):
        if not run_dir.is_dir():
            continue

        metal = run_dir.name.split("_")[0]
        slab = "_".join(run_dir.name.split("_")[1:])

        # Find best structure
        best_file = run_dir / f"{metal}_best.xyz"
        if not best_file.exists():
            continue

        atoms = read(best_file)
        analysis = analyze_boundary_clearance(atoms, metal)
        if analysis:
            analysis['metal'] = metal
            analysis['slab'] = slab
            results.append(analysis)

    # Summary table
    print(f"{'Metal':<4} {'Slab':<8} {'Cell(Å)':<12} {'Spread(Å)':<14} {'Range(Å)':<14} {'Boundary(Å)':<12} {'Cover%':<8} {'Cross'}")
    print("=" * 95)

    boundary_issues = []
    for r in sorted(results, key=lambda x: -x['coverage_ratio']):
        cell_str = f"{r['cell_a']:.1f}x{r['cell_b']:.1f}"
        spread_str = f"{r['xy_spread'][0]:.1f}, {r['xy_spread'][1]:.1f}"
        range_str = f"{r['xy_range'][0]:.1f}, {r['xy_range'][1]:.1f}"
        bound_str = f"{min(r['min_boundary_dist_A']):.1f}"
        cover_pct = r['coverage_ratio'] * 100
        cross = "⚠️ YES" if r['boundary_crossing'] else "no"

        print(f"{r['metal']:<4} {r['slab']:<8} {cell_str:<12} {spread_str:<14} {range_str:<14} {bound_str:<12} {cover_pct:<8.1f} {cross}")

        if r['boundary_crossing'] or r['coverage_ratio'] > 0.7:
            boundary_issues.append(r)

    # Summary stats
    print("\n" + "=" * 95)
    coverages = [r['coverage_ratio'] for r in results]
    crossings = sum(1 for r in results if r['boundary_crossing'])
    print(f"Coverage ratio: {np.mean(coverages)*100:.1f}% ± {np.std(coverages)*100:.1f}% (max: {np.max(coverages)*100:.1f}%)")
    print(f"Boundary crossings: {crossings}/{len(results)} ({100*crossings/len(results):.0f}%)")

    if boundary_issues:
        print(f"\n⚠️  {len(boundary_issues)} cases with potential boundary issues (coverage>70% or crossing):")
        for r in boundary_issues:
            print(f"   {r['metal']}_{r['slab']}: coverage={r['coverage_ratio']*100:.0f}%, crossing={r['boundary_crossing']}")

    # Plot
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))

    # Coverage distribution
    axes[0].hist(np.array(coverages)*100, bins=15, edgecolor='black', alpha=0.7)
    axes[0].axvline(70, color='r', linestyle='--', label='70% threshold')
    axes[0].set_xlabel('Coverage Ratio (%)')
    axes[0].set_ylabel('Count')
    axes[0].set_title('Cluster Size / Cell Size')
    axes[0].legend()

    # By slab type
    slabs = list(set(r['slab'] for r in results))
    slab_coverages = {s: [r['coverage_ratio']*100 for r in results if r['slab'] == s] for s in slabs}
    axes[1].boxplot([slab_coverages[s] for s in sorted(slabs)], labels=sorted(slabs))
    axes[1].set_ylabel('Coverage Ratio (%)')
    axes[1].set_title('Coverage by Support')
    axes[1].tick_params(axis='x', rotation=45)
    axes[1].axhline(70, color='r', linestyle='--', alpha=0.5)

    # Boundary distance vs cell size
    min_bounds = [min(r['min_boundary_dist_A']) for r in results]
    cell_sizes = [r['cell_min_dim'] for r in results]
    colors = ['red' if r['boundary_crossing'] else 'blue' for r in results]
    axes[2].scatter(cell_sizes, min_bounds, c=colors, alpha=0.6)
    axes[2].set_xlabel('Cell Min Dimension (Å)')
    axes[2].set_ylabel('Min Boundary Distance (Å)')
    axes[2].set_title('Boundary Clearance')
    axes[2].axhline(3, color='r', linestyle='--', alpha=0.5, label='3Å threshold')
    axes[2].legend()

    plt.tight_layout()
    plt.savefig(base.parent / 'analysis' / 'boundary_analysis.png', dpi=150)
    print(f"\nPlot saved: analysis/boundary_analysis.png")

if __name__ == "__main__":
    main()
