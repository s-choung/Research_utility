#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu1
#SBATCH --job-name=slabs_ch1
#SBATCH --time=96:00:00
#SBATCH -o slurm_logs/slabs_chunk1.%N.%j.out
#SBATCH -e slurm_logs/slabs_chunk1.%N.%j.err
#SBATCH --gres=gpu:1

# Chunk 1: MgO, CaO

mkdir -p slurm_logs
mkdir -p slabs

echo "=========================================="
echo "SLAB GENERATION - CHUNK 1 (MgO, CaO)"
echo "Host: $(hostname) | Started: $(date)"
echo "=========================================="

export OMP_NUM_THREADS=1
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_ALLOCATOR=cuda_malloc_async

StartTime=$(date +%s)
cd $SLURM_SUBMIT_DIR

echo "Python: $(which python)"
echo "Python version: $(python --version)"
echo "Conda env: $CONDA_DEFAULT_ENV"
echo ""

python restart_failed.py #generate_slabs_chunk.py 4

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Chunk 1 completed successfully"
    touch CHUNK1_COMPLETED
else
    echo ""
    echo "❌ Chunk 1 failed"
    touch CHUNK1_FAILED
    exit 1
fi

EndTime=$(date +%s)
RUNTIME=$((EndTime - StartTime))
HOURS=$((RUNTIME / 3600))
MINUTES=$(((RUNTIME % 3600) / 60))
SECONDS=$((RUNTIME % 60))

echo ""
echo "=========================================="
echo "CHUNK 1 COMPLETED"
echo "Runtime: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "Finished: $(date)"
echo "=========================================="
