

from ase.io import read, write, Trajectory
from ase.md.langevin import Langevin
from ase.md.velocitydistribution import MaxwellBoltzmannDistribution, Stationary
from ase.md import MDLogger
from ase import units
from ase.constraints import FixAtoms
import numpy as np
import os
import torch
import time
import datetime
import sys
import argparse
from fairchem.core.common.relaxation.ase_utils import OCPCalculator
from ase.neighborlist import NeighborList
from ase.optimize import LBFGS

# Function for simpler logging
def log(message):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {message}")
    sys.stdout.flush()

def load_gemnet_calculator():
    """Load the finetuned GemNet calculator"""
    checkpoint_path = "/home/jsh9967/6_ni_exs_training/3_gemnet_train/2_re_jmoon/2_training/checkpoints/2025-04-13-17-32-00/best_checkpoint.pt"
    
    try:
        log(f"Loading GemNet model from: {checkpoint_path}")
        start_time = time.time()
        
        # Set default dtype to float32 to avoid type issues
        torch.set_default_dtype(torch.float32)
        
        # Initialize the calculator
        calculator = OCPCalculator(
            checkpoint_path=checkpoint_path,
            trainer='energy', 
            cpu=False
        )
        
        end_time = time.time()
        log(f"GemNet model loaded in {end_time - start_time:.2f} seconds")
        return calculator
    except Exception as e:
        log(f"Error loading GemNet model: {e}")
        import traceback
        traceback.print_exc()
        return None

def optimize_structure(atoms, calculator, fmax=0.05, steps=100, output_dir=None, name=None):
    """Pre-optimize structure using LBFGS before MD"""
    log(f"Pre-optimizing structure with LBFGS (max {steps} steps, fmax={fmax} eV/Å)...")
    atoms.calc = calculator
    
    if output_dir and name:
        log_file = os.path.join(output_dir, f"{name}_lbfgs.log")
        opt_traj = os.path.join(output_dir, f"{name}_lbfgs.traj")
        dyn = LBFGS(atoms, trajectory=opt_traj, logfile=log_file)
    else:
        dyn = LBFGS(atoms)
    
    start_time = time.time()
    try:
        dyn.run(fmax=fmax, steps=steps)
        converged = dyn.converged()
        final_forces = np.linalg.norm(atoms.get_forces(), axis=1).max()
    except Exception as e:
        log(f"Optimization error: {e}")
        converged = False
        final_forces = np.nan
    
    elapsed = time.time() - start_time
    log(f"LBFGS optimization completed in {elapsed:.1f} seconds")
    log(f"Converged: {converged}, Max force: {final_forces:.4f} eV/Å")
    
    if output_dir and name:
        # Save optimized structure
        opt_file = os.path.join(output_dir, f"{name}_optimized.vasp")
        write(opt_file, atoms, format='vasp')
        log(f"Optimized structure saved to {opt_file}")
    
    return converged, final_forces

