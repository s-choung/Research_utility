#!/usr/bin/env python3
"""
Genetic Algorithm for Metal Deposition on Oxide Slabs
Optimizes placement of metal atoms (Pt, Au, Pd, Rh, Ni, Ru, Os, Ir) on oxide surfaces
"""

import os
import sys
import json
import numpy as np
import torch
import threading
import queue
from pathlib import Path
from datetime import datetime
from random import random
from functools import partial
from ase import Atoms
from ase.constraints import FixAtoms
from ase.io import write, read
from ase.optimize import LBFGS
from ase.data import atomic_numbers, covalent_radii
from ase.calculators.singlepoint import SinglePointCalculator

# Force unbuffered output for real-time logging
print = partial(print, flush=True)

# ASE GA modules
from ase.ga.data import PrepareDB, DataConnection
from ase.ga.startgenerator import StartGenerator
from ase.ga.population import Population
from ase.ga.utilities import closest_distances_generator, get_all_atom_types
from ase.ga.standard_comparators import InteratomicDistanceComparator
from ase.ga.cutandsplicepairing import CutAndSplicePairing
from ase.ga.offspring_creator import OperationSelector
from ase.ga.standardmutations import MirrorMutation, RattleMutation, PermutationMutation

# Default slab directory
SLABS_DIR = Path('/DATA/user_scratch/jsh9967/5_uma_MSI/1_slab_gen/slabs_large')


# =============================================================================
# UMA CALCULATOR
# =============================================================================

def load_uma_calculator(checkpoint_path, device='cuda'):
    """
    Load UMA model calculator

    Parameters:
    -----------
    checkpoint_path : str or Path
        Path to UMA model checkpoint
    device : str
        Device to use ('cuda' or 'cpu')

    Returns:
    --------
    calc : FAIRChemCalculator
        UMA calculator object
    """
    from fairchem.core import FAIRChemCalculator, pretrained_mlip

    # Check device availability
    if device == 'cuda' and not torch.cuda.is_available():
        print("⚠ CUDA not available, falling back to CPU")
        device = 'cpu'

    print(f"\n{'='*70}")
    print(f"Loading UMA model from: {checkpoint_path}")
    print(f"Device: {device}")
    print(f"{'='*70}")

    try:
        predict_unit = pretrained_mlip.load_predict_unit(
            path=str(checkpoint_path),
            inference_settings="default",
            device=device
        )

        calc = FAIRChemCalculator(predict_unit, task_name="omat")
        print("✓ UMA model loaded successfully\n")

        return calc

    except Exception as e:
        print(f"❌ Error loading UMA model: {e}")
        raise


# =============================================================================
# SLAB LOADING
# =============================================================================

def load_oxide_slab(slab_name, slabs_dir=None):
    """
    Load oxide slab from traj file

    Parameters:
    -----------
    slab_name : str
        Slab identifier (e.g., 'CeO2_111', 'TiO2_anatase_001')
    slabs_dir : Path, optional
        Directory containing slab files (default: SLABS_DIR)

    Returns:
    --------
    slab : ase.Atoms
        Oxide slab with constraints preserved
    """
    if slabs_dir is None:
        slabs_dir = SLABS_DIR
    slabs_dir = Path(slabs_dir)

    print(f"\n{'='*70}")
    print(f"Loading oxide slab: {slab_name}")
    print(f"{'='*70}")

    # Construct path: {slab_name}_large.traj
    slab_file = slabs_dir / f"{slab_name}_large.traj"

    if not slab_file.exists():
        # List available slabs for helpful error message
        available = [f.stem.replace('_large', '') for f in slabs_dir.glob('*_large.traj')]
        raise FileNotFoundError(
            f"Slab file not found: {slab_file}\n"
            f"Available slabs: {', '.join(sorted(available))}"
        )

    # Load slab from trajectory file
    slab = read(str(slab_file))

    # Ensure PBC for UMA
    slab.set_pbc([True, True, True])

    # Report slab info
    n_atoms = len(slab)
    constraint = slab.constraints[0] if slab.constraints else None
    n_fixed = len(constraint.index) if constraint else 0
    cell_params = slab.cell.lengths()

    # Parse miller indices from filename (e.g., CeO2_111 -> [1,1,1])
    parts = slab_name.split('_')
    miller_str = parts[-1]  # Last part is miller index
    miller = [int(d) for d in miller_str]

    print(f"✓ Slab loaded from: {slab_file.name}")
    print(f"  Composition: {slab.get_chemical_formula()}")
    print(f"  Atoms: {n_atoms} ({n_fixed} fixed)")
    print(f"  Cell: {cell_params[0]:.2f} × {cell_params[1]:.2f} × {cell_params[2]:.2f} Å")
    print(f"  Miller: {miller}")

    return slab

