#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu1
#SBATCH --job-name=ga_test_single
#SBATCH --time=2:00:00
#SBATCH --gres=gpu:1
#SBATCH -o /DATA/user_scratch/jsh9967/5_uma_MSI/3_GA/logs/test_single_%j.out
#SBATCH -e /DATA/user_scratch/jsh9967/5_uma_MSI/3_GA/logs/test_single_%j.err

# Quick test script - Run GA for Pt on small slabs (test set - 10 materials)
# This tests the PrepareDB -> DataConnection fix with fmax=1.0 and 10 metal atoms

echo "=========================================="
echo "GA SINGLE TEST RUN"
echo "Host: $(hostname)"
echo "Started: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "=========================================="
echo "Testing: Pt on small slabs (10 materials)"
echo "Purpose: Verify PrepareDB->DataConnection fix"
echo "Convergence: fmax=0.05, n_metal=30"
echo ""

# Environment setup
export OMP_NUM_THREADS=1
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_ALLOCATOR=cuda_malloc_async

StartTime=$(date +%s)

# Directories
BASE_DIR="/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA"
cd "$BASE_DIR"

# GPU info
echo "GPU Information:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
echo ""

echo "=========================================="
echo "Starting test GA run..."
echo "=========================================="
echo ""

# Run GA for Pt only (small slabs test set - 9 slabs)
# Using fewer metal atoms for smaller slab sizes
/home/jsh9967/anaconda3/envs/fairchem_v2/bin/python3 -u scripts/ga_runner_all_slabs.py \
    --metal Pt \
    --n-metal 30 \
    --config-dir configs \
    --output-base output \
    --device cuda

EXIT_CODE=$?

echo ""
echo "=========================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test run completed successfully"

    # Show results
    SUMMARY_FILE="output/Pt_campaign_summary.json"

    if [ -f "$SUMMARY_FILE" ]; then
        echo ""
        echo "Test Results:"
        /home/jsh9967/anaconda3/envs/fairchem_v2/bin/python3 -c "
import json
d = json.load(open('$SUMMARY_FILE'))
print(f\"  Completed: {d['completed']}/{d['total_slabs']} slabs\")
print(f\"  Duration: {d['total_duration_hours']:.2f} hours\")
if d['results']:
    best = min(d['results'], key=lambda x: x['best_energy'])
    print(f\"  Best: {best['slab']}, E={best['best_energy']:.4f} eV\")
"
        echo ""
        echo "Summary: $SUMMARY_FILE"
        echo ""
        echo "✓ PrepareDB->DataConnection fix is working!"
    fi
else
    echo "❌ Test run failed with exit code: $EXIT_CODE"
    echo ""
    echo "Check logs in: $BASE_DIR/logs/"
fi

EndTime=$(date +%s)
RUNTIME=$((EndTime - StartTime))
HOURS=$((RUNTIME / 3600))
MINUTES=$(((RUNTIME % 3600) / 60))
SECONDS=$((RUNTIME % 60))

echo ""
echo "Runtime: ${HOURS}h ${MINUTES}m ${SECONDS}s"
echo "Finished: $(date)"
echo "=========================================="

exit $EXIT_CODE
