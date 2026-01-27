#!/usr/bin/env python3
"""
Simple Bulk Energy Evaluation Script
=====================================
Evaluates bulk energies for all metal oxides to calculate accurate surface energies.
Handles both TiO2 rutile and anatase polymorphs separately.
"""

from ase.spacegroup import crystal
from ase.io import write
from ase.optimize import LBFGS
import numpy as np
import torch
import os
import sys

# ============================================================================
# FairChem Calculator Setup
# ============================================================================

def load_fairchem_calculator(checkpoint_path):
    """Load FairChem v2 calculator from checkpoint"""
    from fairchem.core import FAIRChemCalculator, pretrained_mlip

    print(f"Loading FairChem calculator from: {checkpoint_path}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")

    predict_unit = pretrained_mlip.load_predict_unit(
        path=checkpoint_path,
        inference_settings="default",
        device=device
    )

    calc = FAIRChemCalculator(predict_unit, task_name="oc20")
    print("✓ Calculator loaded successfully\n")
    return calc


# ============================================================================
# Bulk Structure Definitions (from generate_slabs.py)
# ============================================================================

def get_bulk_structures():
    """Define all bulk structures"""

    bulks = {}

    # MgO - Rock salt
    a_mgo = 4.212
    bulks['MgO'] = crystal(['Mg', 'O'],
                          basis=[(0, 0, 0), (0.5, 0.5, 0.5)],
                          spacegroup=225,
                          cellpar=[a_mgo, a_mgo, a_mgo, 90, 90, 90])

    # CaO - Rock salt
    a_cao = 4.810
    bulks['CaO'] = crystal(['Ca', 'O'],
                          basis=[(0, 0, 0), (0.5, 0.5, 0.5)],
                          spacegroup=225,
                          cellpar=[a_cao, a_cao, a_cao, 90, 90, 90])

    # CeO2 - Fluorite
    a_ceo2 = 5.411
    bulks['CeO2'] = crystal(['Ce', 'O'],
                           basis=[(0, 0, 0), (0.25, 0.25, 0.25)],
                           spacegroup=225,
                           cellpar=[a_ceo2, a_ceo2, a_ceo2, 90, 90, 90])

    # TiO2 Rutile
    a_tio2 = 4.594
    c_tio2 = 2.959
    bulks['TiO2_rutile'] = crystal(['Ti', 'O'],
                                  basis=[(0, 0, 0), (0.3, 0.3, 0.0)],
                                  spacegroup=136,
                                  cellpar=[a_tio2, a_tio2, c_tio2, 90, 90, 90])

    # TiO2 Anatase
    a_anatase = 3.785
    c_anatase = 9.514
    bulks['TiO2_anatase'] = crystal(['Ti', 'O'],
                                   basis=[(0, 0, 0), (0, 0, 0.208)],
                                   spacegroup=141,
                                   cellpar=[a_anatase, a_anatase, c_anatase, 90, 90, 90])

    # SnO2 - Rutile
    a_sno2 = 4.737
    c_sno2 = 3.186
    bulks['SnO2'] = crystal(['Sn', 'O'],
                           basis=[(0, 0, 0), (0.306, 0.306, 0.0)],
                           spacegroup=136,
                           cellpar=[a_sno2, a_sno2, c_sno2, 90, 90, 90])

    # ZnO - Wurtzite
    a_zno = 3.250
    c_zno = 5.207
    bulks['ZnO'] = crystal(['Zn', 'O'],
                          basis=[(1/3, 2/3, 0), (1/3, 2/3, 0.382)],
                          spacegroup=186,
                          cellpar=[a_zno, a_zno, c_zno, 90, 90, 120])

    # Al2O3 - Corundum
    a_al2o3 = 4.759
    c_al2o3 = 12.991
    bulks['Al2O3'] = crystal(['Al', 'O'],
                            basis=[(0, 0, 0.352), (0.306, 0, 0.25)],
                            spacegroup=167,
                            cellpar=[a_al2o3, a_al2o3, c_al2o3, 90, 90, 120])

    # ZrO2 - Monoclinic
    a_zro2 = 5.150
    b_zro2 = 5.212
    c_zro2 = 5.317
    beta_zro2 = 99.23
    bulks['ZrO2'] = crystal(['Zr', 'O'],
                           basis=[(0.276, 0.041, 0.208), (0.070, 0.332, 0.341)],
                           spacegroup=14,
                           cellpar=[a_zro2, b_zro2, c_zro2, 90, beta_zro2, 90])

    # SiO2 - Alpha-quartz
    a_sio2 = 4.916
    c_sio2 = 5.405
    bulks['SiO2'] = crystal(['Si', 'O'],
                           basis=[(0.470, 0, 2/3), (0.415, 0.272, 0.785)],
                           spacegroup=154,
                           cellpar=[a_sio2, a_sio2, c_sio2, 90, 90, 120])

    return bulks


