#!/usr/bin/env python3
"""
Slab Generation Script for Metal Oxide Surfaces
Generates all possible terminations for specified Miller indices
"""

from ase.spacegroup import crystal
from ase.io import write, read
from ase.constraints import FixAtoms
from ase.optimize import LBFGS
import numpy as np
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.ase import AseAtomsAdaptor
import os
import torch
import sys

# ============================================================================
# FairChem Calculator Setup
# ============================================================================

def load_fairchem_v2_calculator(checkpoint_path):
    """
    Load a FairChem v2 calculator from a local checkpoint file.

    Args:
        checkpoint_path: Path to the .pt checkpoint file

    Returns:
        FAIRChemCalculator instance
    """
    from fairchem.core import FAIRChemCalculator, pretrained_mlip

    print(f"  Loading FairChem v2 calculator from: {checkpoint_path}")

    # Determine device
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"  Using device: {device}")

    try:
        # Load predict unit from checkpoint
        predict_unit = pretrained_mlip.load_predict_unit(
            path=checkpoint_path,
            inference_settings="default",
            device=device
        )

        # Create the FAIRChemCalculator
        calc = FAIRChemCalculator(predict_unit, task_name="oc20")
        print("  ✓ Model loaded successfully")
        return calc

    except Exception as e:
        print(f"  ✗ Failed to load model: {e}")
        raise RuntimeError(f"Could not load FairChem calculator: {e}")


# ============================================================================
# Bulk Structure Definitions
# ============================================================================

# Rock salt structures
a_mgo = 4.212
mgo_bulk = crystal(['Mg', 'O'],
                   basis=[(0, 0, 0), (0.5, 0.5, 0.5)],
                   spacegroup=225,
                   cellpar=[a_mgo, a_mgo, a_mgo, 90, 90, 90])

a_cao = 4.810
cao_bulk = crystal(['Ca', 'O'],
                   basis=[(0, 0, 0), (0.5, 0.5, 0.5)],
                   spacegroup=225,
                   cellpar=[a_cao, a_cao, a_cao, 90, 90, 90])

# Fluorite structure
a_ceo2 = 5.411
ceo2_bulk = crystal(['Ce', 'O'],
                    basis=[(0, 0, 0), (0.25, 0.25, 0.25)],
                    spacegroup=225,
                    cellpar=[a_ceo2, a_ceo2, a_ceo2, 90, 90, 90])

# Rutile structures
a_tio2 = 4.594
c_tio2 = 2.959
tio2_rutile_bulk = crystal(['Ti', 'O'],
                           basis=[(0, 0, 0), (0.3, 0.3, 0.0)],
                           spacegroup=136,
                           cellpar=[a_tio2, a_tio2, c_tio2, 90, 90, 90])

a_anatase = 3.785
c_anatase = 9.514
tio2_anatase_bulk = crystal(['Ti', 'O'],
                            basis=[(0, 0, 0), (0, 0, 0.208)],
                            spacegroup=141,
                            cellpar=[a_anatase, a_anatase, c_anatase, 90, 90, 90])

a_sno2 = 4.737
c_sno2 = 3.186
sno2_bulk = crystal(['Sn', 'O'],
                    basis=[(0, 0, 0), (0.306, 0.306, 0.0)],
                    spacegroup=136,
                    cellpar=[a_sno2, a_sno2, c_sno2, 90, 90, 90])

# Wurtzite structure
a_zno = 3.250
c_zno = 5.207
zno_bulk = crystal(['Zn', 'O'],
                   basis=[(1/3, 2/3, 0), (1/3, 2/3, 0.382)],
                   spacegroup=186,
                   cellpar=[a_zno, a_zno, c_zno, 90, 90, 120])

# Corundum structure
a_al2o3 = 4.759
c_al2o3 = 12.991
al2o3_bulk = crystal(['Al', 'O'],
                     basis=[(0, 0, 0.352), (0.306, 0, 0.25)],
                     spacegroup=167,
                     cellpar=[a_al2o3, a_al2o3, c_al2o3, 90, 90, 120])