# =============================================================================
# GA SETUP
# =============================================================================

def create_metal_atoms_box(slab, metal_symbol, n_metal, placement_config):
    """
    Create placement box for metal atoms above slab surface

    Parameters:
    -----------
    slab : ase.Atoms
        Oxide slab
    metal_symbol : str
        Metal element symbol
    n_metal : int
        Number of metal atoms
    placement_config : dict
        Placement configuration parameters

    Returns:
    --------
    box_to_place_in : list
        Box definition [p0, [v1, v2, v3]] for StartGenerator
    """
    cell = slab.cell
    positions = slab.positions

    # Get surface height
    surface_z = positions[:, 2].max()

    # Placement box parameters
    height = placement_config['placement_height']
    xy_ratio = placement_config['placement_xy_ratio']

    # Define box origin (bottom corner)
    p0 = np.array([
        cell[0, 0] * (1 - xy_ratio) / 2,
        cell[1, 1] * (1 - xy_ratio) / 2,
        surface_z + 2.0  # 2Å clearance above surface
    ])

    # Define box vectors
    v1 = cell[0, :] * xy_ratio  # x direction
    v2 = cell[1, :] * xy_ratio  # y direction
    v3 = np.array([0, 0, height])  # z direction (height above surface)

    box_to_place_in = [p0, [v1, v2, v3]]

    print(f"✓ Placement box created:")
    print(f"  Origin: ({p0[0]:.2f}, {p0[1]:.2f}, {p0[2]:.2f}) Å")
    print(f"  X range: {p0[0]:.2f} - {p0[0] + np.linalg.norm(v1):.2f} Å")
    print(f"  Y range: {p0[1]:.2f} - {p0[1] + np.linalg.norm(v2):.2f} Å")
    print(f"  Z range: {p0[2]:.2f} - {p0[2] + height:.2f} Å")
    volume = np.linalg.norm(v1) * np.linalg.norm(v2) * height
    print(f"  Volume: {volume:.2f} Å³")

    return box_to_place_in


def generate_candidate_with_timeout(sg, timeout_sec=60):
    """
    Generate a single candidate with timeout protection.

    Parameters:
    -----------
    sg : StartGenerator
        ASE GA start generator
    timeout_sec : float
        Timeout in seconds

    Returns:
    --------
    candidate : Atoms or None
        Generated candidate or None if timeout
    """
    result_queue = queue.Queue()

    def worker():
        try:
            candidate = sg.get_new_candidate()
            result_queue.put(('success', candidate))
        except Exception as e:
            result_queue.put(('error', str(e)))

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    thread.join(timeout=timeout_sec)

    if thread.is_alive():
        # Thread is still running - timeout occurred
        return None

    try:
        status, result = result_queue.get_nowait()
        if status == 'success':
            return result
        else:
            print(f"⚠ Error generating candidate: {result}")
            return None
    except queue.Empty:
        return None


