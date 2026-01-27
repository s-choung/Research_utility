#!/bin/bash
#SBATCH --job-name=ga_MxOy
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu2
#SBATCH --job-name=ga_MxOy
#SBATCH --time=48:00:00
#SBATCH --gres=gpu:1
#SBATCH -o logs/%x_%j.out
#SBATCH -e logs/%x_%j.err

# Flexible GA submission script for MxOy configurations
# Usage: sbatch submit_ga.sh --metal Pt --slab CeO2 --n-metal 45

# Parse arguments
METAL=""
SLAB=""
N_METAL=45
N_OXIDE=0
DEVICE="cuda"

while [[ $# -gt 0 ]]; do
    case $1 in
        --metal)
            METAL="$2"
            shift 2
            ;;
        --slab)
            SLAB="$2"
            shift 2
            ;;
        --n-metal)
            N_METAL="$2"
            shift 2
            ;;
        --n-oxide)
            N_OXIDE="$2"
            shift 2
            ;;
        --device)
            DEVICE="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$METAL" ] || [ -z "$SLAB" ]; then
    echo "Error: --metal and --slab are required"
    echo "Usage: sbatch submit_ga.sh --metal Pt --slab CeO2 --n-metal 45"
    exit 1
fi

# Create atom configuration string
ATOM_CONFIG="M${N_METAL}"
if [ $N_OXIDE -gt 0 ]; then
    ATOM_CONFIG="${ATOM_CONFIG}O${N_OXIDE}"
fi

# Update job name
#SBATCH --job-name=ga_${ATOM_CONFIG}_${METAL}_${SLAB}

# Environment setup
echo "=========================================="
echo "GA JOB: ${ATOM_CONFIG}_${METAL}_${SLAB}"
echo "=========================================="
echo "Metal: $METAL ($N_METAL atoms)"
echo "Slab: $SLAB"
echo "Oxide atoms: $N_OXIDE"
echo "Device: $DEVICE"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Start: $(date)"
echo "=========================================="

# Load modules (adjust as needed for your cluster)
module load python/3.9
module load cuda/11.8
module load gcc/11.2

# Activate environment (adjust path as needed)
source /DATA/user_scratch/jsh9967/5_uma_MSI/venv_fair/bin/activate

# Change to project directory
cd /DATA/user_scratch/jsh9967/5_uma_MSI/3_GA

# Run GA optimization
echo "Starting GA optimization..."
python3 run_ga.py \
    --single \
    --metal $METAL \
    --slab $SLAB \
    --n-metal $N_METAL \
    --n-oxide $N_OXIDE \
    --device $DEVICE

# Check exit status
if [ $? -eq 0 ]; then
    echo "=========================================="
    echo "✓ JOB COMPLETED SUCCESSFULLY"
    echo "End: $(date)"
    echo "=========================================="
else
    echo "=========================================="
    echo "❌ JOB FAILED"
    echo "End: $(date)"
    echo "=========================================="
    exit 1
fi