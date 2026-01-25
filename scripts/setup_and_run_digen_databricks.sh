#!/bin/bash
# Script to download and run TPC-DI DIGen on Databricks cluster
# This script generates TPC-DI benchmark data and uploads to GCS
# Can be run as a cluster init script or via notebook %sh command

set -e  # Exit on error

# Configuration - Update these or pass as environment variables
SCALE_FACTOR=${SCALE_FACTOR:-1}
GCS_BUCKET=${GCS_BUCKET:-"your-tpc-di-bucket"}
GCS_RAW_PATH=${GCS_RAW_PATH:-"raw"}
PROJECT_ID=${PROJECT_ID:-"your-project-id"}

# TPC-DI Tools download URL (update with actual URL from TPC website)
# Note: You need to download TPCDI_Tools.zip from https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp
TPCDI_TOOLS_URL=${TPCDI_TOOLS_URL:-""}

# Local directories - use DBFS for persistence in Databricks
WORK_DIR="/dbfs/tmp/tpc-di-setup"
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

# Check if running on Databricks
check_databricks() {
    if [ -d "/databricks" ] || [ -n "${DATABRICKS_RUNTIME_VERSION}" ]; then
        log_info "Running on Databricks cluster"
        if [ -n "${DATABRICKS_RUNTIME_VERSION}" ]; then
            log_info "Databricks runtime version: ${DATABRICKS_RUNTIME_VERSION}"
        fi
    else
        log_warn "Not running on Databricks - some features may not work"
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
        log_info "On Databricks, Java should be pre-installed. Checking alternative locations..."
        
        # Check common Java locations on Databricks
        if [ -f "/usr/bin/java" ]; then
            export PATH="/usr/bin:$PATH"
            log_info "Found Java at /usr/bin/java"
        elif [ -f "/usr/lib/jvm/java-8-openjdk-amd64/bin/java" ]; then
            export PATH="/usr/lib/jvm/java-8-openjdk-amd64/bin:$PATH"
            log_info "Found Java at /usr/lib/jvm/java-8-openjdk-amd64/bin/java"
        else
            log_error "Java not found. Please ensure Java is installed on the cluster."
            exit 1
        fi
    fi
}

# Download Apache Commons CLI dependency
download_commons_cli() {
    log_info "Checking for Apache Commons CLI dependency..."
    
    COMMONS_CLI_JAR="${DIGEN_DIR}/lib/commons-cli-1.4.jar"
    COMMONS_CLI_URL="https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar"
    
    # Check if already exists
    if [ -f "${COMMONS_CLI_JAR}" ]; then
        log_info "Apache Commons CLI found at ${COMMONS_CLI_JAR}"
        return 0
    fi
    
    # Create lib directory
    mkdir -p "${DIGEN_DIR}/lib"
    
    log_info "Downloading Apache Commons CLI..."
    if command -v curl &> /dev/null; then
        curl -L -o "${COMMONS_CLI_JAR}" "${COMMONS_CLI_URL}" || {
            log_warn "Failed to download from Maven Central, trying alternative..."
            # Try alternative version
            COMMONS_CLI_URL="https://repo1.maven.org/maven2/commons-cli/commons-cli/1.5.0/commons-cli-1.5.0.jar"
            curl -L -o "${COMMONS_CLI_JAR}" "${COMMONS_CLI_URL}" || {
                log_error "Failed to download Apache Commons CLI"
                return 1
            }
        }
    elif command -v wget &> /dev/null; then
        wget -q "${COMMONS_CLI_URL}" -O "${COMMONS_CLI_JAR}" || {
            log_error "Failed to download Apache Commons CLI"
            return 1
        }
    else
        log_error "Neither curl nor wget found. Cannot download dependency."
        log_info "Please manually download commons-cli-1.4.jar to ${DIGEN_DIR}/lib/"
        return 1
    fi
    
    if [ -f "${COMMONS_CLI_JAR}" ]; then
        log_info "Apache Commons CLI downloaded successfully"
        return 0
    else
        log_error "Apache Commons CLI download failed"
        return 1
    fi
}

