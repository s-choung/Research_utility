#!/bin/bash
# Submit GA campaigns - one job per metal (8 jobs total)
# Each job processes all 10 oxide slabs for that metal

BASE_DIR="/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA"
SLURM_SCRIPT="${BASE_DIR}/slurm/run_metal_campaign.sh"
LOGS_DIR="${BASE_DIR}/logs"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Metals to process
METALS=("Ir" "Pt" "Au" "Pd" "Rh" "Ni" "Ru")

echo "=========================================="
echo "SUBMITTING GA CAMPAIGNS"
echo "=========================================="
echo "Metals: ${#METALS[@]}"
echo "Slabs per metal: 10"
echo "Total jobs: ${#METALS[@]}"
echo "Script: $SLURM_SCRIPT"
echo "Logs: $LOGS_DIR"
echo "=========================================="
echo ""

# Check if script exists
if [ ! -f "$SLURM_SCRIPT" ]; then
    echo "❌ Error: SLURM script not found: $SLURM_SCRIPT"
    exit 1
fi

# Submission counter
submitted=0
skipped=0

# Submit campaign for each metal
for metal in "${METALS[@]}"; do
    job_name="ga_${metal}_campaign"
    summary_file="${BASE_DIR}/output/${metal}_campaign_summary.json"

    # Check if already completed
    if [ -f "$summary_file" ]; then
        completed=$(python3 -c "import json; d=json.load(open('$summary_file')); print(d['completed'])")
        if [ "$completed" == "10" ]; then
            echo "⏭️  Skipping ${metal} (campaign already completed)"
            ((skipped++))
            continue
        fi
    fi

    # Submit job
    job_id=$(sbatch \
        --job-name="$job_name" \
        --export=METAL="$metal" \
        "$SLURM_SCRIPT" 2>&1 | grep -oP '(?<=Submitted batch job )\d+')

    if [ -n "$job_id" ]; then
        echo "✓ Submitted: ${metal} campaign (Job ID: $job_id)"
        ((submitted++))
    else
        echo "❌ Failed to submit: ${metal} campaign"
    fi

    # Small delay
    sleep 0.5
done

echo ""
echo "=========================================="
echo "SUBMISSION COMPLETE"
echo "=========================================="
echo "Submitted: $submitted jobs"
echo "Skipped: $skipped jobs (already completed)"
echo "Total: $((submitted + skipped)) metals"
echo ""
echo "Each job will process 10 oxide slabs sequentially"
echo "Expected runtime: ~10-15 hours per job (30 metal atoms, fmax=0.05)"
echo ""
echo "Monitor jobs with:"
echo "  squeue -u $USER"
echo "  tail -f ${LOGS_DIR}/campaign_ga_Pt_campaign_JOBID.out"
echo ""
echo "Check logs in: $LOGS_DIR"
echo "=========================================="
