#!/usr/bin/env python3
"""
Large Slab Generation for GA - Metal Oxide Surfaces
Generates thin slabs (~8Å, 3-4 layers) with xy≥50Å and relaxation.
"""

from ase.spacegroup import crystal
from ase.io import read, write
from ase.constraints import FixAtoms, ExpCellFilter
from ase.optimize import LBFGS
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.ase import AseAtomsAdaptor
import numpy as np
import os
import sys
import torch

# ============================================================================
# Configuration
# ============================================================================

OUTPUT_DIR = "./slabs_large"
LOG_DIR = "./logs"
TARGET_XY_MIN = 35.0  # Reduced for faster relaxation
TARGET_VACUUM = 15.0
TARGET_BUFFER = 2.0
MIN_SLAB_THICKNESS = 8.0  # Thin slabs for fewer atoms

# Relaxation settings
ENABLE_RELAXATION = True
CHECKPOINT_PATH = "../utility/uma-s-1p1.pt"
FMAX = 0.05  # eV/Å
MAX_STEPS = 300

# ============================================================================
# Bulk Structure Definitions
# ============================================================================

# Rock salt (MgO, CaO)
a_mgo = 4.212
mgo_bulk = crystal(['Mg', 'O'], basis=[(0, 0, 0), (0.5, 0.5, 0.5)],
                   spacegroup=225, cellpar=[a_mgo]*3 + [90]*3)

a_cao = 4.810
cao_bulk = crystal(['Ca', 'O'], basis=[(0, 0, 0), (0.5, 0.5, 0.5)],
                   spacegroup=225, cellpar=[a_cao]*3 + [90]*3)

# Fluorite (CeO2)
a_ceo2 = 5.411
ceo2_bulk = crystal(['Ce', 'O'], basis=[(0, 0, 0), (0.25, 0.25, 0.25)],
                    spacegroup=225, cellpar=[a_ceo2]*3 + [90]*3)

# Rutile (TiO2, SnO2)
a_tio2, c_tio2 = 4.594, 2.959
tio2_rutile_bulk = crystal(['Ti', 'O'], basis=[(0, 0, 0), (0.3, 0.3, 0.0)],
                           spacegroup=136, cellpar=[a_tio2, a_tio2, c_tio2, 90, 90, 90])

a_sno2, c_sno2 = 4.737, 3.186
sno2_bulk = crystal(['Sn', 'O'], basis=[(0, 0, 0), (0.306, 0.306, 0.0)],
                    spacegroup=136, cellpar=[a_sno2, a_sno2, c_sno2, 90, 90, 90])

# Anatase (TiO2)
a_anatase, c_anatase = 3.785, 9.514
tio2_anatase_bulk = crystal(['Ti', 'O'], basis=[(0, 0, 0), (0, 0, 0.208)],
                            spacegroup=141, cellpar=[a_anatase, a_anatase, c_anatase, 90, 90, 90])

# Wurtzite (ZnO)
a_zno, c_zno = 3.250, 5.207
zno_bulk = crystal(['Zn', 'O'], basis=[(1/3, 2/3, 0), (1/3, 2/3, 0.382)],
                   spacegroup=186, cellpar=[a_zno, a_zno, c_zno, 90, 90, 120])

# Corundum (Al2O3)
a_al2o3, c_al2o3 = 4.759, 12.991
al2o3_bulk = crystal(['Al', 'O'], basis=[(0, 0, 0.352), (0.306, 0, 0.25)],
                     spacegroup=167, cellpar=[a_al2o3, a_al2o3, c_al2o3, 90, 90, 120])

# Monoclinic ZrO2
a_zro2, b_zro2, c_zro2, beta_zro2 = 5.150, 5.212, 5.317, 99.23
zro2_bulk = crystal(['Zr', 'O'], basis=[(0.276, 0.041, 0.208), (0.070, 0.332, 0.341)],
                    spacegroup=14, cellpar=[a_zro2, b_zro2, c_zro2, 90, beta_zro2, 90])

