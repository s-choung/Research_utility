#!/usr/bin/env python3
"""
Restart Script for Failed Slab Relaxations
Loads unconverged structures and re-runs with increased max_steps and adjusted parameters
"""

from ase.io import read, write
from ase.optimize import LBFGS
import numpy as np
import os
import torch

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


def relax_slab_with_lbfgs(slab, fmax=0.05, steps=500, log_file=None):
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
# Failed Calculations Definition
# ============================================================================

# Define failed calculations from energy_evaluation.log (Converged: False)
failed_calculations = [
    {
        'file': './slabs/CeO2_100_5x5_relaxed.traj',
        'termination': 0,  # Only 1 termination (index 0)
        'material': 'CeO2',
        'miller': '(1,0,0)',
        'max_force': 2.5991  # Final max force from log
    },
    {
        'file': './slabs/TiO2_rutile_110_5x4_relaxed.traj',
        'termination': 1,  # Second of 2 terminations
        'material': 'TiO2_rutile',
        'miller': '(1,1,0)',
        'max_force': 0.1725
    },
    {
        'file': './slabs/ZnO_001_5x5_relaxed.traj',
        'termination': 1,  # Second of 2 terminations
        'material': 'ZnO',
        'miller': '(0,0,1)',
        'max_force': 0.6991
    },
    {
        'file': './slabs/ZrO2_111_4x4_relaxed.traj',
        'termination': 2,  # Third of 4 terminations
        'material': 'ZrO2',
        'miller': '(1,1,1)',
        'max_force': 0.3068
    },
    {
        'file': './slabs/ZrO2_111_4x4_relaxed.traj',
        'termination': 3,  # Fourth of 4 terminations
        'material': 'ZrO2',
        'miller': '(1,1,1)',
        'max_force': 0.1040
    },
]


# ============================================================================
# Main Execution
# ============================================================================

def main():
    """
    Main function to restart failed relaxations.
    """

    print(f"\n{'='*80}")
    print("RESTART FAILED RELAXATIONS")
    print(f"{'='*80}\n")

    # Load FairChem calculator
    checkpoint_path = "../utility/uma-s-1p1.pt"

    if not os.path.exists(checkpoint_path):
        print(f"ERROR: Checkpoint not found at {checkpoint_path}")
        print("Cannot proceed without calculator.")
        return

    print(f"{'='*80}")
    print("Loading FairChem calculator...")
    print(f"{'='*80}")

    try:
        calculator = load_fairchem_v2_calculator(checkpoint_path)
        print("✓ Calculator loaded - restart can proceed\n")
    except Exception as e:
        print(f"ERROR: Could not load calculator: {e}")
        return

    # Create output directory for restarted slabs
    output_dir = './slabs_restarted'
    os.makedirs(output_dir, exist_ok=True)

    # Open restart log file
    log_filename = './restart_failed.log'
    log_file = open(log_filename, 'w')
    log_file.write("=" * 80 + "\n")
    log_file.write("RESTART FAILED RELAXATIONS LOG\n")
    log_file.write("=" * 80 + "\n")
    log_file.write(f"Total failed calculations to restart: {len(failed_calculations)}\n")
    log_file.write(f"Max steps increased: 300 → 500\n")
    log_file.write(f"Force convergence: fmax = 0.05 eV/Å\n")
    log_file.write("=" * 80 + "\n\n")
    log_file.flush()

    # Statistics
    total_attempts = 0
    total_converged = 0
    total_failed = 0

    # Process each failed calculation
    for calc_info in failed_calculations:
        traj_file = calc_info['file']
        term_idx = calc_info['termination']
        material = calc_info['material']
        miller = calc_info['miller']
        prev_max_force = calc_info['max_force']

        print(f"\n{'='*80}")
        print(f"Restarting: {material} Miller {miller} - Termination {term_idx+1}")
        print(f"  Previous max force: {prev_max_force:.4f} eV/Å (did not converge)")
        print(f"{'='*80}")

        log_file.write(f"\n{material} Miller {miller} - Termination {term_idx+1}:\n")
        log_file.write("-" * 80 + "\n")
        log_file.write(f"  Source: {traj_file}\n")
        log_file.write(f"  Previous max force: {prev_max_force:.4f} eV/Å\n")
        log_file.flush()

        # Check if file exists
        if not os.path.exists(traj_file):
            print(f"  ⚠ WARNING: File not found: {traj_file}")
            log_file.write(f"  ERROR: File not found\n")
            log_file.flush()
            total_failed += 1
            continue

        try:
            # Load all structures from trajectory
            all_slabs = read(traj_file, index=':')

            # Check if termination index is valid
            if term_idx >= len(all_slabs):
                print(f"  ⚠ WARNING: Termination index {term_idx} out of range (only {len(all_slabs)} structures)")
                log_file.write(f"  ERROR: Invalid termination index\n")
                log_file.flush()
                total_failed += 1
                continue

            # Get the specific failed structure
            slab = all_slabs[term_idx].copy()

            print(f"  Loaded structure: {len(slab)} atoms")
            log_file.write(f"  Number of atoms: {len(slab)}\n")

            # Ensure PBC is set correctly for FairChem
            slab.set_pbc([True, True, True])

            # Attach calculator
            slab.calc = calculator

            # Run relaxation with increased max_steps
            print(f"  Running LBFGS relaxation (max_steps=500)...")
            total_attempts += 1

            relaxed, E_initial, E_final, converged = relax_slab_with_lbfgs(
                slab, fmax=0.05, steps=500, log_file=log_file
            )

            if converged:
                print(f"  ✓ CONVERGED: ΔE = {E_final - E_initial:.4f} eV")
                total_converged += 1
            else:
                print(f"  ✗ STILL UNCONVERGED: ΔE = {E_final - E_initial:.4f} eV")
                total_failed += 1

            # Save restarted structure
            output_file = f"{material}_miller{miller.replace(',','').replace('(','').replace(')','')}_term{term_idx}_restarted.traj"
            output_path = os.path.join(output_dir, output_file)
            write(output_path, relaxed)
            print(f"  Saved to: {output_path}")
            log_file.write(f"  Output: {output_path}\n")
            log_file.flush()

        except Exception as e:
            print(f"  ✗ ERROR: {e}")
            log_file.write(f"  EXCEPTION: {e}\n")
            log_file.flush()
            total_failed += 1
            continue

    # Summary
    print(f"\n{'='*80}")
    print("RESTART SUMMARY")
    print(f"{'='*80}")
    print(f"Total restart attempts: {total_attempts}")
    print(f"Total converged: {total_converged}")
    print(f"Total still unconverged: {total_failed}")
    if total_attempts > 0:
        print(f"Convergence rate: {total_converged/total_attempts*100:.1f}%")
    print(f"Output directory: {output_dir}/")
    print(f"Log file: {log_filename}")
    print(f"{'='*80}")

    # Write summary to log
    log_file.write("\n" + "=" * 80 + "\n")
    log_file.write("RESTART SUMMARY\n")
    log_file.write("=" * 80 + "\n")
    log_file.write(f"Total restart attempts: {total_attempts}\n")
    log_file.write(f"Total converged: {total_converged}\n")
    log_file.write(f"Total still unconverged: {total_failed}\n")
    if total_attempts > 0:
        log_file.write(f"Convergence rate: {total_converged/total_attempts*100:.1f}%\n")
    log_file.write("=" * 80 + "\n")
    log_file.close()


if __name__ == "__main__":
    main()