def get_formula_units(atoms, material):
    """Calculate number of formula units in the structure"""

    formula_map = {
        'MgO': {'Mg': 1, 'O': 1},
        'CaO': {'Ca': 1, 'O': 1},
        'CeO2': {'Ce': 1, 'O': 2},
        'TiO2_rutile': {'Ti': 1, 'O': 2},
        'TiO2_anatase': {'Ti': 1, 'O': 2},
        'SnO2': {'Sn': 1, 'O': 2},
        'ZnO': {'Zn': 1, 'O': 1},
        'Al2O3': {'Al': 2, 'O': 3},
        'ZrO2': {'Zr': 1, 'O': 2},
        'SiO2': {'Si': 1, 'O': 2},
    }

    formula = formula_map[material]
    symbols = atoms.get_chemical_symbols()

    # Count atoms
    counts = {}
    for symbol in set(symbols):
        counts[symbol] = symbols.count(symbol)

    # Get cation (non-oxygen element)
    cation = [k for k in formula.keys() if k != 'O'][0]
    n_formula_units = counts[cation] / formula[cation]

    return n_formula_units


def relax_bulk(bulk, calculator, fmax=0.01, steps=500):
    """
    Relax bulk structure and return energy per formula unit

    Args:
        bulk: ASE Atoms object
        calculator: ASE calculator
        fmax: Force convergence criterion (eV/Å)
        steps: Maximum optimization steps

    Returns:
        Tuple of (relaxed_bulk, total_energy, energy_per_formula_unit, converged)
    """
    # Make a copy and attach calculator
    bulk = bulk.copy()
    bulk.calc = calculator

    # Get initial energy
    E_initial = bulk.get_potential_energy()
    forces_initial = bulk.get_forces()
    max_force_initial = np.max(np.linalg.norm(forces_initial, axis=1))

    print(f"  Initial energy: {E_initial:.4f} eV")
    print(f"  Initial max force: {max_force_initial:.4f} eV/Å")

    # Relax structure
    opt = LBFGS(bulk, logfile=None)
    opt.run(fmax=fmax, steps=steps)

    # Get final energy
    E_final = bulk.get_potential_energy()
    forces_final = bulk.get_forces()
    max_force_final = np.max(np.linalg.norm(forces_final, axis=1))

    converged = max_force_final < fmax

    print(f"  Final energy: {E_final:.4f} eV")
    print(f"  Energy change: {E_final - E_initial:.4f} eV")
    print(f"  Final max force: {max_force_final:.4f} eV/Å")
    print(f"  Steps: {opt.nsteps}")
    print(f"  Converged: {converged}")

    return bulk, E_final, converged


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """Main function to evaluate bulk energies"""

    print("=" * 80)
    print("BULK ENERGY EVALUATION")
    print("=" * 80)
    print()

    # Load calculator
    checkpoint_path = "../utility/uma-s-1p1.pt"

    if not os.path.exists(checkpoint_path):
        print(f"ERROR: Checkpoint not found at {checkpoint_path}")
        print("Please provide the correct path to the UMA-S-1P1 checkpoint.")
        sys.exit(1)

    calculator = load_fairchem_calculator(checkpoint_path)

    # Get bulk structures
    bulks = get_bulk_structures()

    # Results storage
    results = {}

    # Evaluate each bulk
    for material, bulk in bulks.items():
        print("=" * 80)
        print(f"Evaluating {material}")
        print("=" * 80)
        print(f"  Atoms: {len(bulk)} atoms")
        print(f"  Composition: {bulk.get_chemical_formula()}")

        try:
            # Relax bulk
            relaxed_bulk, total_energy, converged = relax_bulk(bulk, calculator)

            # Calculate energy per formula unit
            n_formula_units = get_formula_units(relaxed_bulk, material)
            energy_per_fu = total_energy / n_formula_units

            print(f"  Formula units: {n_formula_units:.1f}")
            print(f"  Energy per formula unit: {energy_per_fu:.4f} eV")

            # Store results
            results[material] = {
                'total_energy': total_energy,
                'n_formula_units': n_formula_units,
                'energy_per_fu': energy_per_fu,
                'converged': converged,
                'n_atoms': len(relaxed_bulk)
            }

            # Save relaxed structure
            output_file = f"bulk_{material}_relaxed.traj"
            write(output_file, relaxed_bulk)
            print(f"  Saved: {output_file}")

        except Exception as e:
            print(f"  ERROR: {e}")
            results[material] = None

        print()

    # ========================================================================
    # Generate Summary Report
    # ========================================================================

    print("=" * 80)
    print("BULK ENERGY SUMMARY")
    print("=" * 80)
    print()

    # Print Python dictionary format
    print("# Bulk reference energies (eV per formula unit)")
    print("# Calculated using FairChem UMA-S-1P1 with LBFGS relaxation")
    print("BULK_ENERGIES = {")

    # Group by base material
    base_materials = {}
    for material, result in results.items():
        if result is None:
            continue

        # Map to base material name for best_slab_small.py compatibility
        if material.startswith('TiO2'):
            base_name = 'TiO2'
        else:
            base_name = material

        if base_name not in base_materials:
            base_materials[base_name] = []

        base_materials[base_name].append((material, result))

    # Print in sorted order
    for base_name in sorted(base_materials.keys()):
        entries = base_materials[base_name]

        if len(entries) == 1:
            # Single entry (e.g., MgO, CaO)
            material, result = entries[0]
            print(f"    '{base_name}': {result['energy_per_fu']:.4f},  "
                  f"# {material}, {result['n_atoms']} atoms, "
                  f"converged={result['converged']}")
        else:
            # Multiple polymorphs (TiO2)
            print(f"    # {base_name} polymorphs:")
            for material, result in sorted(entries):
                polymorph = material.split('_')[1] if '_' in material else material
                print(f"    '{material}': {result['energy_per_fu']:.4f},  "
                      f"# {polymorph}, {result['n_atoms']} atoms, "
                      f"converged={result['converged']}")

    print("}")
    print()

    # Write detailed report to file
    report_file = "bulk_energy_report.txt"
    with open(report_file, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("BULK ENERGY EVALUATION REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write("Calculator: FairChem UMA-S-1P1\n")
        f.write("Optimizer: LBFGS (fmax=0.01 eV/Å, steps=500)\n\n")

        f.write(f"{'Material':<20} {'E_total (eV)':<15} {'N_fu':<8} "
                f"{'E/fu (eV)':<12} {'Converged':<12}\n")
        f.write("-" * 80 + "\n")

        for material in sorted(results.keys()):
            result = results[material]
            if result is None:
                f.write(f"{material:<20} {'FAILED':<15}\n")
            else:
                f.write(f"{material:<20} {result['total_energy']:<15.4f} "
                       f"{result['n_formula_units']:<8.1f} "
                       f"{result['energy_per_fu']:<12.4f} "
                       f"{str(result['converged']):<12}\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("BULK_ENERGIES dictionary for best_slab_small.py:\n")
        f.write("=" * 80 + "\n\n")
        f.write("BULK_ENERGIES = {\n")

        for base_name in sorted(base_materials.keys()):
            entries = base_materials[base_name]
            if len(entries) == 1:
                material, result = entries[0]
                f.write(f"    '{base_name}': {result['energy_per_fu']:.4f},\n")
            else:
                for material, result in sorted(entries):
                    f.write(f"    '{material}': {result['energy_per_fu']:.4f},  # {material}\n")

        f.write("}\n")

    print(f"Detailed report saved to: {report_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