# Monoclinic ZrO2
a_zro2 = 5.150
b_zro2 = 5.212
c_zro2 = 5.317
beta_zro2 = 99.23
zro2_bulk = crystal(['Zr', 'O'],
                    basis=[(0.276, 0.041, 0.208), (0.070, 0.332, 0.341)],
                    spacegroup=14,
                    cellpar=[a_zro2, b_zro2, c_zro2, 90, beta_zro2, 90])

# Alpha-quartz SiO2
a_sio2 = 4.916
c_sio2 = 5.405
sio2_bulk = crystal(['Si', 'O'],
                    basis=[(0.470, 0, 2/3), (0.415, 0.272, 0.785)],
                    spacegroup=154,
                    cellpar=[a_sio2, a_sio2, c_sio2, 90, 90, 120])

# ============================================================================
# Helper Functions
# ============================================================================

def verify_periodic_boundary(atoms):
    """
    Verify that periodic boundary conditions are properly set for a slab.

    Args:
        atoms: ASE Atoms object

    Returns:
        None (prints warnings if issues found)
    """
    pbc = atoms.get_pbc()
    cell = atoms.get_cell()

    # Check PBC (now using [True, True, True] for UMA compatibility)
    if not (pbc[0] and pbc[1] and pbc[2]):
        print(f"    ⚠️  Warning: PBC should be [True, True, True] for UMA, got {pbc}")

    # Check that atoms are not too close to cell boundaries in z
    positions = atoms.get_positions()
    z_coords = positions[:, 2]
    min_z = np.min(z_coords)
    max_z = np.max(z_coords)

    if min_z < 1.0:
        print(f"    ⚠️  Warning: Atoms too close to bottom boundary (min_z={min_z:.2f}Å)")

    if (cell[2, 2] - max_z) < 10.0:
        print(f"    ⚠️  Warning: Vacuum too small (vacuum={cell[2, 2] - max_z:.2f}Å, recommend ≥15Å)")

    # Check for reasonable cell size
    slab_thickness = max_z - min_z
    if slab_thickness > cell[2, 2] * 0.8:
        print(f"    ⚠️  Warning: Slab thickness ({slab_thickness:.2f}Å) > 80% of cell height")


def fix_atoms_auto(atoms):
    """
    Automatically detect metal element and fix bottom half of atoms.

    Args:
        atoms: ASE Atoms object

    Returns:
        ASE Atoms object with constraints applied
    """
    temp = atoms.copy()

    # Get unique elements and find the metal (not oxygen)
    symbols = atoms.get_chemical_symbols()
    unique_elements = set(symbols)

    # Remove oxygen to find metal
    metals = [el for el in unique_elements if el != 'O']

    if len(metals) == 0:
        print("    Warning: No metal atoms found")
        return temp

    # Use the first metal as reference (or most abundant if multiple)
    if len(metals) > 1:
        metal_counts = {metal: symbols.count(metal) for metal in metals}
        element_symbol = max(metal_counts, key=metal_counts.get)
    else:
        element_symbol = metals[0]

    print(f"    Using {element_symbol} as reference element")

    # Get positions of reference element
    element_positions = np.array([atom.position for atom in temp if atom.symbol == element_symbol])

    if len(element_positions) == 0:
        print(f"    Warning: No {element_symbol} atoms found")
        return temp

    # Calculate median z-position
    element_median_z = np.median(element_positions[:, 2])

    # Create mask for atoms below median z
    mask = temp.positions[:, 2] < element_median_z

    # Apply constraints
    c = FixAtoms(mask=mask)
    temp.set_constraint(c)

    num_constrained = np.sum(mask)
    print(f"    Fixed {num_constrained} out of {len(temp)} atoms (below z={element_median_z:.3f} Å)")

    return temp


