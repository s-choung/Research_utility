#!/bin/bash
#SBATCH --job-name=ga_campaign
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --partition=snu-gpu2
#SBATCH --time=72:00:00
#SBATCH --gres=gpu:1
#SBATCH -o logs/ga_M%a_%x_%j.out
#SBATCH -e logs/ga_M%a_%x_%j.err

# Single metal campaign - runs all 10 slabs sequentially
# Usage: sbatch submit_metal_campaign.sh --metal Pt --n-metal 40

# Parse arguments
METAL=""
N_METAL=40
N_OXIDE=0
DEVICE="cuda"

while [[ $# -gt 0 ]]; do
    case $1 in
        --metal)
            METAL="$2"
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

# Validate
if [ -z "$METAL" ]; then
    echo "Error: --metal is required"
    exit 1
fi

# All slabs to process
SLABS="Al2O3_001 CaO_100 CeO2_111 MgO_100 SiO2_101 SnO2_100 TiO2_anatase_001 TiO2_rutile_100 ZnO_100 ZrO2_100"

echo "=========================================="
echo "GA METAL CAMPAIGN: $METAL"
echo "=========================================="
echo "Metal: $METAL ($N_METAL atoms)"
echo "Slabs: 10 oxides"
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $(hostname)"
echo "Start: $(date)"
echo "=========================================="

# Activate environment
source /home/jsh9967/anaconda3/etc/profile.d/conda.sh
conda activate fairchem_v2

# Change to project directory
cd /DATA/user_scratch/jsh9967/5_uma_MSI/3_GA

# Process each slab
COMPLETED=0
FAILED=0

for SLAB in $SLABS; do
    echo ""
    echo "##################################################"
    echo "# Processing: $METAL on $SLAB"
    echo "##################################################"

    python3 run_ga.py \
        --single \
        --metal $METAL \
        --slab $SLAB \
        --n-metal $N_METAL \
        --n-oxide $N_OXIDE \
        --device $DEVICE

    if [ $? -eq 0 ]; then
        echo "✓ Completed: $METAL on $SLAB"
        COMPLETED=$((COMPLETED + 1))
    else
        echo "❌ Failed: $METAL on $SLAB"
        FAILED=$((FAILED + 1))
    fi
done

echo ""
echo "=========================================="
echo "CAMPAIGN COMPLETE: $METAL"
echo "=========================================="
echo "Completed: $COMPLETED/10"
echo "Failed: $FAILED/10"
echo "End: $(date)"
echo "=========================================="

if [ $FAILED -gt 0 ]; then
    exit 1
fi
