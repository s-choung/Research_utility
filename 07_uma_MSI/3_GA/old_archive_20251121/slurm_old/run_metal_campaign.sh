#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu2
#SBATCH --job-name=ga_metal_campaign
#SBATCH --time=72:00:00
#SBATCH --gres=gpu:1
#SBATCH -o ../logs/campaign_%x_%j.out
#SBATCH -e ../logs/campaign_%x_%j.err

# SLURM job script for single metal on all oxide slabs
# Usage: sbatch --export=METAL=Pt run_metal_campaign.sh

echo "=========================================="
echo "GA METAL CAMPAIGN"
echo "Host: $(hostname)"
echo "Started: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "=========================================="

# Check required environment variable
if [ -z "$METAL" ]; then
    echo "❌ Error: METAL environment variable must be set"
    echo "   Usage: sbatch --export=METAL=Pt run_metal_campaign.sh"
    exit 1
fi

echo "Metal: $METAL"
echo "Processing all 10 oxide slabs"
echo ""

# Environment setup
export OMP_NUM_THREADS=1
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_ALLOCATOR=cuda_malloc_async

StartTime=$(date +%s)

# Directories
BASE_DIR="/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA"
SCRIPT="${BASE_DIR}/scripts/ga_runner_all_slabs.py"
CONFIG_DIR="${BASE_DIR}/configs"
OUTPUT_BASE="${BASE_DIR}/output"

echo "Base directory: $BASE_DIR"
echo "Script: $SCRIPT"
echo "Config directory: $CONFIG_DIR"
echo "Output base: $OUTPUT_BASE"
echo ""

# Check files
if [ ! -f "$SCRIPT" ]; then
    echo "❌ Error: Script not found: $SCRIPT"
    exit 1
fi

if [ ! -d "$CONFIG_DIR" ]; then
    echo "❌ Error: Config directory not found: $CONFIG_DIR"
    exit 1
fi

# GPU info
echo "GPU Information:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv
echo ""

echo "=========================================="
echo "Starting GA campaign: ${METAL} on all slabs..."
echo "=========================================="
echo ""

cd "$BASE_DIR"

# Run GA campaign with unbuffered output
/home/jsh9967/anaconda3/envs/fairchem_v2/bin/python3 -u "$SCRIPT" \
    --metal "$METAL" \
    --n-metal 30 \
    --config-dir "$CONFIG_DIR" \
    --output-base "$OUTPUT_BASE" \
    --device cuda

EXIT_CODE=$?

echo ""
echo "=========================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Campaign completed successfully"

    # Show campaign summary
    SUMMARY_FILE="${OUTPUT_BASE}/${METAL}_campaign_summary.json"

    if [ -f "$SUMMARY_FILE" ]; then
        echo ""
        echo "Campaign Summary for ${METAL}:"
        /home/jsh9967/anaconda3/envs/fairchem_v2/bin/python3 -c "import json; d=json.load(open('$SUMMARY_FILE')); print(f\"  Completed: {d['completed']}/{d['total_slabs']} slabs\"); print(f\"  Duration: {d['total_duration_hours']:.2f} hours\"); best=min(d['results'], key=lambda x: x['best_energy']) if d['results'] else None; print(f\"  Best: {best['slab']}, E={best['best_energy']:.4f} eV\") if best else print('  No results')"
        echo ""
        echo "Campaign summary: $SUMMARY_FILE"
    fi
else
    echo "❌ Campaign failed with exit code: $EXIT_CODE"
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