def generate_all_slabs_for_miller(bulk, miller_index, supercell_dimensions, thick, fixoff=False, calculator=None):
    """
    Generate all possible terminations for a specific Miller index.
    Uses auto-detection for fixing atoms.

    Args:
        bulk: ASE Atoms object of bulk structure
        miller_index: tuple of (h, k, l) Miller indices
        supercell_dimensions: tuple of (nx, ny, nz) for supercell
        thick: minimum slab thickness in Angstroms
        fixoff: if True, don't apply constraints
        calculator: Optional ASE calculator to attach to slabs

    Returns:
        List of ASE Atoms objects (all terminations)
    """
    bulk_temp = bulk.copy()
    pmg_structure = AseAtomsAdaptor.get_structure(bulk_temp)

    # Generate slab for specific Miller index with normal search
    # Use smaller vacuum to reduce initial force artifacts
    slab_gen = SlabGenerator(
        initial_structure=pmg_structure,
        miller_index=miller_index,
        min_slab_size=thick,
        min_vacuum_size=15.0,  # Reduced from 40.0 to minimize artifacts
        lll_reduce=False,
        center_slab=False,  # Don't center - we'll position manually
        primitive=True,
        max_normal_search=None,  # Normal search
    )

    # Get all possible terminations
    slabs = slab_gen.get_slabs(tol=0.3, bonds=None, max_broken_bonds=0, symmetrize=False)

    if len(slabs) == 0:
        raise ValueError(f"No valid slab generated for Miller {miller_index}")

    print(f"  Generated Miller {miller_index} ({len(slabs)} terminations)")

    # Process all terminations
    processed_slabs = []
    for slab_pmg in slabs:
        # Convert to ASE
        slab_ase = AseAtomsAdaptor.get_atoms(slab_pmg)
        slab = slab_ase.copy()
        slab = slab * supercell_dimensions

        # Properly position slab at bottom with correct vacuum
        min_pos_z = np.min(slab.positions[:, 2])
        max_pos_z = np.max(slab.positions[:, 2])
        slab_thickness = max_pos_z - min_pos_z

        # Shift to bottom leaving small buffer
        slab.positions[:, 2] -= min_pos_z
        slab.positions[:, 2] += 2.0  # 2Å buffer from bottom

        # Set proper cell height: slab + vacuum (20Å as requested)
        cell = slab.cell.copy()
        cell[2, 2] = slab_thickness + 20.0  # zmax-zmin+20 as requested
        slab.set_cell(cell, scale_atoms=False)

        # Set PBC to fully periodic for UMA compatibility
        slab.set_pbc([True, True, True])

        temp = slab.copy()
        if not fixoff:
            temp = fix_atoms_auto(temp)

        # Verify periodic boundary setup
        verify_periodic_boundary(temp)

        # Attach calculator if provided
        if calculator is not None:
            temp.calc = calculator

        processed_slabs.append(temp)

    return processed_slabs


def generate_miller_indices(max_index=1):
    """
    Generate all unique Miller indices up to max_index.

    Args:
        max_index: Maximum Miller index value

    Returns:
        List of unique Miller index tuples
    """
    miller_indices = []
    for h in range(-max_index, max_index + 1):
        for k in range(-max_index, max_index + 1):
            for l in range(-max_index, max_index + 1):
                # Skip (0,0,0)
                if h == 0 and k == 0 and l == 0:
                    continue

                # Add the Miller index
                miller_indices.append((h, k, l))

    return miller_indices


