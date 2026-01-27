#!/bin/bash
# Monitor GA job progress

BASE_DIR="/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA"
OUTPUT_BASE="${BASE_DIR}/output"
JOBS_DIR="${BASE_DIR}/jobs"

METALS=("Pt" "Au" "Pd" "Rh" "Ni" "Ru" "Os" "Ir")
SLABS=("Al2O3" "CaO" "CeO2" "MgO" "SiO2" "SnO2" "TiO2_anatase" "TiO2_rutile" "ZnO" "ZrO2")

TOTAL_JOBS=$((${#METALS[@]} * ${#SLABS[@]}))

echo "=========================================="
echo "GA JOB MONITORING"
echo "$(date)"
echo "=========================================="
echo ""

# Check SLURM queue
echo "Current SLURM jobs:"
squeue -u $USER -o "%.10i %.12j %.8T %.10M %.6D" | grep "ga_"
echo ""

# Count job statuses
completed=0
running=0
pending=0
failed=0

for metal in "${METALS[@]}"; do
    for slab in "${SLABS[@]}"; do
        output_dir="${OUTPUT_BASE}/${metal}_${slab}"
        summary_file="${output_dir}/${metal}_summary.json"

        if [ -f "$summary_file" ]; then
            ((completed++))
        elif squeue -u $USER -n "ga_${metal}_${slab}" -h -o "%T" | grep -q "RUNNING"; then
            ((running++))
        elif squeue -u $USER -n "ga_${metal}_${slab}" -h -o "%T" | grep -q "PENDING"; then
            ((pending++))
        fi
    done
done

failed=$((TOTAL_JOBS - completed - running - pending))

echo "=========================================="
echo "JOB STATISTICS"
echo "=========================================="
echo "Total jobs: $TOTAL_JOBS"
echo "Completed: $completed"
echo "Running: $running"
echo "Pending: $pending"
echo "Not submitted/Failed: $failed"
echo ""

# Progress bar
percent=$((completed * 100 / TOTAL_JOBS))
bar_length=50
filled=$((percent * bar_length / 100))
empty=$((bar_length - filled))

printf "Progress: ["
printf "%${filled}s" | tr ' ' '='
printf "%${empty}s" | tr ' ' '-'
printf "] %d%%\n" "$percent"
echo ""

# Show completed jobs summary
if [ $completed -gt 0 ]; then
    echo "=========================================="
    echo "COMPLETED JOBS ($completed)"
    echo "=========================================="

    for metal in "${METALS[@]}"; do
        for slab in "${SLABS[@]}"; do
            summary_file="${OUTPUT_BASE}/${metal}_${slab}/${metal}_summary.json"

            if [ -f "$summary_file" ]; then
                energy=$(python3 -c "import json; d=json.load(open('$summary_file')); print(f\"{d['best_energy']:.4f}\")")
                duration=$(python3 -c "import json; d=json.load(open('$summary_file')); print(f\"{d['duration_hours']:.2f}\")")
                echo "  ${metal}_${slab}: E = ${energy} eV (${duration}h)"
            fi
        done
    done
    echo ""
fi

# Show running jobs details
if [ $running -gt 0 ]; then
    echo "=========================================="
    echo "RUNNING JOBS ($running)"
    echo "=========================================="
    squeue -u $USER -n "ga_*" -h -o "%.12j %.8T %.10M %.6D %R" | while read line; do
        echo "  $line"
    done
    echo ""
fi

echo "=========================================="
echo "Refresh monitoring:"
echo "  watch -n 60 ${BASE_DIR}/slurm/monitor_jobs.sh"
echo "=========================================="
