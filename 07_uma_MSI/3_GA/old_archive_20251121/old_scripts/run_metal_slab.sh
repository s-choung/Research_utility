#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu1
#SBATCH --job-name=ga_metal_oxide
#SBATCH --time=48:00:00
#SBATCH --gres=gpu:1
#SBATCH -o ../logs/ga_%x_%j.out
#SBATCH -e ../logs/ga_%x_%j.err

# SLURM job script for metal-on-oxide GA optimization
# Usage: sbatch --export=METAL=Pt,SLAB=CeO2 run_metal_slab.sh

echo "=========================================="
echo "GA METAL-ON-OXIDE OPTIMIZATION"
echo "Host: $(hostname)"
echo "Started: $(date)"
echo "Job ID: $SLURM_JOB_ID"
echo "Job Name: $SLURM_JOB_NAME"
echo "=========================================="

# Check required environment variables
if [ -z "$METAL" ] || [ -z "$SLAB" ]; then
    echo "❌ Error: METAL and SLAB environment variables must be set"
    echo "   Usage: sbatch --export=METAL=Pt,SLAB=CeO2 run_metal_slab.sh"
    exit 1
fi

echo "Metal: $METAL"
echo "Slab: $SLAB"
echo ""

# Environment setup
export OMP_NUM_THREADS=1
export TF_FORCE_GPU_ALLOW_GROWTH=true
export TF_GPU_ALLOCATOR=cuda_malloc_async

StartTime=$(date +%s)

# Directories
BASE_DIR="/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA"
SCRIPT="${BASE_DIR}/scripts/ga_runner.py"
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
echo "Starting GA optimization: ${METAL} on ${SLAB}..."
echo "=========================================="
echo ""

cd "$BASE_DIR"

# Run GA with unbuffered output (use full Python path from fairchem_v2 env)
/home/jsh9967/anaconda3/envs/fairchem_v2/bin/python3 -u "$SCRIPT" \
    --metal "$METAL" \
    --slab "$SLAB" \
    --n-metal 45 \
    --config-dir "$CONFIG_DIR" \
    --output-base "$OUTPUT_BASE" \
    --device cuda

EXIT_CODE=$?

echo ""
echo "=========================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ GA optimization completed successfully"

    # Show results
    OUTPUT_DIR="${OUTPUT_BASE}/${METAL}_${SLAB}"
    SUMMARY_FILE="${OUTPUT_DIR}/${METAL}_summary.json"

    if [ -f "$SUMMARY_FILE" ]; then
        echo ""
        echo "Results for ${METAL} on ${SLAB}:"
        /home/jsh9967/anaconda3/envs/fairchem_v2/bin/python3 -c "import json; d=json.load(open('$SUMMARY_FILE')); print(f\"  Best energy: {d['best_energy']:.4f} eV\"); print(f\"  Per atom: {d['best_energy_per_metal']:.4f} eV/atom\"); print(f\"  Duration: {d['duration_hours']:.2f} hours\"); print(f\"  Structures: {d['total_structures']}\")"
        echo ""
        echo "Output directory: $OUTPUT_DIR"
    fi
else
    echo "❌ GA optimization failed with exit code: $EXIT_CODE"
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
