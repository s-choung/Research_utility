#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu2
#SBATCH --job-name=slab_large
#SBATCH --time=24:00:00
#SBATCH -o logs/slabgen.%N.%j.out
#SBATCH -e logs/slabgen.%N.%j.err
#SBATCH --gres=gpu:1

# Large Slab Generation with Relaxation

echo "=========================================="
echo "LARGE SLAB GENERATION WITH RELAXATION"
echo "Host: $(hostname) | Started: $(date)"
echo "GPU: $CUDA_VISIBLE_DEVICES"
echo "=========================================="

# Environment
export OMP_NUM_THREADS=1

cd $SLURM_SUBMIT_DIR

echo "Python: $(which python)"
echo "Conda env: $CONDA_DEFAULT_ENV"
echo ""

# Create logs directory and clean previous output
mkdir -p logs
rm -rf slabs_large

# Generate and relax slabs (unbuffered output)
python -u generate_slabs.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Slab generation completed"
else
    echo ""
    echo "❌ Slab generation failed"
    exit 1
fi

echo ""
echo "=========================================="
echo "COMPLETED: $(date)"
echo "Output: slabs_large/"
echo "=========================================="