# Download TPC-DI Tools
download_tpcdi_tools() {
    log_info "Setting up TPC-DI DIGen..."
    
    # Create work directory (using DBFS for persistence)
    mkdir -p "${WORK_DIR}"
    cd "${WORK_DIR}"
    
    if [ -n "${TPCDI_TOOLS_URL}" ] && [ "${TPCDI_TOOLS_URL}" != "" ]; then
        log_info "Downloading TPC-DI Tools from: ${TPCDI_TOOLS_URL}"
        
        # Use curl or wget (Databricks usually has curl)
        if command -v curl &> /dev/null; then
            curl -L -o TPCDI_Tools.zip "${TPCDI_TOOLS_URL}"
        elif command -v wget &> /dev/null; then
            wget -q "${TPCDI_TOOLS_URL}" -O TPCDI_Tools.zip
        else
            log_error "Neither curl nor wget found. Cannot download tools."
            exit 1
        fi
        
        if [ ! -f TPCDI_Tools.zip ]; then
            log_error "Failed to download TPCDI_Tools.zip"
            exit 1
        fi
        
        log_info "Extracting TPCDI_Tools.zip..."
        unzip -q -o TPCDI_Tools.zip || {
            log_error "Failed to extract TPCDI_Tools.zip. Checking if unzip is available..."
            # Try alternative extraction method
            python3 -m zipfile -e TPCDI_Tools.zip . || exit 1
        }
        
        # Rename PDGF to pdgf (required by DIGen)
        if [ -d "Tools/PDGF" ]; then
            log_info "Renaming PDGF to pdgf..."
            mv Tools/PDGF Tools/pdgf
        fi
    else
        log_warn "TPCDI_TOOLS_URL not set. Checking if DIGen is already available..."
        
        if [ ! -f "${DIGEN_DIR}/DIGen.jar" ]; then
            log_error "DIGen.jar not found at ${DIGEN_DIR}/DIGen.jar"
            log_info "Please either:"
            log_info "1. Set TPCDI_TOOLS_URL environment variable"
            log_info "2. Upload TPCDI_Tools.zip to dbfs:/tmp/tpc-di-setup/ and extract manually"
            log_info "3. Download from: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp"
            exit 1
        fi
    fi
    
    if [ ! -f "${DIGEN_DIR}/DIGen.jar" ]; then
        log_error "DIGen.jar not found at ${DIGEN_DIR}/DIGen.jar"
        exit 1
    fi
    
    log_info "DIGen.jar found at ${DIGEN_DIR}/DIGen.jar"
    
    # Download required dependencies
    download_commons_cli
}

# Extract main class from JAR manifest
get_main_class() {
    if [ -f "${DIGEN_DIR}/DIGen.jar" ]; then
        # Try to extract Main-Class from manifest
        MAIN_CLASS=$(unzip -p "${DIGEN_DIR}/DIGen.jar" META-INF/MANIFEST.MF 2>/dev/null | grep -i "Main-Class:" | cut -d' ' -f2 | tr -d '\r' | tr -d '\n')
        if [ -n "${MAIN_CLASS}" ]; then
            echo "${MAIN_CLASS}"
            return 0
        fi
    fi
    # Default - use -jar which reads manifest automatically
    echo ""
    return 1
}