# Alpha-quartz (SiO2)
a_sio2, c_sio2 = 4.916, 5.405
sio2_bulk = crystal(['Si', 'O'], basis=[(0.470, 0, 2/3), (0.415, 0.272, 0.785)],
                    spacegroup=154, cellpar=[a_sio2, a_sio2, c_sio2, 90, 90, 120])

# ============================================================================
# Material configurations: (name, bulk, miller, term_idx, target_supercell)
# Target supercell chosen to get xy~50Å with atoms<2000
# ============================================================================

MATERIALS = [
    # name, bulk, miller_index, preferred_term, (nx, ny) for ~50Å
    ("Al2O3_001", al2o3_bulk, (0, 0, 1), 0, (12, 12)),  # 4.76*12=57Å
    ("CaO_100", cao_bulk, (1, 0, 0), 0, (11, 11)),       # 4.81*11=53Å
    ("CeO2_111", ceo2_bulk, (1, 1, 1), 1, (9, 9)),       # 5.41*1.41*9/3=57Å
    ("MgO_100", mgo_bulk, (1, 0, 0), 0, (12, 12)),       # 4.21*12=51Å
    ("SiO2_101", sio2_bulk, (1, 0, 1), 0, (10, 8)),      # Need to find best
    ("SnO2_100", sno2_bulk, (1, 0, 0), 1, (11, 16)),     # 4.74*11=52Å, 3.19*16=51Å
    ("TiO2_anatase_001", tio2_anatase_bulk, (0, 0, 1), 1, (14, 14)),  # 3.79*14=53Å
    ("TiO2_rutile_100", tio2_rutile_bulk, (1, 0, 0), 1, (11, 17)),    # 4.59*11=50Å, 2.96*17=50Å
    ("ZnO_100", zno_bulk, (1, 0, 0), 0, (10, 10)),       # 3.25*1.73*10=56Å
    ("ZrO2_100", zro2_bulk, (1, 0, 0), 1, (10, 10)),     # 5.15*10=52Å
]

# ============================================================================
# FairChem Calculator
# ============================================================================

def load_fairchem_calculator(checkpoint_path):
    """Load FairChem v2 calculator."""
    from fairchem.core import FAIRChemCalculator, pretrained_mlip

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Loading FairChem calculator on {device}...")

    predict_unit = pretrained_mlip.load_predict_unit(
        path=checkpoint_path,
        inference_settings="default",
        device=device
    )
    calc = FAIRChemCalculator(predict_unit, task_name="oc20")
    print("  ✓ Calculator loaded")
    return calc


def relax_bulk(bulk, calculator, fmax=0.01, steps=200):
    """
    Relax bulk structure with volume/cell optimization using ExpCellFilter.
    Returns relaxed bulk structure.
    """
    bulk = bulk.copy()
    bulk.calc = calculator
    bulk.set_pbc([True, True, True])

    # Get initial state
    E_init = bulk.get_potential_energy()
    cell_init = bulk.get_cell()
    V_init = bulk.get_volume()

    print(f"    Initial: E={E_init:.3f} eV, V={V_init:.2f} Å³", flush=True)
    print(f"    Cell: a={np.linalg.norm(cell_init[0]):.3f}, b={np.linalg.norm(cell_init[1]):.3f}, c={np.linalg.norm(cell_init[2]):.3f} Å", flush=True)

    # Use ExpCellFilter for volume relaxation
    ecf = ExpCellFilter(bulk)
    opt = LBFGS(ecf, logfile='-')
    converged = opt.run(fmax=fmax, steps=steps)

    # Get final state
    E_final = bulk.get_potential_energy()
    cell_final = bulk.get_cell()
    V_final = bulk.get_volume()

    print(f"    Final: E={E_final:.3f} eV, V={V_final:.2f} Å³, steps={opt.nsteps}", flush=True)
    print(f"    Cell: a={np.linalg.norm(cell_final[0]):.3f}, b={np.linalg.norm(cell_final[1]):.3f}, c={np.linalg.norm(cell_final[2]):.3f} Å", flush=True)
    print(f"    ΔV={V_final - V_init:.2f} Å³ ({100*(V_final-V_init)/V_init:.1f}%), Converged={converged}", flush=True)

    return bulk, converged


