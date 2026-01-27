#!/usr/bin/env python3
"""
Prepare Job Configurations
Generate individual job configuration files for all metal-slab combinations
"""

import json
from pathlib import Path

# Configuration
BASE_DIR = Path('/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA')
JOBS_DIR = BASE_DIR / 'jobs'
CONFIGS_DIR = BASE_DIR / 'configs'

# Metals to test
METALS = ['Pt', 'Au', 'Pd', 'Rh', 'Ni', 'Ru', 'Os', 'Ir']

# Oxide slabs
SLABS = [
    'Al2O3', 'CaO', 'CeO2', 'MgO', 'SiO2',
    'SnO2', 'TiO2_anatase', 'TiO2_rutile', 'ZnO', 'ZrO2'
]

# Number of metal atoms
N_METAL = 45


def main():
    """Generate job configuration files for all combinations"""

    # Create jobs directory
    JOBS_DIR.mkdir(parents=True, exist_ok=True)

    # Load configurations for reference
    with open(CONFIGS_DIR / 'metals_config.json', 'r') as f:
        metals_config = json.load(f)

    with open(CONFIGS_DIR / 'slabs_config.json', 'r') as f:
        slabs_config = json.load(f)

    print("="*70)
    print("GENERATING JOB CONFIGURATIONS")
    print("="*70)
    print(f"Metals: {len(METALS)}")
    print(f"Slabs: {len(SLABS)}")
    print(f"Total jobs: {len(METALS) * len(SLABS)}")
    print(f"Metal atoms per job: {N_METAL}")
    print(f"Output directory: {JOBS_DIR}")
    print("="*70)
    print()

    # Generate job files
    job_list = []
    job_id = 1

    for metal in METALS:
        for slab in SLABS:
            # Job configuration
            job_config = {
                'job_id': job_id,
                'metal': metal,
                'slab': slab,
                'n_metal': N_METAL,
                'metal_info': metals_config['metals'][metal],
                'slab_info': slabs_config['slabs'][slab],
                'output_dir': f'/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA/output/{metal}_{slab}',
                'job_name': f'{metal}_{slab}'
            }

            # Save individual job file
            job_file = JOBS_DIR / f'{metal}_{slab}.json'
            with open(job_file, 'w') as f:
                json.dump(job_config, f, indent=2)

            job_list.append(job_config)
            print(f"✓ Generated: {job_file.name} (ID: {job_id})")
            job_id += 1

    # Create master job list
    master_list = {
        'total_jobs': len(job_list),
        'n_metals': len(METALS),
        'n_slabs': len(SLABS),
        'metals': METALS,
        'slabs': SLABS,
        'n_metal_atoms': N_METAL,
        'jobs': job_list
    }

    master_file = JOBS_DIR / 'job_list.json'
    with open(master_file, 'w') as f:
        json.dump(master_list, f, indent=2)

    print()
    print("="*70)
    print("✅ JOB CONFIGURATION COMPLETE")
    print("="*70)
    print(f"Total job files: {len(job_list)}")
    print(f"Master list: {master_file}")
    print()

    # Print summary by metal
    print("Jobs by metal:")
    for metal in METALS:
        count = sum(1 for j in job_list if j['metal'] == metal)
        print(f"  {metal}: {count} jobs")

    print()

    # Print summary by slab
    print("Jobs by slab:")
    for slab in SLABS:
        count = sum(1 for j in job_list if j['slab'] == slab)
        print(f"  {slab}: {count} jobs")

    print()
    print("="*70)
    print("Next steps:")
    print("  1. Review job configurations in:", JOBS_DIR)
    print("  2. Submit jobs using: slurm/submit_all.sh")
    print("  3. Monitor progress: slurm/monitor_jobs.sh")
    print("="*70)
    print()


if __name__ == '__main__':
    main()
