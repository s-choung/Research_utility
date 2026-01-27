#!/bin/bash
# Submit GA campaign with flexible atom configurations

# Default values
N_METAL=45
N_OXIDE=0
METALS="Pt" # Au Pd Rh Ni Ru Os Ir
SLABS="Al2O3" # CaO CeO2 MgO SiO2 SnO2 TiO2_anatase TiO2_rutile ZnO ZrO2

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --n-metal)
            N_METAL="$2"
            shift 2
            ;;
        --n-oxide)
            N_OXIDE="$2"
            shift 2
            ;;
        --metals)
            METALS="$2"
            shift 2
            ;;
        --slabs)
            SLABS="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --n-metal N     Number of metal atoms (default: 45)"
            echo "  --n-oxide N     Number of oxide atoms (default: 0)"
            echo "  --metals LIST   Space-separated list of metals"
            echo "  --slabs LIST    Space-separated list of slabs"
            echo ""
            echo "Examples:"
            echo "  # Submit all 80 jobs with 45 metal atoms"
            echo "  $0 --n-metal 45"
            echo ""
            echo "  # Submit only Pt on all slabs with 30 atoms"
            echo "  $0 --n-metal 30 --metals Pt"
            echo ""
            echo "  # Submit Pt and Au on CeO2 and MgO with 60 atoms"
            echo "  $0 --n-metal 60 --metals \"Pt Au\" --slabs \"CeO2 MgO\""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Create atom configuration string
ATOM_CONFIG="M${N_METAL}"
if [ $N_OXIDE -gt 0 ]; then
    ATOM_CONFIG="${ATOM_CONFIG}O${N_OXIDE}"
fi

# Create logs directory if it doesn't exist
mkdir -p ../logs

echo "=========================================="
echo "GA CAMPAIGN SUBMISSION"
echo "=========================================="
echo "Configuration: $ATOM_CONFIG"
echo "Metals: $METALS"
echo "Slabs: $SLABS"
echo "=========================================="

# Counter for jobs
JOB_COUNT=0
JOB_IDS=""

# Submit jobs for each metal-slab combination
for METAL in $METALS; do
    for SLAB in $SLABS; do
        # Check if job already completed
        OUTPUT_DIR="../runs_${ATOM_CONFIG}/${METAL}_${SLAB}"
        SUMMARY_FILE="${OUTPUT_DIR}/${METAL}_summary.json"

        if [ -f "$SUMMARY_FILE" ]; then
            echo "⚠ Skipping ${METAL}_${SLAB} (already completed)"
            continue
        fi

        # Submit job
        echo -n "Submitting ${ATOM_CONFIG}_${METAL}_${SLAB}... "

        JOB_ID=$(sbatch \
            --job-name="ga_${ATOM_CONFIG}_${METAL}_${SLAB}" \
            --output="../logs/${ATOM_CONFIG}_${METAL}_${SLAB}_%j.out" \
            --error="../logs/${ATOM_CONFIG}_${METAL}_${SLAB}_%j.err" \
            submit_ga.sh \
            --metal $METAL \
            --slab $SLAB \
            --n-metal $N_METAL \
            --n-oxide $N_OXIDE \
            2>&1 | awk '{print $4}')

        if [ -n "$JOB_ID" ]; then
            echo "✓ Job ID: $JOB_ID"
            JOB_IDS="$JOB_IDS $JOB_ID"
            JOB_COUNT=$((JOB_COUNT + 1))
        else
            echo "❌ Failed to submit"
        fi

        # Small delay to avoid overwhelming scheduler
        sleep 0.5
    done
done

echo "=========================================="
echo "✓ SUBMISSION COMPLETE"
echo "=========================================="
echo "Total jobs submitted: $JOB_COUNT"
echo "Configuration: $ATOM_CONFIG"
echo ""
echo "Monitor progress with:"
echo "  squeue -u $USER"
echo "  watch -n 60 'squeue -u $USER | grep ga_${ATOM_CONFIG}'"
echo ""
echo "Check logs in: ../logs/"
echo "Results in: ../runs_${ATOM_CONFIG}/"
echo "==========================================="