def run_md_simulation_nvt(atoms, calculator, temperature, num_steps, time_step, 
                         friction, output_dir, name, fix_bottom=True):
    """Simple NVT molecular dynamics simulation with Langevin thermostat"""
    # Setup directories
    traj_dir = os.path.join(output_dir, "trajectories")
    log_dir = os.path.join(output_dir, "logs")
    
    for d in [traj_dir, log_dir, output_dir]:
        os.makedirs(d, exist_ok=True)
    
    # Setup output files
    traj_file = os.path.join(traj_dir, f"{name}.traj")
    log_file = os.path.join(log_dir, f"{name}.log")
    
    # Set calculator
    atoms.calc = calculator
    
    # If requested, fix bottom layers of the slab (CeO2)
    if fix_bottom:
        # Identify Ni atoms
        ni_indices = [i for i, symbol in enumerate(atoms.get_chemical_symbols()) if symbol == 'Ni']
        # Fix all CeO2 atoms
        fixed_indices = [i for i in range(len(atoms)) if i not in ni_indices]
        constraint = FixAtoms(indices=fixed_indices)
        atoms.set_constraint(constraint)
        log(f"Fixed {len(fixed_indices)} substrate atoms during MD")
    
    # Initialize velocities
    log(f"Initializing velocities at {temperature}K...")
    MaxwellBoltzmannDistribution(atoms, temperature_K=temperature)
    Stationary(atoms)
    
    # Setup dynamics
    dyn = Langevin(
        atoms,
        timestep=time_step*units.fs,
        temperature_K=temperature,
        friction=friction
    )
    
    # Setup proper MD Logger to log physical quantities
    md_logger = MDLogger(
        dyn,
        atoms,
        log_file,
        header=True,
        stress=False,
        peratom=False,
        mode='w'
    )
    
    # Create a custom progress logger with elapsed time
    class ProgressLogger:
        def __init__(self, dyn, num_steps, interval=500):
            self.interval = interval
            self.start_time = time.time()
            self.last_step = 0
            self.dyn = dyn
            self.num_steps = num_steps
            
        def __call__(self):
            step = self.dyn.get_number_of_steps()
            if step % self.interval == 0 and step != self.last_step:
                elapsed = time.time() - self.start_time
                log(f"Step {step}/{self.num_steps} ({step/self.num_steps*100:.1f}%) - Elapsed: {elapsed:.1f}s")
                self.last_step = step

    # Create trajectory file
    traj = Trajectory(traj_file, 'w', atoms)

    # Attach loggers to dynamics
    progress_logger = ProgressLogger(dyn, num_steps, interval=500)
    dyn.attach(progress_logger, interval=1)
    dyn.attach(md_logger, interval=100)  # Log data every 100 steps
    dyn.attach(traj.write, interval=100)
    
    # Run dynamics
    log("\nStarting MD simulation:")
    log(f"Temperature: {temperature} K")
    log(f"Number of steps: {num_steps}")
    log(f"Time step: {time_step} fs")
    log(f"Output trajectory: {traj_file}")
    log(f"Output log file: {log_file}")
    
    # Run the simulation
    md_start_time = time.time()
    dyn.run(steps=num_steps)
    md_run_time = time.time() - md_start_time
    
    log(f"\nSimulation completed in {md_run_time:.1f} seconds")
    traj.close()
    
    # Save final structure
    final_file = os.path.join(output_dir, f"{name}_final.vasp")
    write(final_file, atoms, format='vasp')
    log(f"Final structure saved to {final_file}")
    
    return traj_file, log_file

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run NVT MD simulation on Ni nanoparticle on CeO2')
    parser.add_argument('--np_size', type=int, default=5, 
                       help='Size parameter of Icosahedron (4 or 5)')
    parser.add_argument('--temperature', type=float, default=573.0,
                       help='Temperature for MD simulation in K')
    parser.add_argument('--steps', type=int, default=50000,
                       help='Number of MD steps')
    parser.add_argument('--time_step', type=float, default=1.0,
                       help='Time step in fs')
    parser.add_argument('--friction', type=float, default=0.002,
                       help='Friction coefficient for Langevin thermostat')
    parser.add_argument('--fix_substrate', type=bool, default=True,
                       help='Whether to fix the CeO2 substrate atoms')
    args = parser.parse_args()
    
    # Verify size parameter is valid
    if args.np_size not in [5]:
        log(f"ERROR: np_size must be 4 or 5, got {args.np_size}")
        sys.exit(1)
    
    # Setup input and output paths
    input_file = f"/home/jsh9967/6_ni_exs_training/3_gemnet_train/2_re_jmoon/5_NP_anchoring/1_loaded/np_structures/structures/Ni_Icosahedron_{args.np_size}_9x9_supported.vasp"
    output_dir = f"./md_results/Ni_Icosahedron_{args.np_size}_9x9_T{int(args.temperature)}K_"
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Check for CUDA availability
    device = "cuda" if torch.cuda.is_available() else "cpu"
    log(f"Using {device} for calculations")
    
    # Load GemNet calculator
    calculator = load_gemnet_calculator()
    if calculator is None:
        log("Failed to load GemNet calculator. Exiting.")
        sys.exit(1)
    
    # Load the supported nanoparticle structure
    try:
        if os.path.exists(input_file):
            log(f"Loading structure from: {input_file}")
            structure = read(input_file, format='vasp')
            
            # Count atoms by type
            ni_atoms = len([atom for atom in structure if atom.symbol == 'Ni'])
            ce_atoms = len([atom for atom in structure if atom.symbol == 'Ce'])
            o_atoms = len([atom for atom in structure if atom.symbol == 'O'])
            total_atoms = len(structure)
            
            log(f"Loaded structure with {total_atoms} atoms: {ni_atoms} Ni, {ce_atoms} Ce, {o_atoms} O atoms")
            
            # Set a name for the simulation
            system_name = f"Ni_Icosahedron_{args.np_size}_T{int(args.temperature)}"
            
            # Make sure periodic boundary conditions are properly set (typically x,y directions for a slab)
            structure.set_pbc([True, True, True])
            
            # Verify the cell dimensions are reasonable
            cell = structure.get_cell()
            log(f"Cell dimensions: {cell[0,0]:.2f} × {cell[1,1]:.2f} × {cell[2,2]:.2f} Å")
            
            # Check if any atoms have no neighbors within cutoff
            cutoff = 12.0  # GemNet cutoff
            nl = NeighborList([cutoff/2]*len(structure), self_interaction=False, bothways=True)
            nl.update(structure)
            neighbors_count = [len(nl.get_neighbors(i)[0]) for i in range(len(structure))]
            isolated = sum(1 for count in neighbors_count if count == 0)
            
            if isolated > 0:
                log(f"WARNING: {isolated} atoms have no neighbors within {cutoff}Å cutoff!")
                log("This will cause the GemNet model to fail")
            
            # Set tags (required by GemNet)
            if not any(structure.get_tags()):
                structure.set_tags(np.ones(len(structure), dtype=int))
            
            # Run LBFGS optimization
            log("Running LBFGS pre-optimization")
            optimize_structure(
                atoms=structure,
                calculator=calculator,
                fmax=0.03,  # Force tolerance in eV/Å
                steps=200,  # Maximum optimization steps
                output_dir=output_dir,
                name=system_name
            )
            
            # Then run the MD simulation
            log("\nRunning NVT molecular dynamics simulation")
            run_md_simulation_nvt(
                atoms=structure,
                calculator=calculator,
                temperature=args.temperature,
                num_steps=args.steps,
                time_step=args.time_step,
                friction=args.friction,
                output_dir=output_dir,
                name=system_name,
                fix_bottom=args.fix_substrate
            )
            
        else:
            log(f"ERROR: Structure file not found: {input_file}")
            sys.exit(1)
    except Exception as e:
        log(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    log("\nSimulation completed successfully!")

if __name__ == "__main__":
    main()