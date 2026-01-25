#!/bin/bash
# Script to run TPC-DI DIGen on Dataproc cluster via SSH or initialization action
# This script can be used as a Dataproc initialization action or run via SSH

set -e

# Configuration
SCALE_FACTOR=${1:-1}
GCS_BUCKET=${2:-"your-tpc-di-bucket"}
GCS_RAW_PATH=${3:-"raw"}
PROJECT_ID=${4:-"your-project-id"}
CLUSTER_NAME=${5:-"tpc-di-cluster"}
REGION=${6:-"us-central1"}

# Path to the setup script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup_and_run_digen.sh"

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    log_error "gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Method 1: Run as Dataproc initialization action
run_as_init_action() {
    log_info "Running DIGen as Dataproc initialization action..."
    
    # Upload setup script to GCS
    GCS_SCRIPT_PATH="gs://${GCS_BUCKET}/scripts/setup_and_run_digen.sh"
    log_info "Uploading setup script to ${GCS_SCRIPT_PATH}..."
    gsutil cp "${SETUP_SCRIPT}" "${GCS_SCRIPT_PATH}"
    
    # Create cluster with initialization action
    log_info "Creating Dataproc cluster with initialization action..."
    gcloud dataproc clusters create "${CLUSTER_NAME}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --initialization-actions="${GCS_SCRIPT_PATH}" \
        --initialization-action-timeout=2h \
        --metadata="SCALE_FACTOR=${SCALE_FACTOR},GCS_BUCKET=${GCS_BUCKET},GCS_RAW_PATH=${GCS_RAW_PATH},PROJECT_ID=${PROJECT_ID}" \
        --num-workers=2 \
        --worker-machine-type=n1-standard-4 \
        --master-machine-type=n1-standard-4
    
    log_info "Cluster created. Check logs for DIGen execution."
}

# Method 2: SSH into master and run script
run_via_ssh() {
    log_info "Running DIGen via SSH to Dataproc master..."
    
    # Get master node name
    MASTER_NODE="${CLUSTER_NAME}-m"
    
    log_info "SSHing into ${MASTER_NODE}..."
    log_info "You will need to manually run the setup script after SSH."
    
    # Copy script to master
    gcloud compute scp "${SETUP_SCRIPT}" "${MASTER_NODE}:/tmp/" \
        --zone="${REGION}-a" \
        --project="${PROJECT_ID}"
    
    # SSH and run
    gcloud compute ssh "${MASTER_NODE}" \
        --zone="${REGION}-a" \
        --project="${PROJECT_ID}" \
        --command="chmod +x /tmp/setup_and_run_digen.sh && \
                   SCALE_FACTOR=${SCALE_FACTOR} \
                   GCS_BUCKET=${GCS_BUCKET} \
                   GCS_RAW_PATH=${GCS_RAW_PATH} \
                   PROJECT_ID=${PROJECT_ID} \
                   /tmp/setup_and_run_digen.sh"
}

# Method 3: Submit as Dataproc job (alternative approach)
run_as_job() {
    log_info "Submitting DIGen as Dataproc job..."
    
    # Create a wrapper script that will be submitted
    JOB_SCRIPT="/tmp/digen_job.sh"
    cat > "${JOB_SCRIPT}" << EOF
#!/bin/bash
# Wrapper script for DIGen execution
export SCALE_FACTOR=${SCALE_FACTOR}
export GCS_BUCKET=${GCS_BUCKET}
export GCS_RAW_PATH=${GCS_RAW_PATH}
export PROJECT_ID=${PROJECT_ID}

# Download and run setup script
gsutil cp gs://${GCS_BUCKET}/scripts/setup_and_run_digen.sh /tmp/
chmod +x /tmp/setup_and_run_digen.sh
/tmp/setup_and_run_digen.sh
EOF
    
    # Upload wrapper script
    gsutil cp "${JOB_SCRIPT}" "gs://${GCS_BUCKET}/scripts/digen_job.sh"
    
    # Submit job
    gcloud dataproc jobs submit hadoop \
        --cluster="${CLUSTER_NAME}" \
        --region="${REGION}" \
        --project="${PROJECT_ID}" \
        --class="org.apache.hadoop.util.RunJar" \
        --jars="gs://${GCS_BUCKET}/scripts/digen_job.sh" \
        -- \
        "bash" "gs://${GCS_BUCKET}/scripts/digen_job.sh"
    
    log_info "Job submitted. Check status with: gcloud dataproc jobs list --cluster=${CLUSTER_NAME}"
}

# Main menu
main() {
    echo "=========================================="
    echo "TPC-DI DIGen on Dataproc"
    echo "=========================================="
    echo "Scale Factor: ${SCALE_FACTOR}"
    echo "GCS Bucket: ${GCS_BUCKET}"
    echo "Cluster: ${CLUSTER_NAME}"
    echo "=========================================="
    echo ""
    echo "Select execution method:"
    echo "1) Run via SSH (recommended for existing cluster)"
    echo "2) Run as initialization action (new cluster)"
    echo "3) Run as Dataproc job"
    echo ""
    read -p "Enter choice [1-3]: " choice
    
    case $choice in
        1)
            run_via_ssh
            ;;
        2)
            run_as_init_action
            ;;
        3)
            run_as_job
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
}

# If arguments provided, run directly
if [ $# -ge 1 ]; then
    if [ "$1" == "ssh" ]; then
        run_via_ssh
    elif [ "$1" == "init" ]; then
        run_as_init_action
    elif [ "$1" == "job" ]; then
        run_as_job
    else
        main
    fi
else
    main
fi
