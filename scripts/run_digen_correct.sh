#!/bin/bash
# Correct way to run DIGen with external dependencies
# This script demonstrates the proper classpath usage

set -e

# Configuration
DIGEN_DIR=${1:-"/Volumes/users/sumit_prakash/tpcdi/zip_file/Tools"}
OUTPUT_DIR=${2:-"/Volumes/users/sumit_prakash/tpcdi/zip_file/output"}
SCALE_FACTOR=${3:-1}
COMMONS_CLI_JAR=${4:-"/Volumes/users/sumit_prakash/tpcdi/zip_file/commons-cli-1.4.jar"}

echo "=========================================="
echo "Running DIGen with correct classpath"
echo "=========================================="
echo "DIGen directory: ${DIGEN_DIR}"
echo "Output directory: ${OUTPUT_DIR}"
echo "Scale factor: ${SCALE_FACTOR}"
echo "Commons CLI: ${COMMONS_CLI_JAR}"
echo "=========================================="

cd "${DIGEN_DIR}"

# Verify files exist
if [ ! -f "DIGen.jar" ]; then
    echo "ERROR: DIGen.jar not found in ${DIGEN_DIR}"
    exit 1
fi

if [ ! -f "${COMMONS_CLI_JAR}" ]; then
    echo "ERROR: commons-cli-1.4.jar not found at ${COMMONS_CLI_JAR}"
    exit 1
fi

# Extract Main-Class from manifest
echo "Extracting Main-Class from DIGen.jar manifest..."
MAIN_CLASS=$(unzip -p DIGen.jar META-INF/MANIFEST.MF 2>/dev/null | grep -i "Main-Class:" | cut -d' ' -f2 | tr -d '\r' | tr -d '\n')

# If not found, use the common wrapper class
if [ -z "${MAIN_CLASS}" ]; then
    echo "Main-Class not found in manifest, using default wrapper class"
    MAIN_CLASS="org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"
else
    echo "Found Main-Class: ${MAIN_CLASS}"
fi

# Build classpath - MUST include both JARs
# Important: Use absolute paths to avoid issues
DIGEN_JAR_ABS=$(cd "${DIGEN_DIR}" && pwd)/DIGen.jar
COMMONS_CLI_ABS=$(cd "$(dirname "${COMMONS_CLI_JAR}")" && pwd)/$(basename "${COMMONS_CLI_JAR}")

CLASSPATH="${DIGEN_JAR_ABS}:${COMMONS_CLI_ABS}"

echo ""
echo "Classpath: ${CLASSPATH}"
echo "Main class: ${MAIN_CLASS}"
echo ""

# Create output directory
mkdir -p "${OUTPUT_DIR}"

echo ""
echo "Running DIGen..."
echo "Command: java -Xmx4g -cp \"${CLASSPATH}\" ${MAIN_CLASS} -o ${OUTPUT_DIR}/ -sf ${SCALE_FACTOR}"
echo ""

# Run DIGen
# CRITICAL: Use -cp WITHOUT -jar to include external dependencies
java -Xmx4g -cp "${CLASSPATH}" ${MAIN_CLASS} -o "${OUTPUT_DIR}/" -sf "${SCALE_FACTOR}"

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "SUCCESS! Data generation completed"
    echo "=========================================="
    echo "Output files in: ${OUTPUT_DIR}"
    ls -lh "${OUTPUT_DIR}"/*.txt 2>/dev/null | head -10
else
    echo ""
    echo "=========================================="
    echo "ERROR: Data generation failed"
    echo "=========================================="
    exit 1
fi