def relax_slab(slab, calculator, fmax=0.05, steps=300):
    """Relax slab with LBFGS optimizer."""
    slab.calc = calculator

    # Pre-check: verify structure is reasonable
    E_init = slab.get_potential_energy()
    forces = slab.get_forces()
    fmax_init = np.max(np.linalg.norm(forces, axis=1))

    print(f"    Initial: E={E_init:.3f} eV, Fmax={fmax_init:.3f} eV/Å", flush=True)

    # Optimize with progress output to stdout
    opt = LBFGS(slab, logfile='-')  # '-' means stdout
    converged = opt.run(fmax=fmax, steps=steps)

    # Get final state
    E_final = slab.get_potential_energy()
    forces = slab.get_forces()
    fmax_final = np.max(np.linalg.norm(forces, axis=1))

    print(f"    Final: E={E_final:.3f} eV, Fmax={fmax_final:.3f} eV/Å, steps={opt.nsteps}", flush=True)
    print(f"    ΔE={E_final - E_init:.3f} eV, Converged={converged}", flush=True)

    return slab, E_init, E_final, converged


# ============================================================================
# Helper Functions
# ============================================================================

def generate_thin_slab(bulk, miller_index, min_thickness=8.0, vacuum=15.0):
    """
    Generate a thin slab with specified Miller index.
    Returns all terminations.
    """
    pmg_structure = AseAtomsAdaptor.get_structure(bulk)

    slab_gen = SlabGenerator(
        initial_structure=pmg_structure,
        miller_index=miller_index,
        min_slab_size=min_thickness,
        min_vacuum_size=vacuum,
        lll_reduce=True,  # Reduce to more orthogonal cell
        center_slab=False,
        primitive=True,
        max_normal_search=max(miller_index) + 1,
    )

    slabs = slab_gen.get_slabs(tol=0.3, bonds=None, max_broken_bonds=0, symmetrize=False)

    if len(slabs) == 0:
        raise ValueError(f"No valid slab for Miller {miller_index}")

    return slabs


def make_orthogonal_supercell(slab_pmg, nx, ny):
    """
    Create supercell and convert to orthogonal cell if needed.
    """
    # Make supercell in pymatgen
    slab_pmg.make_supercell([nx, ny, 1])

    # Convert to ASE
    slab = AseAtomsAdaptor.get_atoms(slab_pmg)

    return slab


def optimize_z_and_pbc(slab, vacuum=15.0, buffer=2.0):
    """
    Position slab at bottom with proper vacuum, set PBC.
    """
    temp = slab.copy()
    positions = temp.get_positions()
    z_coords = positions[:, 2]
    min_z, max_z = np.min(z_coords), np.max(z_coords)

    # Shift to bottom
    positions[:, 2] -= min_z
    positions[:, 2] += buffer
    temp.set_positions(positions)

    # Set cell height
    slab_thickness = max_z - min_z
    cell = temp.get_cell().copy()
    cell[2, 2] = slab_thickness + buffer + vacuum
    temp.set_cell(cell, scale_atoms=False)

    # Set PBC - True for all dimensions (required for FairChem)
    temp.set_pbc([True, True, True])

    return temp, slab_thickness


def fix_bottom_half(slab):
    """Fix bottom half of atoms."""
    temp = slab.copy()
    symbols = temp.get_chemical_symbols()
    metals = [el for el in set(symbols) if el != 'O']

    if not metals:
        return temp

    metal = metals[0] if len(metals) == 1 else max(metals, key=lambda m: symbols.count(m))
    metal_z = np.array([a.position[2] for a in temp if a.symbol == metal])

    if len(metal_z) == 0:
        return temp

    median_z = np.median(metal_z)
    mask = temp.positions[:, 2] < median_z
    temp.set_constraint(FixAtoms(mask=mask))

    return temp


