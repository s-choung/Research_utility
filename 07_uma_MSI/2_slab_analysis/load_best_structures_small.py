#!/usr/bin/env python3
"""
Load Best Surface Structures - Small Slabs (Test Set)
======================================================
This file defines how to load the most stable surface for each material
from the small slab test set.
For files with multiple terminations (frames), specifies the exact frame index.

Usage:
    from ase.io import read
    from load_best_structures_small import BEST_STRUCTURES

    # Load CeO2 best surface
    atoms = read(BEST_STRUCTURES['CeO2']['path'],
                 index=BEST_STRUCTURES['CeO2']['frame'])
"""

from pathlib import Path

# Slab directories
SLAB_DIR_0 = Path("/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs")
SLAB_DIR_1 = Path("/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs_restarted")

# Best surface structures with frame indices
BEST_STRUCTURES = {
    'Al2O3': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/Al2O3_001_4x4_relaxed.traj',
        'frame': 0,  # Frame 0 of 2 terminations
        'miller': (0, 0, 1),
        'termination': 0,
        'surface_energy': 0.1130,  # eV/Å²
        'n_terminations': 2,
        'source': 'original',
        'description': 'Al2O3 (001) surface'
    },

    'CaO': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/CaO_100_5x5_relaxed.traj',
        'frame': 0,  # Frame 0
        'miller': (1, 0, 0),
        'termination': 0,
        'surface_energy': 0.0267,  # eV/Å²
        'n_terminations': 1,
        'source': 'original',
        'description': 'CaO (100) surface'
    },

    'CeO2': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/CeO2_111_5x5_relaxed.traj',
        'frame': 1,  # Frame 1 of 2 terminations
        'miller': (1, 1, 1),
        'termination': 1,
        'surface_energy': 0.0273,  # eV/Å²
        'n_terminations': 2,
        'source': 'original',
        'description': 'CeO2 (111) surface'
    },

    'MgO': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/MgO_100_5x5_relaxed.traj',
        'frame': 0,  # Frame 0
        'miller': (1, 0, 0),
        'termination': 0,
        'surface_energy': 0.0146,  # eV/Å²
        'n_terminations': 1,
        'source': 'original',
        'description': 'MgO (100) surface'
    },

    'SiO2': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/SiO2_101_4x4_relaxed.traj',
        'frame': 3,  # Frame 3 of 4 terminations
        'miller': (1, 0, 1),
        'termination': 3,
        'surface_energy': 0.1199,  # eV/Å²
        'n_terminations': 4,
        'source': 'original',
        'description': 'SiO2 (101) surface'
    },

    'SnO2': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/SnO2_100_5x4_relaxed.traj',
        'frame': 1,  # Frame 1 of 2 terminations
        'miller': (1, 0, 0),
        'termination': 1,
        'surface_energy': 0.0421,  # eV/Å²
        'n_terminations': 2,
        'source': 'original',
        'description': 'SnO2 (100) surface'
    },

    'TiO2_anatase': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/TiO2_anatase_001_5x4_relaxed.traj',
        'frame': 1,  # Frame 1 of 2 terminations
        'miller': (0, 0, 1),
        'termination': 1,
        'surface_energy': -0.0303,  # eV/Å²
        'n_terminations': 2,
        'source': 'original',
        'description': 'TiO2_anatase anatase (001) surface'
    },

    'TiO2_rutile': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/TiO2_rutile_100_5x4_relaxed.traj',
        'frame': 1,  # Frame 1 of 2 terminations
        'miller': (1, 0, 0),
        'termination': 1,
        'surface_energy': 0.0204,  # eV/Å²
        'n_terminations': 2,
        'source': 'original',
        'description': 'TiO2_rutile rutile (100) surface'
    },

    'ZnO': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/ZnO_100_5x5_relaxed.traj',
        'frame': 0,  # Frame 0 of 2 terminations
        'miller': (1, 0, 0),
        'termination': 0,
        'surface_energy': 0.0474,  # eV/Å²
        'n_terminations': 2,
        'source': 'original',
        'description': 'ZnO (100) surface'
    },

    'ZrO2': {
        'path': '/DATA/user_scratch/jsh9967/5_uma_MSI/0_slab_gen_small/slabs/ZrO2_100_4x4_relaxed.traj',
        'frame': 1,  # Frame 1 of 3 terminations
        'miller': (1, 0, 0),
        'termination': 1,
        'surface_energy': 0.1015,  # eV/Å²
        'n_terminations': 3,
        'source': 'original',
        'description': 'ZrO2 (100) surface'
    },

}


def load_structure(material):
    """
    Load the best surface structure for a given material

    Parameters:
    -----------
    material : str
        Material name (e.g., 'CeO2', 'TiO2_anatase')

    Returns:
    --------
    atoms : ase.Atoms
        ASE Atoms object with the most stable surface
    """
    from ase.io import read

    if material not in BEST_STRUCTURES:
        raise ValueError(f"Material '{material}' not found. "
                        f"Available: {list(BEST_STRUCTURES.keys())}")

    info = BEST_STRUCTURES[material]
    atoms = read(info['path'], index=info['frame'])

    # Add metadata
    atoms.info['material'] = material
    atoms.info['miller_index'] = info['miller']
    atoms.info['termination'] = info['termination']
    atoms.info['surface_energy'] = info['surface_energy']

    return atoms


if __name__ == '__main__':
    """Print loading instructions for all materials"""

    print("=" * 80)
    print("BEST SURFACE STRUCTURES - SMALL SLABS - LOADING INSTRUCTIONS")
    print("=" * 80)
    print()
    print("Python code to load each structure:")
    print()

    for material, info in BEST_STRUCTURES.items():
        frame_comment = ""
        if info['n_terminations'] > 1:
            frame_comment = f"  # Frame {info['frame']} of {info['n_terminations']}"

        print(f"# {material}: {info['miller']} surface, γ = {info['surface_energy']:.4f} eV/Å²")
        print(f"{material}_slab = read('{info['path']}', index={info['frame']}){frame_comment}")
        print()
