# Databricks notebook source
# MAGIC %md
# MAGIC # TPC-DI DIGen Data Generation on Databricks
# MAGIC 
# MAGIC This notebook runs the official TPC-DI DIGen tool to generate benchmark data and upload it to GCS.
# MAGIC 
# MAGIC ## Configuration
# MAGIC Update the variables in the next cell before running.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC Update these variables according to your setup:

# COMMAND ----------

# Configuration variables
SCALE_FACTOR = 10  # Scale factor (1 = ~1GB, 10 = ~10GB, etc.)
GCS_BUCKET = "your-tpc-di-bucket"  # Your GCS bucket name
GCS_RAW_PATH = "raw"  # Path in bucket for raw data
PROJECT_ID = "your-project-id"  # Your GCP project ID

# TPC-DI Tools zip file location in Databricks workspace
TPCDI_ZIP_PATH = "/Workspace/Users/sumit.prakash@databricks.com/Cursor/datagen/801FA37E-A4C5-4307-BD70-985A205019ED-TPC-DI-Tool.zip"

# Local directories
WORK_DIR = "/dbfs/tmp/tpc-di-setup"
TOOLS_DIR = f"{WORK_DIR}/Tools"
OUTPUT_DIR = f"{WORK_DIR}/output"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Install Java 8 and Setup Environment

# COMMAND ----------

# MAGIC %sh
# MAGIC # Install Java 8
# MAGIC sudo apt update
# MAGIC sudo apt install openjdk-8-jdk -y
# MAGIC 
# MAGIC # Set Java environment variables
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Verify Java installation
# MAGIC java -version
# MAGIC echo "JAVA_HOME: $JAVA_HOME"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Extract TPC-DI Tools and Setup

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set Java environment (needed in each cell)
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Create work directories
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/Tools
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/output
# MAGIC 
# MAGIC # Copy zip file from workspace to local filesystem for extraction
# MAGIC ZIP_FILE="/Workspace/Users/sumit.prakash@databricks.com/Cursor/datagen/801FA37E-A4C5-4307-BD70-985A205019ED-TPC-DI-Tool.zip"
# MAGIC TEMP_ZIP="/tmp/tpcdi-tools.zip"
# MAGIC 
# MAGIC echo "Copying TPC-DI Tools zip file..."
# MAGIC cp "$ZIP_FILE" "$TEMP_ZIP"
# MAGIC 
# MAGIC # Extract to work directory
# MAGIC echo "Extracting TPC-DI Tools..."
# MAGIC cd /dbfs/tmp/tpc-di-setup
# MAGIC unzip -q -o "$TEMP_ZIP"
# MAGIC 
# MAGIC # Rename PDGF to pdgf (required by DIGen)
# MAGIC if [ -d "Tools/PDGF" ]; then
# MAGIC   echo "Renaming PDGF to pdgf..."
# MAGIC   mv Tools/PDGF Tools/pdgf
# MAGIC   echo "✓ PDGF renamed to pdgf"
# MAGIC else
# MAGIC   echo "PDGF directory not found (may already be renamed)"
# MAGIC fi
# MAGIC 
# MAGIC # Verify DIGen.jar exists
# MAGIC if [ -f "Tools/DIGen.jar" ]; then
# MAGIC   echo "✓ DIGen.jar found"
# MAGIC   ls -lh Tools/DIGen.jar
# MAGIC else
# MAGIC   echo "✗ ERROR: DIGen.jar not found!"
# MAGIC   exit 1
# MAGIC fi
# MAGIC 
# MAGIC # Clean up temp file
# MAGIC rm -f "$TEMP_ZIP"
# MAGIC 
# MAGIC echo "TPC-DI Tools setup completed!"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Download Apache Commons CLI Dependency

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set Java environment
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Download Apache Commons CLI dependency (required for DIGen)
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC 
# MAGIC # Download commons-cli
# MAGIC echo "Downloading Apache Commons CLI..."
# MAGIC curl -L -o commons-cli-1.4.jar https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar
# MAGIC 
# MAGIC if [ -f "commons-cli-1.4.jar" ]; then
# MAGIC   echo "✓ Apache Commons CLI downloaded successfully"
# MAGIC   ls -lh commons-cli-1.4.jar
# MAGIC else
# MAGIC   echo "✗ ERROR: Failed to download Apache Commons CLI"
# MAGIC   exit 1
# MAGIC fi

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Run DIGen

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set Java environment
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Set PDG agreement (required by DIGen)
# MAGIC export PDG_AGREE=YES
# MAGIC 
# MAGIC # Navigate to Tools directory
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools
# MAGIC 
# MAGIC # Build classpath with dependencies
# MAGIC CLASSPATH="/dbfs/tmp/tpc-di-setup/Tools/DIGen.jar:/dbfs/tmp/tpc-di-setup/Tools/lib/commons-cli-1.4.jar"
# MAGIC 
# MAGIC # Main class (Eclipse JAR wrapper)
# MAGIC MAIN_CLASS="org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"
# MAGIC 
# MAGIC # Scale factor
# MAGIC SCALE_FACTOR=10
# MAGIC 
# MAGIC # Output directory
# MAGIC OUTPUT_DIR="/dbfs/tmp/tpc-di-setup/output"
# MAGIC mkdir -p "$OUTPUT_DIR"
# MAGIC 
# MAGIC echo "=========================================="
# MAGIC echo "Running TPC-DI DIGen"
# MAGIC echo "=========================================="
# MAGIC echo "Scale Factor: $SCALE_FACTOR"
# MAGIC echo "Output Directory: $OUTPUT_DIR"
# MAGIC echo "Classpath: $CLASSPATH"
# MAGIC echo "Main Class: $MAIN_CLASS"
# MAGIC echo "=========================================="
# MAGIC echo ""
# MAGIC echo "Starting data generation (this may take a while)..."
# MAGIC 
# MAGIC # Run DIGen
# MAGIC # Use yes YES| to automatically agree to license
# MAGIC # Use -cp WITHOUT -jar to include external dependencies
# MAGIC yes YES | java -Xmx8g -cp "$CLASSPATH" $MAIN_CLASS -o "$OUTPUT_DIR/" -sf $SCALE_FACTOR
# MAGIC 
# MAGIC if [ $? -eq 0 ]; then
# MAGIC   echo ""
# MAGIC   echo "=========================================="
# MAGIC   echo "✓ Data generation completed successfully!"
# MAGIC   echo "=========================================="
# MAGIC else
# MAGIC   echo ""
# MAGIC   echo "=========================================="
# MAGIC   echo "✗ ERROR: Data generation failed!"
# MAGIC   echo "=========================================="
# MAGIC   exit 1
# MAGIC fi

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: List Generated Files