def get_slab_info(slab):
    """Get slab dimensions and composition."""
    cell = slab.get_cell()
    pos = slab.get_positions()

    a = np.linalg.norm(cell[0])
    b = np.linalg.norm(cell[1])
    c = cell[2, 2]

    z = pos[:, 2]
    thick = np.max(z) - np.min(z)
    vac = c - np.max(z)

    syms = slab.get_chemical_symbols()
    comp = {}
    for s in syms:
        comp[s] = comp.get(s, 0) + 1

    return {'a': a, 'b': b, 'c': c, 'thick': thick, 'vacuum': vac,
            'n_atoms': len(slab), 'composition': comp}


# ============================================================================
# Main
# ============================================================================

def main():
    print("=" * 80)
    print(f"LARGE SLAB GENERATION FOR GA (xy~{TARGET_XY_MIN}Å, with relaxation)")
    print("=" * 80)

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    # Load calculator for relaxation
    calculator = None
    if ENABLE_RELAXATION:
        if os.path.exists(CHECKPOINT_PATH):
            try:
                calculator = load_fairchem_calculator(CHECKPOINT_PATH)
            except Exception as e:
                print(f"  WARNING: Failed to load calculator: {e}")
                print("  Continuing without relaxation...")
        else:
            print(f"  WARNING: Checkpoint not found at {CHECKPOINT_PATH}")
            print("  Continuing without relaxation...")

    # =========================================================================
    # STEP 1: Relax all bulk structures first
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 1: BULK RELAXATION (with volume optimization)")
    print("=" * 80)

    relaxed_bulks = {}
    unique_bulks = {}  # key: id(bulk) -> (base_name, bulk)
    for name, bulk, miller, pref_term, (nx, ny) in MATERIALS:
        # Extract base material name (e.g., "Al2O3" from "Al2O3_001")
        base_name = name.rsplit('_', 1)[0]
        bulk_id = id(bulk)
        if bulk_id not in unique_bulks:
            unique_bulks[bulk_id] = (base_name, bulk)

    for bulk_id, (base_name, bulk) in unique_bulks.items():
        print(f"\n{'-'*60}", flush=True)
        print(f"Relaxing bulk: {base_name}", flush=True)

        if calculator is not None:
            try:
                relaxed_bulk, conv = relax_bulk(bulk, calculator, fmax=0.01, steps=200)
                relaxed_bulks[bulk_id] = relaxed_bulk
                print(f"  ✓ Bulk relaxed: {base_name}", flush=True)
            except Exception as e:
                print(f"  WARNING: Bulk relaxation failed: {e}", flush=True)
                relaxed_bulks[bulk_id] = bulk  # Use original
        else:
            relaxed_bulks[bulk_id] = bulk  # Use original

    # =========================================================================
    # STEP 2: Generate slabs from relaxed bulks
    # =========================================================================
    print("\n" + "=" * 80)
    print("STEP 2: SLAB GENERATION FROM RELAXED BULKS")
    print("=" * 80)

    results = []

    for name, bulk, miller, pref_term, (nx, ny) in MATERIALS:
        # Use relaxed bulk
        bulk_to_use = relaxed_bulks.get(id(bulk), bulk)
        print(f"\n{'-'*60}", flush=True)
        print(f"Processing: {name}", flush=True)
        print(f"  Miller: {miller}", flush=True)

        try:
            # Generate thin slab from relaxed bulk
            slabs_pmg = generate_thin_slab(bulk_to_use, miller, min_thickness=MIN_SLAB_THICKNESS)
            print(f"  Generated {len(slabs_pmg)} terminations")

            # Select termination
            term_idx = min(pref_term, len(slabs_pmg) - 1)
            slab_pmg = slabs_pmg[term_idx]

            # Get primitive cell info
            prim_slab = AseAtomsAdaptor.get_atoms(slab_pmg)
            prim_info = get_slab_info(prim_slab)
            print(f"  Primitive: {prim_info['a']:.1f}×{prim_info['b']:.1f}Å, {prim_info['n_atoms']} atoms, thick={prim_info['thick']:.1f}Å")

            # Calculate optimal supercell to target ~50×50 Å surface area
            base_atoms = prim_info['n_atoms']
            base_a, base_b = prim_info['a'], prim_info['b']

            # Find nx, ny that gives closest to TARGET_XY (50Å) in both dimensions
            best_scale = None
            best_score = float('inf')
            for test_nx in range(1, 30):
                for test_ny in range(1, 30):
                    fa, fb = base_a * test_nx, base_b * test_ny
                    # Score: how far from target 50×50
                    score = abs(fa - TARGET_XY_MIN) + abs(fb - TARGET_XY_MIN)
                    # Penalize if too small
                    if fa < TARGET_XY_MIN * 0.9 or fb < TARGET_XY_MIN * 0.9:
                        score += 100
                    atoms = base_atoms * test_nx * test_ny
                    if score < best_score:
                        best_score = score
                        best_scale = (test_nx, test_ny, fa, fb, min(fa, fb), atoms)

            if best_scale is None:
                print(f"  ERROR: Cannot find suitable scaling")
                continue

            nx, ny, final_a, final_b, min_xy, final_atoms = best_scale
            print(f"  Optimal scale: {nx}×{ny} → {final_a:.0f}×{final_b:.0f}Å, {final_atoms} atoms")

            # Make supercell
            slab_pmg_copy = slab_pmg.copy()
            slab = make_orthogonal_supercell(slab_pmg_copy, nx, ny)

            # Optimize z and PBC
            slab, thick = optimize_z_and_pbc(slab, vacuum=TARGET_VACUUM, buffer=TARGET_BUFFER)

            # Fix bottom atoms
            slab = fix_bottom_half(slab)

            # Get final info
            info = get_slab_info(slab)
            print(f"  Final: {info['a']:.1f}×{info['b']:.1f}×{info['c']:.1f}Å")
            print(f"  Slab thickness: {info['thick']:.1f}Å, Atoms: {info['n_atoms']}")
            print(f"  Composition: {info['composition']}")

            # Relaxation
            E_init, E_final, converged = None, None, False
            if calculator is not None:
                print(f"  Relaxing {info['n_atoms']} atoms...")
                try:
                    slab, E_init, E_final, converged = relax_slab(
                        slab, calculator, fmax=FMAX, steps=MAX_STEPS
                    )
                    # Update info after relaxation
                    info = get_slab_info(slab)
                except Exception as e:
                    print(f"  WARNING: Relaxation failed: {e}")

            # Status
            status = "✓" if converged else ("no_relax" if calculator is None else "not_conv")

            # Save
            outfile = f"{name}_large.traj"
            outpath = os.path.join(OUTPUT_DIR, outfile)
            write(outpath, slab)
            print(f"  Saved: {outfile}")

            results.append((name, info['a'], info['b'], info['thick'], info['n_atoms'],
                          info['composition'], E_init, E_final, converged, status))

        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"{'Material':<20} {'xy (Å)':<12} {'Thick':<7} {'Atoms':<7} {'E_final':<12} {'Status'}")
    print("-" * 75)
    for name, a, b, thick, atoms, comp, E_init, E_final, conv, status in results:
        E_str = f"{E_final:.1f}" if E_final is not None else "N/A"
        print(f"{name:<20} {a:.0f}×{b:.0f}{'':>3} {thick:<7.1f} {atoms:<7} {E_str:<12} {status}")

    # Write summary
    with open(os.path.join(OUTPUT_DIR, "generation_summary.txt"), 'w') as f:
        f.write("LARGE SLAB GENERATION SUMMARY (with relaxation)\n")
        f.write("=" * 60 + "\n\n")
        for name, a, b, thick, atoms, comp, E_init, E_final, conv, status in results:
            f.write(f"{name}:\n")
            f.write(f"  Size: {a:.1f}×{b:.1f}Å, Thick: {thick:.1f}Å\n")
            f.write(f"  Atoms: {atoms} {comp}\n")
            if E_final is not None:
                f.write(f"  Energy: {E_final:.3f} eV (ΔE={E_final-E_init:.3f} eV)\n")
            f.write(f"  Converged: {conv}\n\n")

    n_converged = sum(1 for r in results if r[8])
    print(f"\nGenerated: {len(results)}/{len(MATERIALS)} slabs")
    print(f"Converged: {n_converged}/{len(results)}")
    print(f"Output: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
