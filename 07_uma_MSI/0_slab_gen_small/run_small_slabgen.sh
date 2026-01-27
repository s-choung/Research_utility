#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu2
#SBATCH --job-name=small_slabgen
#SBATCH --time=24:00:00
#SBATCH -o slurm_logs/small_slabgen.%N.%j.out
#SBATCH -e slurm_logs/small_slabgen.%N.%j.err
#SBATCH --gres=gpu:1

# SMALL Slab Generation & Energy Evaluation Script
# Generates SMALL slabs (<2nm lateral, thin layers) for single GPU runs
# No chunking needed - all slabs fit in single GPU memory

# Create output directories
mkdir -p slurm_logs
mkdir -p slabs

echo "=========================================="
echo "SMALL SLAB GENERATION & EVALUATION JOB"
echo "Lateral size: <2nm | Thin layers"
echo "Host: $(hostname) | Started: $(date)"
echo "=========================================="

# Environment setup (assumes fairchem_v2 is already active)
export OMP_NUM_THREADS=1
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_ALLOCATOR=cuda_malloc_async

StartTime=$(date +%s)
cd $SLURM_SUBMIT_DIR

echo "Python: $(which python)"
echo "Python version: $(python --version)"
echo "Conda env: $CONDA_DEFAULT_ENV"
echo ""

# Generate slabs
python generate_slabs.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Slab generation completed successfully"
    touch COMPLETED
else
    echo ""
    echo "❌ Slab generation failed"
    touch FAILED
    exit 1
fi

EndTime=$(date +%s)
RUNTIME=$((EndTime - StartTime))
HOURS=$((RUNTIME / 3600))
MINUTES=$(((RUNTIME % 3600) / 60))
SECONDS=$((RUNTIME % 60))

echo ""
echo "=========================================="
echo "JOB COMPLETED"
echo "Runtime: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "Finished: $(date)"
echo "=========================================="
echo ""
echo "Output files:"
echo "  - Summary: slab_generation_summary.txt"
echo "  - Generated slabs: slabs/*.traj"
echo "  - Relaxed slabs: slabs/*_relaxed.traj"
echo "  - Energy log: energy_evaluation.log"
echo "=========================================="