def relax_slab_with_lbfgs(slab, fmax=0.05, steps=300, log_file=None):
    """
    Relax a slab using LBFGS optimizer.

    Args:
        slab: ASE Atoms object with calculator attached
        fmax: Force convergence criterion (eV/Å)
        steps: Maximum optimization steps
        log_file: File handle for logging (optional)

    Returns:
        Tuple of (relaxed_slab, initial_energy, final_energy, converged)
    """
    if slab.calc is None:
        raise ValueError("Slab must have a calculator attached for relaxation")

    # Get initial energy
    try:
        initial_energy = slab.get_potential_energy()
        initial_forces = slab.get_forces()
        max_initial_force = np.max(np.linalg.norm(initial_forces, axis=1))
    except Exception as e:
        if log_file:
            log_file.write(f"    ERROR: Failed to get initial energy: {e}\n")
            log_file.flush()
        raise

    if log_file:
        log_file.write(f"    Initial energy: {initial_energy:.4f} eV\n")
        log_file.write(f"    Max initial force: {max_initial_force:.4f} eV/Å\n")
        log_file.flush()

    # Run optimization
    try:
        opt = LBFGS(slab, logfile=None)  # Suppress LBFGS output
        opt.run(fmax=fmax, steps=steps)

        # Get final energy
        final_energy = slab.get_potential_energy()
        final_forces = slab.get_forces()
        max_final_force = np.max(np.linalg.norm(final_forces, axis=1))

        converged = max_final_force < fmax

        if log_file:
            log_file.write(f"    Final energy: {final_energy:.4f} eV\n")
            log_file.write(f"    Energy change: {final_energy - initial_energy:.4f} eV\n")
            log_file.write(f"    Max final force: {max_final_force:.4f} eV/Å\n")
            log_file.write(f"    Optimization steps: {opt.nsteps}\n")
            log_file.write(f"    Converged: {converged}\n")
            log_file.flush()

        return slab, initial_energy, final_energy, converged

    except Exception as e:
        if log_file:
            log_file.write(f"    ERROR during optimization: {e}\n")
            log_file.flush()
        raise


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """
    Main function to generate all slabs for specified oxide materials.
    Generates all Miller indices with max index of 1 and all terminations.
    """

    # Load FairChem calculator for energy evaluation
    checkpoint_path = "../utility/uma-s-1p1.pt"
    calculator = None
    enable_relaxation = False

    if os.path.exists(checkpoint_path):
        print(f"\n{'='*80}")
        print("Loading FairChem calculator...")
        print(f"{'='*80}")
        try:
            calculator = load_fairchem_v2_calculator(checkpoint_path)
            print("✓ Calculator loaded - energy evaluation will be performed")
            enable_relaxation = True
        except Exception as e:
            print(f"⚠ Warning: Could not load calculator: {e}")
            print("  Continuing without energy evaluation...")
            calculator = None
    else:
        print(f"\n⚠ Warning: Checkpoint not found at {checkpoint_path}")
        print("  Slabs will be generated without energy evaluation")

    # Define materials with SMALL supercell dimensions for single GPU runs
    # Format: (name, bulk_structure, supercell_dimensions, thickness, miller_indices)
    # Supercell: Optimized for <20 Å (2nm) lateral size
    # Thickness: Reduced for smaller models (8-12 Å, 3-5 atomic layers)
    materials = [
        # Rock salt structures - cubic, a=4.2Å
        # (100): 4x4 gives 16.8x16.8 Å, thickness 8Å = ~4 layers (SMALL)
        ('MgO', mgo_bulk, (5, 5, 1), 8, [(1, 0, 0), (1, 1, 0), (1, 1, 1)]),
        # (100): 3x3 gives 14.4x14.4 Å, thickness 9Å = ~4 layers (SMALL)
        ('CaO', cao_bulk, (5, 5, 1), 9, [(1, 0, 0), (1, 1, 0), (1, 1, 1)]),

        # Fluorite (CeO2) - cubic, a=5.4Å, larger ions
        # (111): 3x3 gives 16.2x16.2 Å, thickness 10Å = ~4 O-Ce-O trilayers (SMALL)
        ('CeO2', ceo2_bulk, (5, 5, 1), 10, [(1, 1, 1), (1, 1, 0), (1, 0, 0)]),

        # Rutile (TiO2) - tetragonal, a=4.6Å, c=3.0Å, anisotropic
        # (110): 4x3 gives 18.4x13.8 Å (rectangular), thickness 8Å = ~4 Ti-O layers (SMALL)
        ('TiO2_rutile', tio2_rutile_bulk, (5, 4, 1), 8, [(1, 1, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)]),
        # Rutile SnO2 - a=4.7Å, c=3.2Å, similar to TiO2
        # (110): 4x3 gives 19.0x14.2 Å, thickness 9Å = ~4 layers (SMALL)
        ('SnO2', sno2_bulk, (5, 4, 1), 9, [(1, 1, 0), (1, 0, 1), (1, 0, 0)]),

        # Anatase (TiO2) - tetragonal, a=3.8Å, c=9.5Å, highly anisotropic
        # (101): 4x3 gives 15.1x11.4 Å, thickness 12Å = ~3 Ti-O layers (SMALL)
        # (001): 4x4 gives 15.1x15.1 Å, thickness 12Å
        # (100): 3x3 gives 11.4x28.5 Å -> skip (100) as it's too elongated
        ('TiO2_anatase', tio2_anatase_bulk, (5, 4, 1), 12, [(1, 0, 1), (0, 0, 1)]),

        # Wurtzite (ZnO) - hexagonal, a=3.25Å, c=5.2Å
        # (0001): 5x5 gives 16.3x16.3 Å (hexagonal), thickness 10Å = ~4 Zn-O bilayers (SMALL)
        # (100): 4x4 gives 13.0x13.0 Å, thickness 10Å
        # Skip (110) as it's too elongated in one dimension
        ('ZnO', zno_bulk, (5, 5, 1), 10, [(0, 0, 1), (1, 0, 0)]),

        # Corundum (Al2O3) - hexagonal, a=4.76Å, c=13.0Å, very anisotropic
        # (0001): 4x4 gives 19.0x19.0 Å, thickness 12Å = ~3 Al-O-Al trilayers (SMALL)
        # Skip (100) and (110) as they're too elongated
        ('Al2O3', al2o3_bulk, (4, 4, 1), 12, [(0, 0, 1)]),

        # Monoclinic (ZrO2) - a=5.15Å, b=5.21Å, c=5.32Å, β=99°
        # (111): 3x3 gives 15.6x15.6 Å, thickness 12Å = ~4 Zr-O layers (SMALL)
        ('ZrO2', zro2_bulk, (4, 4, 1), 12, [(1, 1, 1), (1, 0, 1), (1, 0, 0)]),

        # Alpha-quartz (SiO2) - hexagonal, a=4.92Å, c=5.41Å
        # (0001): 4x4 gives 19.7x19.7 Å, thickness 12Å = ~4 Si-O layers (SMALL)
        ('SiO2', sio2_bulk, (4, 4, 1), 12, [(0, 0, 1), (1, 0, 0), (1, 0, 1)]),
    ]

    print(f"\nGenerating slabs for experimentally relevant facets only")

    # Create output directory
    output_dir = './slabs'
    os.makedirs(output_dir, exist_ok=True)

    # Open energy log file if relaxation is enabled
    energy_log = None
    if enable_relaxation:
        energy_log = open('./energy_evaluation.log', 'w')
        energy_log.write("=" * 80 + "\n")
        energy_log.write("ENERGY EVALUATION LOG\n")
        energy_log.write("=" * 80 + "\n\n")
        energy_log.flush()

    # Summary log
    summary = []
    summary.append("=" * 80)
    summary.append("SLAB GENERATION SUMMARY - IMPORTANT FACETS ONLY")
    summary.append("=" * 80)
    if calculator is not None:
        summary.append("Calculator: FairChem v2 (UMA-S-1P1)")
        summary.append("Energy evaluation: Enabled with LBFGS relaxation")
    else:
        summary.append("Calculator: None")
        summary.append("Energy evaluation: Disabled")
    summary.append("")

    total_slabs = 0
    total_miller_processed = 0
    total_relaxed = 0
    total_converged = 0

    for name, bulk, supercell, thick, miller_indices in materials:
        print(f"\n{'='*80}")
        print(f"Processing {name} - {len(miller_indices)} important facets")
        print(f"{'='*80}")

        summary.append(f"{name} ({len(miller_indices)} facets):")
        material_slabs = 0

        for miller in miller_indices:
            miller_str = ''.join(map(str, miller)).replace('-', 'm')

            try:
                # Generate all terminations for this Miller index
                slabs = generate_all_slabs_for_miller(
                    bulk, miller, supercell, thick,
                    fixoff=False,
                    calculator=calculator
                )

                # Save initial slabs
                filename = f"{name}_{miller_str}_{supercell[0]}x{supercell[1]}.traj"
                filepath = os.path.join(output_dir, filename)
                write(filepath, slabs, format='traj')

                print(f"  Saved: {filename} ({len(slabs)} terminations, {len(slabs[0])} atoms)")

                # Perform energy evaluation if calculator is loaded
                if enable_relaxation and energy_log:
                    print(f"  Running LBFGS relaxation for {len(slabs)} terminations...")
                    energy_log.write(f"\n{name} Miller {miller} ({len(slabs)} terminations):\n")
                    energy_log.write("-" * 80 + "\n")
                    energy_log.flush()

                    relaxed_slabs = []
                    for i, slab in enumerate(slabs):
                        energy_log.write(f"  Termination {i+1}/{len(slabs)}:\n")
                        energy_log.flush()

                        try:
                            relaxed, E_initial, E_final, converged = relax_slab_with_lbfgs(
                                slab, fmax=0.05, steps=300, log_file=energy_log
                            )
                            relaxed_slabs.append(relaxed)
                            total_relaxed += 1
                            if converged:
                                total_converged += 1

                        except Exception as e:
                            energy_log.write(f"    FAILED: {e}\n")
                            energy_log.flush()
                            print(f"    Warning: Relaxation failed for termination {i+1}")
                            relaxed_slabs.append(slab)  # Keep original if relaxation fails

                    # Save relaxed slabs
                    relaxed_filename = f"{name}_{miller_str}_{supercell[0]}x{supercell[1]}_relaxed.traj"
                    relaxed_filepath = os.path.join(output_dir, relaxed_filename)
                    write(relaxed_filepath, relaxed_slabs, format='traj')
                    print(f"  Saved relaxed: {relaxed_filename}")

                summary.append(f"  Miller {miller}: {len(slabs)} terminations → {filename}")

                material_slabs += len(slabs)
                total_slabs += len(slabs)
                total_miller_processed += 1

            except Exception as e:
                print(f"  ERROR processing {name} Miller {miller}: {str(e)}")
                summary.append(f"  Miller {miller}: ERROR - {str(e)}")
                continue

        summary.append(f"  Total for {name}: {material_slabs} slabs")
        summary.append("")

    summary.append("=" * 80)
    summary.append(f"Total Miller indices processed: {total_miller_processed}")
    summary.append(f"Total slabs generated: {total_slabs}")
    if enable_relaxation:
        summary.append(f"Total slabs relaxed: {total_relaxed}")
        summary.append(f"Total converged: {total_converged}")
        convergence_rate = (total_converged / total_relaxed * 100) if total_relaxed > 0 else 0
        summary.append(f"Convergence rate: {convergence_rate:.1f}%")
    summary.append("=" * 80)

    # Close energy log if open
    if energy_log:
        energy_log.write("\n" + "=" * 80 + "\n")
        energy_log.write(f"Total slabs relaxed: {total_relaxed}\n")
        energy_log.write(f"Total converged: {total_converged}\n")
        if total_relaxed > 0:
            energy_log.write(f"Convergence rate: {total_converged/total_relaxed*100:.1f}%\n")
        energy_log.write("=" * 80 + "\n")
        energy_log.close()

    # Write summary to file
    summary_file = './slab_generation_summary.txt'
    with open(summary_file, 'w') as f:
        f.write('\n'.join(summary))

    print(f"\n{'='*80}")
    print(f"Summary written to: {summary_file}")
    print(f"All slabs saved to: {output_dir}/")
    print(f"Total Miller indices processed: {total_miller_processed}")
    print(f"Total slabs generated: {total_slabs}")
    if enable_relaxation:
        print(f"Total slabs relaxed: {total_relaxed}")
        print(f"Total converged: {total_converged}")
        convergence_rate = (total_converged / total_relaxed * 100) if total_relaxed > 0 else 0
        print(f"Convergence rate: {convergence_rate:.1f}%")
        print(f"Energy log: energy_evaluation.log")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