def generate_initial_population_adaptive(
    slab, metal_symbol, n_metal, placement_config, ga_params, operators,
    timeout_per_candidate=60, max_retries=5, box_expansion_factor=1.3
):
    """
    Generate initial population with adaptive box sizing.

    If candidate generation times out, expands the placement box and retries.

    Parameters:
    -----------
    slab : Atoms
        Oxide slab
    metal_symbol : str
        Metal element symbol
    n_metal : int
        Number of metal atoms
    placement_config : dict
        Initial placement configuration (will be modified if expansion needed)
    ga_params : dict
        GA parameters including population_size
    operators : dict
        GA operators including blmin
    timeout_per_candidate : float
        Timeout per candidate in seconds (default: 60)
    max_retries : int
        Maximum number of box expansion retries (default: 5)
    box_expansion_factor : float
        Factor to expand box on each retry (default: 1.3)

    Returns:
    --------
    population : list
        List of generated candidate Atoms objects
    final_placement_box : list
        The placement box used for successful generation
    """
    population_size = ga_params['population_size']
    current_config = placement_config.copy()

    for retry in range(max_retries + 1):
        # Create placement box with current config
        placement_box = create_metal_atoms_box(slab, metal_symbol, n_metal, current_config)

        # Create start generator
        atom_numbers_list = [atomic_numbers[metal_symbol]] * n_metal
        sg = StartGenerator(
            slab, atom_numbers_list, operators['blmin'],
            box_to_place_in=placement_box
        )

        # Try to generate population
        print(f"Generating initial population (attempt {retry + 1}/{max_retries + 1})...")
        population = []
        consecutive_timeouts = 0

        for i in range(population_size):
            start_time = datetime.now()
            candidate = generate_candidate_with_timeout(sg, timeout_sec=timeout_per_candidate)
            elapsed = (datetime.now() - start_time).total_seconds()

            if candidate is None:
                consecutive_timeouts += 1
                print(f"  ⚠ Candidate {i+1} timed out after {elapsed:.1f}s (consecutive: {consecutive_timeouts})")

                # If too many consecutive timeouts, expand box and restart
                if consecutive_timeouts >= 3:
                    print(f"  🔄 Too many timeouts - expanding placement box...")
                    break
            else:
                consecutive_timeouts = 0
                population.append(candidate)
                if (i + 1) % 5 == 0 or (i + 1) == population_size:
                    print(f"  Generated {i + 1}/{population_size} candidates")

        # Check if we got enough candidates
        if len(population) >= population_size:
            print(f"✓ Initial population generated ({len(population)} structures)")
            return population, placement_box

        # Need to expand and retry
        if retry < max_retries:
            old_xy = current_config['placement_xy_ratio']
            old_height = current_config['placement_height']

            # Expand the box
            new_xy = min(old_xy * box_expansion_factor, 0.95)  # Cap at 95% of cell
            new_height = old_height * box_expansion_factor

            current_config['placement_xy_ratio'] = new_xy
            current_config['placement_height'] = new_height

            print(f"\n{'='*50}")
            print(f"⚠ Box expansion (retry {retry + 1}/{max_retries}):")
            print(f"  xy_ratio: {old_xy:.3f} → {new_xy:.3f}")
            print(f"  height: {old_height:.2f} → {new_height:.2f} Å")
            print(f"{'='*50}\n")
        else:
            print(f"❌ Failed to generate full population after {max_retries} retries")
            print(f"  Generated {len(population)}/{population_size} candidates")
            if len(population) > 0:
                return population, placement_box
            raise RuntimeError(f"Could not generate any candidates after {max_retries} box expansions")

    return population, placement_box