# Show DIGen help
show_digen_help() {
    log_info "DIGen command line options:"
    # Build classpath with dependencies
    CLASSPATH="${DIGEN_DIR}/DIGen.jar"
    if ls "${DIGEN_DIR}"/lib/commons-cli-*.jar 2>/dev/null | head -n 1 | read COMMONS_CLI_JAR; then
        CLASSPATH="${CLASSPATH}:${COMMONS_CLI_JAR}"
    fi
    
    # Try with classpath and -jar (reads main class from manifest)
    if [ "${CLASSPATH}" != "${DIGEN_DIR}/DIGen.jar" ]; then
        java -cp "${CLASSPATH}" -jar "${DIGEN_DIR}/DIGen.jar" -h || \
        java -jar "${DIGEN_DIR}/DIGen.jar" -h || true
    else
        java -jar "${DIGEN_DIR}/DIGen.jar" -h || true
    fi
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
    
    # Build classpath with dependencies
    CLASSPATH="${DIGEN_DIR}/DIGen.jar"
    
    # Add Commons CLI to classpath if available
    if [ -f "${DIGEN_DIR}/lib/commons-cli-1.4.jar" ]; then
        CLASSPATH="${CLASSPATH}:${DIGEN_DIR}/lib/commons-cli-1.4.jar"
    elif [ -f "${DIGEN_DIR}/lib/commons-cli-1.5.0.jar" ]; then
        CLASSPATH="${CLASSPATH}:${DIGEN_DIR}/lib/commons-cli-1.5.0.jar"
    elif ls "${DIGEN_DIR}"/lib/commons-cli-*.jar 2>/dev/null | head -n 1 | read COMMONS_CLI_JAR; then
        CLASSPATH="${CLASSPATH}:${COMMONS_CLI_JAR}"
    fi
    
    # Try running with classpath first (for dependencies)
    if [ "${CLASSPATH}" != "${DIGEN_DIR}/DIGen.jar" ]; then
        log_info "Running DIGen with classpath: ${CLASSPATH}"
        # Use -jar which automatically reads Main-Class from manifest
        # The classpath will include the dependency JARs
        java -Xmx4g -cp "${CLASSPATH}" -jar "${DIGEN_DIR}/DIGen.jar" -o "${OUTPUT_DIR}/" -sf "${SCALE_FACTOR}"
    else
        # Fallback to standard jar execution
        log_warn "Running without explicit classpath (may fail if dependencies missing)"
        java -Xmx4g -jar DIGen.jar -o "${OUTPUT_DIR}/" -sf "${SCALE_FACTOR}"
    fi
    
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

# Upload generated files to GCS using Databricks utilities
upload_to_gcs() {
    log_info "Uploading generated files to GCS..."
    log_info "GCS Bucket: gs://${GCS_BUCKET}/${GCS_RAW_PATH}/"
    
    # Check if we're in a Databricks notebook context
    if command -v python3 &> /dev/null && python3 -c "import dbutils" 2>/dev/null; then
        log_info "Using Databricks dbutils to upload files..."
        
        python3 << EOF
from pyspark.dbutils import DBUtils
import os
import glob

dbutils = DBUtils()

output_dir = "${OUTPUT_DIR}"
gcs_bucket = "${GCS_BUCKET}"
gcs_path = "${GCS_RAW_PATH}"

# Upload all .txt files
txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
for file_path in txt_files:
    filename = os.path.basename(file_path)
    gcs_dest = f"gs://{gcs_bucket}/{gcs_path}/{filename}"
    print(f"Uploading {filename} to {gcs_dest}...")
    dbutils.fs.cp(f"file://{file_path}", gcs_dest)
    print(f"Successfully uploaded {filename}")

print(f"All files uploaded to gs://{gcs_bucket}/{gcs_path}/")
EOF
    elif command -v gsutil &> /dev/null; then
        log_info "Using gsutil to upload files..."
        
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
    else
        log_error "Neither dbutils nor gsutil available. Cannot upload to GCS."
        log_info "Files are available at: ${OUTPUT_DIR}"
        log_info "You can manually upload using:"
        log_info "  dbutils.fs.cp('file://${OUTPUT_DIR}/filename.txt', 'gs://${GCS_BUCKET}/${GCS_RAW_PATH}/filename.txt')"
        exit 1
    fi
    
    log_info "Upload to GCS completed!"
    log_info "Files available at: gs://${GCS_BUCKET}/${GCS_RAW_PATH}/"
}

# Main execution
main() {
    log_info "=========================================="
    log_info "TPC-DI DIGen Setup and Execution (Databricks)"
    log_info "=========================================="
    log_info "Scale Factor: ${SCALE_FACTOR}"
    log_info "GCS Bucket: ${GCS_BUCKET}"
    log_info "GCS Path: ${GCS_RAW_PATH}"
    log_info "=========================================="
    
    # Pre-flight checks
    check_databricks
    check_java
    
    # Setup and run
    download_tpcdi_tools
    
    # Verify dependencies
    if ! ls "${DIGEN_DIR}"/lib/commons-cli-*.jar 2>/dev/null | grep -q .; then
        log_warn "Apache Commons CLI not found. Attempting to download..."
        download_commons_cli
    fi
    
    show_digen_help
    run_digen
    upload_to_gcs
    
    log_info "=========================================="
    log_info "TPC-DI data generation completed!"
    log_info "=========================================="
    log_info "Next steps:"
    log_info "1. Verify files in GCS: gsutil ls gs://${GCS_BUCKET}/${GCS_RAW_PATH}/"
    log_info "2. Or in Databricks: dbutils.fs.ls('gs://${GCS_BUCKET}/${GCS_RAW_PATH}/')"
    log_info "3. Run your PySpark pipeline: python src/main.py --load-type historical"
    log_info "=========================================="
}

# Run main function
main "$@"
