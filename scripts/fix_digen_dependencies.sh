#!/bin/bash
# Quick fix script to download Apache Commons CLI for DIGen
# Run this if you encounter NoClassDefFoundError for org.apache.commons.cli.ParseException

set -e

# Configuration
DIGEN_DIR=${1:-"/tmp/tpc-di-setup/Tools"}
COMMONS_CLI_VERSION=${2:-"1.4"}

log_info() {
    echo "[INFO] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
}

# Create lib directory
mkdir -p "${DIGEN_DIR}/lib"

# Download Apache Commons CLI
COMMONS_CLI_JAR="${DIGEN_DIR}/lib/commons-cli-${COMMONS_CLI_VERSION}.jar"
COMMONS_CLI_URL="https://repo1.maven.org/maven2/commons-cli/commons-cli/${COMMONS_CLI_VERSION}/commons-cli-${COMMONS_CLI_VERSION}.jar"

log_info "Downloading Apache Commons CLI ${COMMONS_CLI_VERSION}..."
log_info "URL: ${COMMONS_CLI_URL}"
log_info "Destination: ${COMMONS_CLI_JAR}"

if command -v curl &> /dev/null; then
    curl -L -o "${COMMONS_CLI_JAR}" "${COMMONS_CLI_URL}"
elif command -v wget &> /dev/null; then
    wget -q "${COMMONS_CLI_URL}" -O "${COMMONS_CLI_JAR}"
else
    log_error "Neither curl nor wget found. Please download manually:"
    log_error "  ${COMMONS_CLI_URL}"
    log_error "  Save to: ${COMMONS_CLI_JAR}"
    exit 1
fi

if [ -f "${COMMONS_CLI_JAR}" ]; then
    log_info "✓ Apache Commons CLI downloaded successfully"
    log_info "  Location: ${COMMONS_CLI_JAR}"
    log_info ""
    log_info "Now run DIGen with classpath:"
    log_info "  java -cp ${DIGEN_DIR}/DIGen.jar:${COMMONS_CLI_JAR} -jar ${DIGEN_DIR}/DIGen.jar -o <output_dir> -sf <scale_factor>"
else
    log_error "Download failed. Please download manually from:"
    log_error "  ${COMMONS_CLI_URL}"
    exit 1
fi
