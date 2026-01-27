# Metal-on-Oxide GA Optimization

Genetic algorithm workflow for optimizing metal atom placement on oxide slab surfaces.

## Overview

- **Metals**: Pt, Au, Pd, Rh, Ni, Ru, Os, Ir (8 elements)
- **Oxide Slabs**: Al2O3, CaO, CeO2, MgO, SiO2, SnO2, TiO2 (anatase & rutile), ZnO, ZrO2 (10 surfaces)
- **Metal Atoms**: 45 atoms per optimization
- **Total Jobs**: 80 (8 metals × 10 slabs)

## Directory Structure

```
3_GA/
├── scripts/           # Python scripts
│   ├── ga_metal_oxide.py      # Main GA library
│   ├── ga_runner.py           # Job runner
│   └── prepare_jobs.py        # Job configuration generator
│
├── slurm/            # SLURM submission scripts
│   ├── run_metal_slab.sh      # Individual job script
│   ├── submit_all.sh          # Submit all 80 jobs
│   ├── submit_selective.sh    # Submit specific jobs
│   └── monitor_jobs.sh        # Monitor progress
│
├── configs/          # Configuration files
│   ├── metals_config.json     # Metal properties
│   ├── slabs_config.json      # Slab information
│   └── ga_params.json         # GA parameters
│
├── jobs/             # Job configurations (generated)
│   ├── Pt_Al2O3.json
│   ├── Pt_CaO.json
│   └── ... (80 files)
│
├── output/           # Results
│   ├── Pt_Al2O3/
│   │   ├── Pt_ga.db           # ASE database
│   │   ├── Pt_best.xyz        # Best structure
│   │   ├── Pt_best.traj       # Best structure (trajectory)
│   │   ├── Pt_top5.traj       # Top 5 structures
│   │   └── Pt_summary.json    # Results summary
│   └── ... (80 directories)
│
├── logs/             # SLURM logs
│   └── ga_*.out/err
│
└── analysis/         # Results analysis
    ├── collect_results.py     # Aggregate results
    ├── all_results.csv        # Complete dataset
    ├── metal_statistics.csv   # By metal
    ├── slab_statistics.csv    # By slab
    ├── energy_matrix.csv      # Pivot table
    └── summary_report.json    # Overall summary
```

## Quick Start

### 1. Prepare Job Configurations

```bash
cd /DATA/user_scratch/jsh9967/5_uma_MSI/3_GA
python3 scripts/prepare_jobs.py
```

This generates 80 job configuration files in `jobs/`.

### 2. Submit Jobs

**Option A: Submit all jobs**
```bash
cd slurm
bash submit_all.sh
```

**Option B: Submit specific jobs**
```bash
# Single metal on all slabs
bash submit_selective.sh --metal Pt

# Single slab with all metals
bash submit_selective.sh --slab CeO2

# Specific combination
bash submit_selective.sh --metal Pt --slab CeO2

# Multiple selections
bash submit_selective.sh --metals Pt,Au --slabs CeO2,MgO
```

### 3. Monitor Progress

```bash
# One-time check
bash slurm/monitor_jobs.sh

# Continuous monitoring (refreshes every 60s)
watch -n 60 bash slurm/monitor_jobs.sh

# SLURM queue
squeue -u $USER
```

### 4. Analyze Results

```bash
python3 analysis/collect_results.py
```

This generates:
- `all_results.csv`: Complete dataset
- `metal_statistics.csv`: Statistics by metal
- `slab_statistics.csv`: Statistics by slab
- `energy_matrix.csv`: Energy matrix (metal × slab)
- `summary_report.json`: Overall summary

## GA Parameters

From `configs/ga_params.json`:

```json
{
  "population_size": 20,
  "n_iterations": 15,
  "mutation_probability": 0.3,
  "crossover_probability": 0.7,
  "fmax_relaxation": 0.05,
  "max_steps_relax": 200
}
```

## Expected Runtime

- **Per job**: 2-4 hours (depends on slab size and complexity)
- **Total serial time**: ~240 GPU-hours
- **Parallel wall time**: ~24-48 hours (with sufficient GPUs)

## Output Files

Each completed job produces:

1. **`{METAL}_summary.json`**: Complete results summary
   - Best energy
   - Per-atom energy
   - Number of structures evaluated
   - Runtime statistics
   - GA parameters

2. **`{METAL}_best.xyz`**: Best structure (XYZ format)

3. **`{METAL}_best.traj`**: Best structure (ASE trajectory)

4. **`{METAL}_top5.traj`**: Top 5 structures

5. **`{METAL}_ga.db`**: Complete ASE database with all evaluated structures

## Troubleshooting

### Job Failed
Check log files in `logs/` directory:
```bash
tail -n 50 logs/ga_Pt_CeO2_<jobid>.err
```

### Rerun Specific Job
Delete the summary file and resubmit:
```bash
rm output/Pt_CeO2/Pt_summary.json
bash slurm/submit_selective.sh --metal Pt --slab CeO2
```

### Check Disk Space
```bash
du -sh output/
```

## Notes

- Oxide slabs are loaded from `load_best_structures.py` in `2_slab_analysis/`
- UMA model checkpoint: `/DATA/user_scratch/jsh9967/5_uma_MSI/utility/uma-s-1p1.pt`
- Jobs automatically skip if summary file exists (prevents duplicate work)
- All scripts use unbuffered Python output for real-time logging

## Citation

Based on the ASE genetic algorithm implementation:
- https://wiki.fysik.dtu.dk/ase/ase/ga.html
