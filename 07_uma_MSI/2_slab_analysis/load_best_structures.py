#!/usr/bin/env python3
"""
Load Best Surface Structures - Frame Index Reference
=====================================================
This file defines how to load the most stable surface for each material.
For files with multiple terminations (frames), specifies the exact frame index.

Usage:
    from ase.io import read
    from load_best_structures import BEST_STRUCTURES

    # Load CeO2 best surface
    atoms = read(BEST_STRUCTURES['CeO2']['path'],
                 index=BEST_STRUCTURES['CeO2']['frame'])
"""

from pathlib import Path

# Base directory
BASE_DIR = Path("/DATA/user_scratch/jsh9967/5_uma_MSI/1_slab_gen")

# Best surface structures with frame indices
BEST_STRUCTURES = {
    'Al2O3': {
        'path': str(BASE_DIR / 'slabs' / 'Al2O3_001_5x5_relaxed.traj'),
        'frame': 0,  # Frame 0 of 2 terminations
        'miller': (0, 0, 1),
        'termination': 0,
        'surface_energy': -4.2618,  # eV/Å²
        'n_terminations': 2,
        'description': 'Corundum (001) basal plane, oxygen-terminated'
    },

    'CaO': {
        'path': str(BASE_DIR / 'slabs' / 'CaO_110_4x4_relaxed.traj'),
        'frame': 0,  # Single frame
        'miller': (1, 1, 0),
        'termination': 0,
        'surface_energy': -1.4016,  # eV/Å²
        'n_terminations': 1,
        'description': 'Rock-salt (110) surface'
    },

    'CeO2': {
        'path': str(BASE_DIR / 'slabs' / 'CeO2_111_4x4_relaxed.traj'),
        'frame': 1,  # Frame 1 of 2 terminations (IMPORTANT!)
        'miller': (1, 1, 1),
        'termination': 1,
        'surface_energy': -2.1639,  # eV/Å²
        'n_terminations': 2,
        'description': 'Fluorite (111) surface, termination 1 is most stable'
    },

    'MgO': {
        'path': str(BASE_DIR / 'slabs' / 'MgO_110_5x5_relaxed.traj'),
        'frame': 0,  # Single frame
        'miller': (1, 1, 0),
        'termination': 0,
        'surface_energy': -1.6751,  # eV/Å²
        'n_terminations': 1,
        'description': 'Rock-salt (110) surface'
    },

    'SiO2': {
        'path': str(BASE_DIR / 'slabs' / 'SiO2_001_5x5_relaxed.traj'),
        'frame': 1,  # Frame 1 of 2 terminations
        'miller': (0, 0, 1),
        'termination': 1,
        'surface_energy': -4.2054,  # eV/Å²
        'n_terminations': 2,
        'description': 'β-cristobalite (001) surface'
    },

    'SnO2': {
        'path': str(BASE_DIR / 'slabs' / 'SnO2_100_5x4_relaxed.traj'),
        'frame': 1,  # Frame 1 of 2 terminations
        'miller': (1, 0, 0),
        'termination': 1,
        'surface_energy': -1.9596,  # eV/Å²
        'n_terminations': 2,
        'description': 'Rutile (100) surface, cassiterite'
    },

    'TiO2_anatase': {
        'path': str(BASE_DIR / 'slabs' / 'TiO2_anatase_100_6x5_relaxed.traj'),
        'frame': 0,  # Single frame
        'miller': (1, 0, 0),
        'termination': 0,
        'surface_energy': -4.2313,  # eV/Å²
        'n_terminations': 1,
        'description': 'Anatase (100) surface, metastable TiO2 polymorph'
    },

    'TiO2_rutile': {
        'path': str(BASE_DIR / 'slabs' / 'TiO2_rutile_001_5x4_relaxed.traj'),
        'frame': 0,  # Single frame
        'miller': (0, 0, 1),
        'termination': 0,
        'surface_energy': -3.5193,  # eV/Å²
        'n_terminations': 1,
        'description': 'Rutile (001) surface, stable TiO2 polymorph'
    },

    'ZnO': {
        'path': str(BASE_DIR / 'slabs' / 'ZnO_001_6x6_relaxed.traj'),
        'frame': 0,  # Frame 0 of 3 terminations
        'miller': (0, 0, 1),
        'termination': 0,
        'surface_energy': -1.7736,  # eV/Å²
        'n_terminations': 3,
        'description': 'Wurtzite (001) polar surface, Zn-terminated'
    },

    'ZrO2': {
        'path': str(BASE_DIR / 'slabs' / 'ZrO2_100_4x4_relaxed.traj'),
        'frame': 1,  # Frame 1 of 3 terminations
        'miller': (1, 0, 0),
        'termination': 1,
        'surface_energy': -1.6352,  # eV/Å²
        'n_terminations': 3,
        'description': 'Monoclinic (100) surface'
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

    Example:
    --------
    >>> from load_best_structures import load_structure
    >>> ceo2_slab = load_structure('CeO2')
    >>> print(f"Loaded {len(ceo2_slab)} atoms")
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


def print_structure_info(material):
    """Print detailed information about a material's best structure"""
    if material not in BEST_STRUCTURES:
        print(f"Material '{material}' not found.")
        return

    info = BEST_STRUCTURES[material]
    print(f"\n{material} - Best Surface Structure")
    print("=" * 70)
    print(f"  Path: {info['path']}")
    print(f"  Frame index: {info['frame']}")
    if info['n_terminations'] > 1:
        print(f"  Note: Frame {info['frame']} of {info['n_terminations']} terminations")
    print(f"  Miller index: {info['miller']}")
    print(f"  Termination: {info['termination']}")
    print(f"  Surface energy: {info['surface_energy']:.4f} eV/Å²")
    print(f"  Description: {info['description']}")
    print()


def load_all_structures():
    """
    Load all best surface structures

    Returns:
    --------
    structures : dict
        Dictionary mapping material names to ASE Atoms objects
    """
    structures = {}
    for material in BEST_STRUCTURES.keys():
        structures[material] = load_structure(material)
    return structures


if __name__ == '__main__':
    """Print loading instructions for all materials"""

    print("=" * 80)
    print("BEST SURFACE STRUCTURES - LOADING INSTRUCTIONS")
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

    print("=" * 80)
    print("ALTERNATIVE: Use the helper function")
    print("=" * 80)
    print()
    print("from load_best_structures import load_structure")
    print()
    print("# Load specific material")
    print("ceo2_slab = load_structure('CeO2')")
    print()
    print("# Load all materials")
    print("from load_best_structures import load_all_structures")
    print("all_slabs = load_all_structures()")
    print()

    print("=" * 80)
    print("IMPORTANT: Materials with Multiple Terminations")
    print("=" * 80)
    print()

    for material, info in BEST_STRUCTURES.items():
        if info['n_terminations'] > 1:
            print(f"✓ {material:15} - Frame {info['frame']} of {info['n_terminations']} "
                  f"(Miller {info['miller']}, term {info['termination']})")

    print()