def setup_ga_operators(slab, metal_symbol, n_metal, ga_params, placement_box):
    """
    Setup GA operators for metal deposition

    Parameters:
    -----------
    slab : ase.Atoms
        Oxide slab
    metal_symbol : str
        Metal element symbol
    n_metal : int
        Number of metal atoms
    ga_params : dict
        GA parameters
    placement_box : numpy.ndarray
        Placement box boundaries

    Returns:
    --------
    operators : dict
        Dictionary containing all GA operators
    """
    # Get all atom types (slab + metal)
    slab_types = set(slab.get_chemical_symbols())
    all_types = list(slab_types) + [metal_symbol]
    atom_numbers = [atomic_numbers[sym] for sym in all_types]

    # Generate closest distance matrix
    blmin = closest_distances_generator(
        atom_numbers=atom_numbers,
        ratio_of_covalent_radii=ga_params['covalent_ratio']
    )

    # Comparator for structure similarity
    comp = InteratomicDistanceComparator(
        n_top=n_metal,
        pair_cor_cum_diff=0.015,
        pair_cor_max=0.7,
        dE=1.0,
        mic=False
    )

    # Pairing operator
    pairing = CutAndSplicePairing(
        slab=slab,
        n_top=n_metal,
        blmin=blmin,
        p1=1.0,
        p2=0.05,
        minfrac=0.15,
        cellbounds=placement_box,
        use_tags=False
    )

    # Mutation operators
    mutation_operators = []
    mutation_weights = []
    weights = ga_params['mutation_weights']

    # Mirror mutation
    if weights[0] > 0:
        mutation_operators.append(MirrorMutation(blmin, n_top=n_metal))
        mutation_weights.append(weights[0])

    # Rattle mutation
    if weights[1] > 0:
        mutation_operators.append(RattleMutation(blmin, n_top=n_metal, rattle_strength=0.8))
        mutation_weights.append(weights[1])

    # Permutation mutation (only if multiple atom types)
    if weights[2] > 0 and len(set([metal_symbol])) > 1:
        mutation_operators.append(PermutationMutation(n_top=n_metal))
        mutation_weights.append(weights[2])

    # Create mutation selector (must have matching lengths)
    mutations = OperationSelector(
        mutation_weights,  # Only weights for operators we actually added
        mutation_operators
    )

    print(f"✓ GA operators configured:")
    print(f"  Crossover prob: {ga_params['crossover_probability']}")
    print(f"  Mutation prob: {ga_params['mutation_probability']}")
    print(f"  Mutations: {len(mutation_operators)} types")

    return {
        'comparator': comp,
        'pairing': pairing,
        'mutations': mutations,
        'blmin': blmin
    }


# =============================================================================
# GA EXECUTION
# =============================================================================

def relax_structure(atoms, calc, fmax=0.05, max_steps=200):
    """
    Relax structure with UMA calculator

    Parameters:
    -----------
    atoms : ase.Atoms
        Structure to relax
    calc : Calculator
        UMA calculator
    fmax : float
        Force convergence criterion
    max_steps : int
        Maximum optimization steps

    Returns:
    --------
    atoms : ase.Atoms
        Relaxed structure
    converged : bool
        Whether optimization converged
    """
    atoms.calc = calc

    # Get initial energy
    e_initial = atoms.get_potential_energy()

    # Optimize
    opt = LBFGS(atoms, trajectory=None, logfile=None)

    try:
        opt.run(fmax=fmax, steps=max_steps)
        # Check convergence by looking at final forces
        forces = atoms.get_forces()
        max_force = (forces**2).sum(axis=1).max()**0.5
        converged = max_force < fmax
        e_final = atoms.get_potential_energy()

    except Exception as e:
        print(f"⚠ Relaxation error: {e}")
        converged = False
        e_final = e_initial

    return atoms, converged


