#!/bin/bash
# Script to download and run TPC-DI DIGen on Dataproc Master node
# This script generates TPC-DI benchmark data and uploads to GCS

set -e  # Exit on error

# Configuration - Update these or pass as environment variables
SCALE_FACTOR=${SCALE_FACTOR:-1}
GCS_BUCKET=${GCS_BUCKET:-"your-tpc-di-bucket"}
GCS_RAW_PATH=${GCS_RAW_PATH:-"raw"}
PROJECT_ID=${PROJECT_ID:-"your-project-id"}

# TPC-DI Tools download URL (update with actual URL from TPC website)
# Note: You need to download TPCDI_Tools.zip from https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp
TPCDI_TOOLS_URL=${TPCDI_TOOLS_URL:-""}

# Local directories
WORK_DIR="/tmp/tpc-di-setup"
DIGEN_DIR="${WORK_DIR}/Tools"
OUTPUT_DIR="${WORK_DIR}/output"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on Dataproc
check_dataproc() {
    if [ -f /etc/google-dataproc/version ]; then
        log_info "Running on Dataproc cluster"
        DATAPROC_VERSION=$(cat /etc/google-dataproc/version)
        log_info "Dataproc version: ${DATAPROC_VERSION}"
    else
        log_warn "Not running on Dataproc - some features may not work"
    fi
}

# Check Java installation
check_java() {
    log_info "Checking Java installation..."
    if command -v java &> /dev/null; then
        JAVA_VERSION=$(java -version 2>&1 | head -n 1)
        log_info "Java found: ${JAVA_VERSION}"
        
        # Check Java version (need 7+)
        JAVA_MAJOR_VERSION=$(java -version 2>&1 | awk -F '"' '/version/ {print $2}' | awk -F '.' '{print $1}')
        if [ "$JAVA_MAJOR_VERSION" -lt 7 ]; then
            log_error "Java 7 or higher required. Found version: ${JAVA_MAJOR_VERSION}"
            exit 1
        fi
    else
        log_error "Java not found. Please install Java 7 or higher."
        exit 1
    fi
}

# Download TPC-DI Tools
download_tpcdi_tools() {
    log_info "Setting up TPC-DI DIGen..."
    
    # Create work directory
    mkdir -p "${WORK_DIR}"
    cd "${WORK_DIR}"
    
    if [ -n "${TPCDI_TOOLS_URL}" ] && [ "${TPCDI_TOOLS_URL}" != "" ]; then
        log_info "Downloading TPC-DI Tools from: ${TPCDI_TOOLS_URL}"
        wget -q "${TPCDI_TOOLS_URL}" -O TPCDI_Tools.zip
        
        if [ ! -f TPCDI_Tools.zip ]; then
            log_error "Failed to download TPCDI_Tools.zip"
            exit 1
        fi
        
        log_info "Extracting TPCDI_Tools.zip..."
        unzip -q TPCDI_Tools.zip
        
        # Rename PDGF to pdgf (required by DIGen)
        if [ -d "Tools/PDGF" ]; then
            log_info "Renaming PDGF to pdgf..."
            mv Tools/PDGF Tools/pdgf
        fi
    else
        log_warn "TPCDI_TOOLS_URL not set. Assuming DIGen is already available."
        log_info "If DIGen is not available, please:"
        log_info "1. Download TPCDI_Tools.zip from: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp"
        log_info "2. Extract it to ${WORK_DIR}/Tools/"
        log_info "3. Rename PDGF directory to pdgf"
        
        if [ ! -f "${DIGEN_DIR}/DIGen.jar" ]; then
            log_error "DIGen.jar not found at ${DIGEN_DIR}/DIGen.jar"
            log_error "Please download and extract TPCDI_Tools.zip manually"
            exit 1
        fi
    fi
    
    if [ ! -f "${DIGEN_DIR}/DIGen.jar" ]; then
        log_error "DIGen.jar not found at ${DIGEN_DIR}/DIGen.jar"
        exit 1
    fi
    
    log_info "DIGen.jar found at ${DIGEN_DIR}/DIGen.jar"
}

# Show DIGen help
show_digen_help() {
    log_info "DIGen command line options:"
    java -jar "${DIGEN_DIR}/DIGen.jar" -h || true
}

# Run DIGen to generate data
run_digen() {
    log_info "Running DIGen with scale factor: ${SCALE_FACTOR}"
    log_info "Output directory: ${OUTPUT_DIR}"
    
    # Create output directory
    mkdir -p "${OUTPUT_DIR}"
    
    # Run DIGen
    # -o: output directory
    # -sf: scale factor
    log_info "Starting data generation (this may take a while)..."
    
    cd "${DIGEN_DIR}"
    java -jar DIGen.jar -o "${OUTPUT_DIR}/" -sf "${SCALE_FACTOR}"
    
    if [ $? -eq 0 ]; then
        log_info "Data generation completed successfully!"
        
        # List generated files
        log_info "Generated files:"
        ls -lh "${OUTPUT_DIR}"/*.txt 2>/dev/null | awk '{print $9, "(" $5 ")"}' || true
    else
        log_error "Data generation failed!"
        exit 1
    fi
}

# Upload generated files to GCS
upload_to_gcs() {
    log_info "Uploading generated files to GCS..."
    log_info "GCS Bucket: gs://${GCS_BUCKET}/${GCS_RAW_PATH}/"
    
    # Check if gsutil is available
    if ! command -v gsutil &> /dev/null; then
        log_error "gsutil not found. Cannot upload to GCS."
        log_error "Please install Google Cloud SDK or use gcloud dataproc jobs submit"
        exit 1
    fi
    
    # Upload all .txt files to GCS
    for file in "${OUTPUT_DIR}"/*.txt; do
        if [ -f "$file" ]; then
            filename=$(basename "$file")
            gcs_path="gs://${GCS_BUCKET}/${GCS_RAW_PATH}/${filename}"
            
            log_info "Uploading ${filename} to ${gcs_path}..."
            gsutil cp "$file" "${gcs_path}"
            
            if [ $? -eq 0 ]; then
                log_info "Successfully uploaded ${filename}"
            else
                log_error "Failed to upload ${filename}"
            fi
        fi
    done
    
    log_info "Upload to GCS completed!"
    log_info "Files available at: gs://${GCS_BUCKET}/${GCS_RAW_PATH}/"
}

# Main execution
main() {
    log_info "=========================================="
    log_info "TPC-DI DIGen Setup and Execution"
    log_info "=========================================="
    log_info "Scale Factor: ${SCALE_FACTOR}"
    log_info "GCS Bucket: ${GCS_BUCKET}"
    log_info "GCS Path: ${GCS_RAW_PATH}"
    log_info "=========================================="
    
    # Pre-flight checks
    check_dataproc
    check_java
    
    # Setup and run
    download_tpcdi_tools
    show_digen_help
    run_digen
    upload_to_gcs
    
    log_info "=========================================="
    log_info "TPC-DI data generation completed!"
    log_info "=========================================="
    log_info "Next steps:"
    log_info "1. Verify files in GCS: gsutil ls gs://${GCS_BUCKET}/${GCS_RAW_PATH}/"
    log_info "2. Run your PySpark pipeline: python src/main.py --load-type historical"
    log_info "=========================================="
}

# Run main function
main "$@"