# COMMAND ----------

# MAGIC %sh
# MAGIC OUTPUT_DIR="/dbfs/tmp/tpc-di-setup/output"
# MAGIC 
# MAGIC echo "Generated files:"
# MAGIC echo "=========================================="
# MAGIC ls -lh "$OUTPUT_DIR"/*.txt 2>/dev/null | awk '{print $9, "(" $5 ")"}'
# MAGIC 
# MAGIC # Count files
# MAGIC FILE_COUNT=$(ls -1 "$OUTPUT_DIR"/*.txt 2>/dev/null | wc -l)
# MAGIC echo ""
# MAGIC echo "Total files generated: $FILE_COUNT"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Upload Generated Files to GCS

# COMMAND ----------

from pyspark.dbutils import DBUtils
import glob
import os

dbutils = DBUtils()

# Configuration
output_dir = "/dbfs/tmp/tpc-di-setup/output"
gcs_bucket = "your-tpc-di-bucket"  # Update this
gcs_path = "raw"  # Update this

# List generated files
txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
print(f"Found {len(txt_files)} files to upload:")

for file_path in txt_files:
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
    print(f"  {filename} ({file_size:.2f} MB)")

# COMMAND ----------

# Upload all .txt files to GCS
for file_path in txt_files:
    filename = os.path.basename(file_path)
    gcs_dest = f"gs://{gcs_bucket}/{gcs_path}/{filename}"
    
    print(f"Uploading {filename} to {gcs_dest}...")
    try:
        dbutils.fs.cp(f"file://{file_path}", gcs_dest)
        print(f"✓ Successfully uploaded {filename}")
    except Exception as e:
        print(f"✗ Failed to upload {filename}: {str(e)}")

print(f"\nAll files uploaded to gs://{gcs_bucket}/{gcs_path}/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Verify Upload

# COMMAND ----------

# List files in GCS
gcs_path_full = f"gs://{gcs_bucket}/{gcs_path}/"
files = dbutils.fs.ls(gcs_path_full)

print(f"Files in {gcs_path_full}:")
for file_info in files:
    size_mb = file_info.size / (1024 * 1024)
    print(f"  {file_info.name} ({size_mb:.2f} MB)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC After data generation:
# MAGIC 1. Verify files in GCS: `dbutils.fs.ls('gs://your-bucket/raw/')`
# MAGIC 2. Run your PySpark pipeline: `python src/main.py --load-type historical`
# MAGIC 3. Process data through Bronze → Silver → Gold layers