def run_single_ga(slab, metal_symbol, n_metal, uma_calc, ga_params, placement_config, output_dir):
    """
    Run single GA optimization for metal on oxide slab

    Parameters:
    -----------
    slab : ase.Atoms
        Oxide slab
    metal_symbol : str
        Metal element symbol
    n_metal : int
        Number of metal atoms
    uma_calc : Calculator
        UMA calculator
    ga_params : dict
        GA parameters
    placement_config : dict
        Placement configuration
    output_dir : Path
        Output directory

    Returns:
    --------
    results : dict
        Summary of GA results
    """
    start_time = datetime.now()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*70}")
    print(f"GA OPTIMIZATION: {metal_symbol} on {slab.info.get('material', 'oxide')}")
    print(f"{'='*70}")
    print(f"Metal atoms: {n_metal}")
    print(f"Population: {ga_params['population_size']}")
    print(f"Generations: {ga_params['n_iterations']}")
    print(f"{'='*70}\n")

    # Create initial placement box (will be adjusted if needed)
    placement_box = create_metal_atoms_box(slab, metal_symbol, n_metal, placement_config)

    # Setup GA operators
    operators = setup_ga_operators(slab, metal_symbol, n_metal, ga_params, placement_box)

    # Database for GA
    db_file = output_dir / f'{metal_symbol}_ga.db'
    if db_file.exists():
        db_file.unlink()

    # Prepare database
    db_prepare = PrepareDB(
        db_file_name=str(db_file),
        simulation_cell=slab,
        stoichiometry=[n_metal],
        atom_numbers=[atomic_numbers[metal_symbol]]
    )

    # Generate initial population with adaptive box sizing
    # Timeout and expansion parameters
    timeout_per_candidate = ga_params.get('candidate_timeout', 60)  # seconds
    max_box_retries = ga_params.get('max_box_retries', 5)
    box_expansion_factor = ga_params.get('box_expansion_factor', 1.3)

    starting_population, placement_box = generate_initial_population_adaptive(
        slab=slab,
        metal_symbol=metal_symbol,
        n_metal=n_metal,
        placement_config=placement_config,
        ga_params=ga_params,
        operators=operators,
        timeout_per_candidate=timeout_per_candidate,
        max_retries=max_box_retries,
        box_expansion_factor=box_expansion_factor
    )

    # Add unrelaxed candidates to database
    for atoms in starting_population:
        db_prepare.add_unrelaxed_candidate(atoms)

    # Track best across all generations
    best_energy = float('inf')
    best_atoms = None
    generation_best = []

    # GA loop
    print(f"\n{'='*70}")
    print(f"Starting GA iterations...")
    print(f"{'='*70}\n")

    for gen in range(ga_params['n_iterations']):
        print(f"\n{'#'*70}")
        print(f"# GENERATION {gen+1}/{ga_params['n_iterations']}")
        print(f"{'#'*70}")

        # Create DataConnection for this iteration
        db = DataConnection(db_file_name=str(db_file))

        # Relax all unrelaxed candidates
        n_to_relax = db.get_number_of_unrelaxed_candidates()
        if n_to_relax > 0:
            print(f"Relaxing {n_to_relax} unrelaxed candidates...")
            relaxed_count = 0
            while db.get_number_of_unrelaxed_candidates() > 0:
                atoms = db.get_an_unrelaxed_candidate()
                atoms.calc = uma_calc

                # Relax
                opt = LBFGS(atoms, trajectory=None, logfile=None)
                opt.run(fmax=ga_params['fmax_relaxation'], steps=ga_params['max_steps_relax'])

                energy = atoms.get_potential_energy()
                if 'key_value_pairs' not in atoms.info:
                    atoms.info['key_value_pairs'] = {}
                atoms.info['key_value_pairs']['raw_score'] = -energy

                # Use SinglePointCalculator to store energy without forces
                # This avoids DB serialization issues with large systems
                atoms.arrays.pop('forces', None)
                atoms.calc = SinglePointCalculator(atoms, energy=energy)

                db.add_relaxed_step(atoms)

                # Track best
                if energy < best_energy:
                    best_energy = energy
                    best_atoms = atoms.copy()
                    print(f"  🏆 New best: E = {energy:.4f} eV (relaxation)")

                relaxed_count += 1
                if relaxed_count % 5 == 0 or relaxed_count == n_to_relax:
                    print(f"  Relaxed {relaxed_count}/{n_to_relax}")

        # Create population from relaxed candidates
        population = Population(
            data_connection=db,
            population_size=ga_params['population_size'],
            comparator=operators['comparator']
        )

        # Generate new offspring
        print(f"Generating {ga_params['n_candidates_per_gen']} new candidates...")
        for i in range(ga_params['n_candidates_per_gen']):
            # Get two parent candidates
            a1, a2 = population.get_two_candidates()

            # Generate offspring using pairing (crossover)
            offspring, desc = operators['pairing'].get_new_individual([a1, a2])

            if offspring is None:
                continue

            # Add unrelaxed offspring to database (this assigns confid)
            db.add_unrelaxed_candidate(offspring, description=desc)

            # Apply mutation with probability (offspring now has confid from database)
            if random() < ga_params['mutation_probability']:
                offspring_mut, mut_desc = operators['mutations'].get_new_individual([offspring])
                if offspring_mut is not None:
                    db.add_unrelaxed_step(offspring_mut, mut_desc)

            if (i + 1) % 5 == 0 or (i + 1) == ga_params['n_candidates_per_gen']:
                print(f"  Generated {i+1}/{ga_params['n_candidates_per_gen']} candidates")

        # Generation summary
        pop_energies = [a.get_potential_energy() for a in population.pop]
        gen_best = min(pop_energies)
        gen_avg = np.mean(pop_energies)
        generation_best.append(gen_best)

        print(f"\nGeneration {gen+1} summary:")
        print(f"  Best: {gen_best:.4f} eV")
        print(f"  Average: {gen_avg:.4f} eV")
        print(f"  Global best: {best_energy:.4f} eV")

    # Save results
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()

    # Get all relaxed candidates
    all_candidates = list(db.get_all_relaxed_candidates())
    all_candidates.sort(key=lambda a: a.get_potential_energy())

    # Ensure we have best_atoms
    if best_atoms is None and all_candidates:
        best_atoms = all_candidates[0]
        best_energy = best_atoms.get_potential_energy()

    # Save best structure
    if best_atoms is not None:
        best_file = output_dir / f'{metal_symbol}_best.xyz'
        write(str(best_file), best_atoms)

        best_traj = output_dir / f'{metal_symbol}_best.traj'
        write(str(best_traj), best_atoms)

    top5_file = output_dir / f'{metal_symbol}_top5.traj'
    write(str(top5_file), all_candidates[:5])

    # Summary
    summary = {
        'slab': slab.info.get('material', 'unknown'),
        'metal': metal_symbol,
        'n_metal': n_metal,
        'best_energy': float(best_energy),
        'best_energy_per_metal': float(best_energy / n_metal),
        'generations': ga_params['n_iterations'],
        'population_size': ga_params['population_size'],
        'total_structures': len(all_candidates),
        'duration_seconds': duration,
        'duration_hours': duration / 3600,
        'generation_best': [float(e) for e in generation_best],
        'ga_parameters': ga_params,
        'timestamp': start_time.isoformat(),
        'output_dir': str(output_dir)
    }

    summary_file = output_dir / f'{metal_symbol}_summary.json'
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

    # Final report
    print(f"\n{'='*70}")
    print(f"✅ GA COMPLETE")
    print(f"{'='*70}")
    print(f"Metal: {metal_symbol} ({n_metal} atoms)")
    print(f"Slab: {slab.info.get('material', 'unknown')}")
    print(f"Best energy: {best_energy:.4f} eV ({best_energy/n_metal:.4f} eV/atom)")
    print(f"Duration: {duration/3600:.2f} hours")
    print(f"Total structures: {len(all_candidates)}")
    print(f"Output: {output_dir}")
    print(f"{'='*70}\n")

    return summary


if __name__ == '__main__':
    print("This is a library module. Use ga_runner.py to run GA jobs.")
