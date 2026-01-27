#!/bin/bash
# Selective submission script for specific metals or slabs
# Usage examples:
#   ./submit_selective.sh --metal Pt          # Submit all Pt jobs
#   ./submit_selective.sh --slab CeO2         # Submit all CeO2 jobs
#   ./submit_selective.sh --metal Pt --slab CeO2  # Submit single job

BASE_DIR="/DATA/user_scratch/jsh9967/5_uma_MSI/3_GA"
SLURM_SCRIPT="${BASE_DIR}/slurm/run_metal_slab.sh"
LOGS_DIR="${BASE_DIR}/logs"

# All available options
ALL_METALS=("Pt" "Au" "Pd" "Rh" "Ni" "Ru" "Os" "Ir")
ALL_SLABS=("Al2O3" "CaO" "CeO2" "MgO" "SiO2" "SnO2" "TiO2_anatase" "TiO2_rutile" "ZnO" "ZrO2")

# Parse arguments
SELECTED_METALS=()
SELECTED_SLABS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --metal)
            SELECTED_METALS+=("$2")
            shift 2
            ;;
        --slab)
            SELECTED_SLABS+=("$2")
            shift 2
            ;;
        --metals)
            IFS=',' read -ra METALS_ARRAY <<< "$2"
            SELECTED_METALS+=("${METALS_ARRAY[@]}")
            shift 2
            ;;
        --slabs)
            IFS=',' read -ra SLABS_ARRAY <<< "$2"
            SELECTED_SLABS+=("${SLABS_ARRAY[@]}")
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --metal <metal>       Submit jobs for specific metal"
            echo "  --metals <m1,m2,...>  Submit jobs for multiple metals (comma-separated)"
            echo "  --slab <slab>         Submit jobs for specific slab"
            echo "  --slabs <s1,s2,...>   Submit jobs for multiple slabs (comma-separated)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Available metals: ${ALL_METALS[*]}"
            echo "Available slabs: ${ALL_SLABS[*]}"
            echo ""
            echo "Examples:"
            echo "  $0 --metal Pt                    # All Pt jobs"
            echo "  $0 --slab CeO2                   # All CeO2 jobs"
            echo "  $0 --metal Pt --slab CeO2        # Single Pt-CeO2 job"
            echo "  $0 --metals Pt,Au --slabs CeO2,MgO  # 4 jobs"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Default to all if not specified
if [ ${#SELECTED_METALS[@]} -eq 0 ]; then
    SELECTED_METALS=("${ALL_METALS[@]}")
fi

if [ ${#SELECTED_SLABS[@]} -eq 0 ]; then
    SELECTED_SLABS=("${ALL_SLABS[@]}")
fi

# Create logs directory
mkdir -p "$LOGS_DIR"

echo "=========================================="
echo "SELECTIVE GA JOB SUBMISSION"
echo "=========================================="
echo "Metals: ${SELECTED_METALS[*]}"
echo "Slabs: ${SELECTED_SLABS[*]}"
echo "Total jobs: $((${#SELECTED_METALS[@]} * ${#SELECTED_SLABS[@]}))"
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

# Submit selected combinations
for metal in "${SELECTED_METALS[@]}"; do
    for slab in "${SELECTED_SLABS[@]}"; do
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

        sleep 0.5
    done
done

echo ""
echo "=========================================="
echo "SUBMISSION COMPLETE"
echo "=========================================="
echo "Submitted: $submitted jobs"
echo "Skipped: $skipped jobs"
echo ""
echo "Monitor with: squeue -u $USER"
echo "=========================================="
