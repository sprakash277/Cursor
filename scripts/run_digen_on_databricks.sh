#!/bin/bash
# Script to run TPC-DI DIGen on Databricks cluster
# This script uploads the setup script and provides instructions for execution

set -e

# Configuration
SCALE_FACTOR=${1:-1}
GCS_BUCKET=${2:-"your-tpc-di-bucket"}
GCS_RAW_PATH=${3:-"raw"}
PROJECT_ID=${4:-"your-project-id"}
DATABRICKS_WORKSPACE=${5:-""}
DATABRICKS_CLUSTER_ID=${6:-""}

# Path to the setup script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETUP_SCRIPT="${SCRIPT_DIR}/setup_and_run_digen_databricks.sh"

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

# Check if databricks-cli is installed
check_databricks_cli() {
    if ! command -v databricks &> /dev/null; then
        log_error "databricks-cli not found."
        log_info "Install with: pip install databricks-cli"
        log_info "Or configure manually using the notebook method below"
        return 1
    fi
    return 0
}

# Method 1: Upload script to DBFS and run as init script
upload_as_init_script() {
    log_info "Uploading setup script to DBFS..."
    
    if ! check_databricks_cli; then
        return 1
    fi
    
    # Upload script to DBFS
    DBFS_SCRIPT_PATH="dbfs:/tmp/tpc-di-setup/setup_and_run_digen.sh"
    databricks fs cp "${SETUP_SCRIPT}" "${DBFS_SCRIPT_PATH}"
    
    log_info "Script uploaded to ${DBFS_SCRIPT_PATH}"
    log_info ""
    log_info "To use as cluster init script:"
    log_info "1. Go to Databricks workspace -> Clusters -> Edit cluster"
    log_info "2. Add init script: ${DBFS_SCRIPT_PATH}"
    log_info "3. Add environment variables:"
    log_info "   SCALE_FACTOR=${SCALE_FACTOR}"
    log_info "   GCS_BUCKET=${GCS_BUCKET}"
    log_info "   GCS_RAW_PATH=${GCS_RAW_PATH}"
    log_info "   PROJECT_ID=${PROJECT_ID}"
    log_info "4. Restart cluster"
}

# Method 2: Create Databricks notebook code
create_notebook_code() {
    log_info "Creating Databricks notebook code..."
    
    cat << 'NOTEBOOK_CODE'
# Databricks notebook source
# MAGIC %md
# MAGIC # TPC-DI DIGen Data Generation
# MAGIC 
# MAGIC This notebook runs the TPC-DI DIGen tool to generate benchmark data.

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set environment variables
# MAGIC export SCALE_FACTOR=1
# MAGIC export GCS_BUCKET=your-tpc-di-bucket
# MAGIC export GCS_RAW_PATH=raw
# MAGIC export PROJECT_ID=your-project-id
# MAGIC 
# MAGIC # Download and run setup script
# MAGIC curl -o /tmp/setup_digen.sh https://raw.githubusercontent.com/your-repo/scripts/setup_and_run_digen_databricks.sh
# MAGIC # Or upload script to DBFS first and use:
# MAGIC # dbutils.fs.cp("dbfs:/tmp/tpc-di-setup/setup_and_run_digen_databricks.sh", "file:/tmp/setup_digen.sh")
# MAGIC 
# MAGIC chmod +x /tmp/setup_digen.sh
# MAGIC /tmp/setup_digen.sh

# COMMAND ----------

# Alternative: Run directly in notebook cells
# MAGIC %sh
# MAGIC # Configuration
# MAGIC SCALE_FACTOR=1
# MAGIC GCS_BUCKET=your-tpc-di-bucket
# MAGIC GCS_RAW_PATH=raw
# MAGIC PROJECT_ID=your-project-id
# MAGIC 
# MAGIC # Create directories
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup
# MAGIC cd /dbfs/tmp/tpc-di-setup
# MAGIC 
# MAGIC # Download TPC-DI Tools (update URL)
# MAGIC # curl -L -o TPCDI_Tools.zip "https://www.tpc.org/.../TPCDI_Tools.zip"
# MAGIC 
# MAGIC # Extract and setup
# MAGIC # unzip -q TPCDI_Tools.zip
# MAGIC # mv Tools/PDGF Tools/pdgf
# MAGIC 
# MAGIC # Run DIGen
# MAGIC # java -Xmx4g -jar Tools/DIGen.jar -o /dbfs/tmp/tpc-di-setup/output/ -sf $SCALE_FACTOR

# COMMAND ----------

# Upload generated files to GCS
from pyspark.dbutils import DBUtils
import glob
import os

dbutils = DBUtils()

output_dir = "/dbfs/tmp/tpc-di-setup/output"
gcs_bucket = "your-tpc-di-bucket"
gcs_path = "raw"

# Upload all .txt files
txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
for file_path in txt_files:
    filename = os.path.basename(file_path)
    gcs_dest = f"gs://{gcs_bucket}/{gcs_path}/{filename}"
    print(f"Uploading {filename} to {gcs_dest}...")
    dbutils.fs.cp(f"file://{file_path}", gcs_dest)
    print(f"Successfully uploaded {filename}")

print(f"All files uploaded to gs://{gcs_bucket}/{gcs_path}/")

NOTEBOOK_CODE

    log_info ""
    log_info "Notebook code created above. Copy this into a Databricks notebook."
}

