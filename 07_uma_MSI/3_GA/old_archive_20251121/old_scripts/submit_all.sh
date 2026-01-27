#!/bin/bash
# Master submission script for all metal-on-oxide GA jobs
# Submits 80 jobs (8 metals × 10 slabs)

BASE_DIR="/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA"
SLURM_SCRIPT="${BASE_DIR}/slurm/run_metal_slab.sh"
LOGS_DIR="${BASE_DIR}/logs"

# Create logs directory
mkdir -p "$LOGS_DIR"

# Metals and slabs
METALS=("Pt" "Au" "Pd" "Rh" "Ni" "Ru" "Os" "Ir")
SLABS=("Al2O3" "CaO" "CeO2" "MgO" "SiO2" "SnO2" "TiO2_anatase" "TiO2_rutile" "ZnO" "ZrO2")

echo "=========================================="
echo "SUBMITTING GA JOBS"
echo "=========================================="
echo "Metals: ${#METALS[@]}"
echo "Slabs: ${#SLABS[@]}"
echo "Total jobs: $((${#METALS[@]} * ${#SLABS[@]}))"
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

# Submit all combinations
for metal in "${METALS[@]}"; do
    for slab in "${SLABS[@]}"; do
        job_name="ga_${metal}_${slab}"
        output_dir="${BASE_DIR}/output/${metal}_${slab}"
        summary_file="${output_dir}/${metal}_summary.json"

        # Check if already completed
        if [ -f "$summary_file" ]; then
            echo "⏭️  Skipping ${metal}_${slab} (already completed)"
            ((skipped++))
            continue
        fi

        # Submit job
        job_id=$(sbatch \
            --job-name="$job_name" \
            --export=METAL="$metal",SLAB="$slab" \
            "$SLURM_SCRIPT" 2>&1 | grep -oP '(?<=Submitted batch job )\d+')

        if [ -n "$job_id" ]; then
            echo "✓ Submitted: ${metal}_${slab} (Job ID: $job_id)"
            ((submitted++))
        else
            echo "❌ Failed to submit: ${metal}_${slab}"
        fi

        # Small delay to avoid overwhelming scheduler
        sleep 0.5
    done
done

echo ""
echo "=========================================="
echo "SUBMISSION COMPLETE"
echo "=========================================="
echo "Submitted: $submitted jobs"
echo "Skipped: $skipped jobs (already completed)"
echo "Total: $((submitted + skipped)) jobs"
echo ""
echo "Monitor jobs with:"
echo "  squeue -u $USER"
echo "  ${BASE_DIR}/slurm/monitor_jobs.sh"
echo ""
echo "Check logs in: $LOGS_DIR"
echo "=========================================="
