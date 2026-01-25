#!/bin/bash
# Helper script to download TPC-DI DIGen tools
# This can be run locally to prepare DIGen for upload to Dataproc

set -e

# Configuration
DOWNLOAD_DIR="./digen_tools"
TPCDI_TOOLS_URL=${TPCDI_TOOLS_URL:-""}

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

# Create download directory
mkdir -p "${DOWNLOAD_DIR}"
cd "${DOWNLOAD_DIR}"

if [ -z "${TPCDI_TOOLS_URL}" ] || [ "${TPCDI_TOOLS_URL}" == "" ]; then
    log_error "TPCDI_TOOLS_URL not set."
    log_info ""
    log_info "To download TPC-DI Tools:"
    log_info "1. Visit: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp"
    log_info "2. Download 'TPCDI_Tools.zip'"
    log_info "3. Set TPCDI_TOOLS_URL environment variable or update this script"
    log_info ""
    log_info "Alternatively, manually download and extract TPCDI_Tools.zip to ${DOWNLOAD_DIR}/Tools/"
    exit 1
fi

log_info "Downloading TPC-DI Tools from: ${TPCDI_TOOLS_URL}"
wget "${TPCDI_TOOLS_URL}" -O TPCDI_Tools.zip

if [ ! -f TPCDI_Tools.zip ]; then
    log_error "Failed to download TPCDI_Tools.zip"
    exit 1
fi

log_info "Extracting TPCDI_Tools.zip..."
unzip TPCDI_Tools.zip

# Rename PDGF to pdgf (required by DIGen)
if [ -d "Tools/PDGF" ]; then
    log_info "Renaming PDGF to pdgf..."
    mv Tools/PDGF Tools/pdgf
fi

# Verify DIGen.jar exists
if [ -f "Tools/DIGen.jar" ]; then
    log_info "DIGen.jar successfully extracted!"
    log_info "Location: ${DOWNLOAD_DIR}/Tools/DIGen.jar"
    log_info ""
    log_info "Next steps:"
    log_info "1. Upload Tools directory to GCS:"
    log_info "   gsutil -m cp -r ${DOWNLOAD_DIR}/Tools gs://your-bucket/tpc-di-tools/"
    log_info ""
    log_info "2. Update setup_and_run_digen.sh to download from GCS instead"
else
    log_error "DIGen.jar not found after extraction"
    exit 1
fi