# Method 3: Upload script and provide manual execution instructions
upload_script_manual() {
    log_info "Uploading setup script to DBFS..."
    
    if check_databricks_cli; then
        DBFS_SCRIPT_PATH="dbfs:/tmp/tpc-di-setup/setup_and_run_digen_databricks.sh"
        databricks fs cp "${SETUP_SCRIPT}" "${DBFS_SCRIPT_PATH}"
        log_info "Script uploaded to ${DBFS_SCRIPT_PATH}"
    else
        log_info "Manual upload required. Use Databricks UI or dbutils:"
        log_info "  dbutils.fs.put('dbfs:/tmp/tpc-di-setup/setup_and_run_digen_databricks.sh', open('${SETUP_SCRIPT}').read())"
    fi
    
    log_info ""
    log_info "To execute, run this in a Databricks notebook:"
    log_info ""
    cat << EXEC_CODE
# MAGIC %sh
# MAGIC # Copy script from DBFS to local filesystem
# MAGIC dbutils.fs.cp("dbfs:/tmp/tpc-di-setup/setup_and_run_digen_databricks.sh", "file:/tmp/setup_digen.sh")
# MAGIC 
# MAGIC # Set environment variables
# MAGIC export SCALE_FACTOR=${SCALE_FACTOR}
# MAGIC export GCS_BUCKET=${GCS_BUCKET}
# MAGIC export GCS_RAW_PATH=${GCS_RAW_PATH}
# MAGIC export PROJECT_ID=${PROJECT_ID}
# MAGIC 
# MAGIC # Make executable and run
# MAGIC chmod +x /tmp/setup_digen.sh
# MAGIC /tmp/setup_digen.sh
EXEC_CODE
}

# Main menu
main() {
    echo "=========================================="
    echo "TPC-DI DIGen on Databricks"
    echo "=========================================="
    echo "Scale Factor: ${SCALE_FACTOR}"
    echo "GCS Bucket: ${GCS_BUCKET}"
    echo "=========================================="
    echo ""
    echo "Select execution method:"
    echo "1) Upload script to DBFS (for init script or manual execution)"
    echo "2) Generate notebook code"
    echo "3) Upload and show manual execution instructions"
    echo ""
    read -p "Enter choice [1-3]: " choice
    
    case $choice in
        1)
            upload_as_init_script
            ;;
        2)
            create_notebook_code
            ;;
        3)
            upload_script_manual
            ;;
        *)
            log_error "Invalid choice"
            exit 1
            ;;
    esac
}

# If arguments provided, run directly
if [ $# -ge 1 ]; then
    if [ "$1" == "upload" ]; then
        upload_as_init_script
    elif [ "$1" == "notebook" ]; then
        create_notebook_code
    elif [ "$1" == "manual" ]; then
        upload_script_manual
    else
        main
    fi
else
    main
fi
