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
SCALE_FACTOR = 1  # Scale factor (1 = ~1GB, 10 = ~10GB, etc.)
GCS_BUCKET = "your-tpc-di-bucket"  # Your GCS bucket name
GCS_RAW_PATH = "raw"  # Path in bucket for raw data
PROJECT_ID = "your-project-id"  # Your GCP project ID

# TPC-DI Tools URL (download from TPC website)
# Get from: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp
TPCDI_TOOLS_URL = ""  # Leave empty if tools are already in DBFS

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Setup Environment

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set environment variables
# MAGIC export SCALE_FACTOR=1
# MAGIC export GCS_BUCKET=your-tpc-di-bucket
# MAGIC export GCS_RAW_PATH=raw
# MAGIC export PROJECT_ID=your-project-id
# MAGIC 
# MAGIC # Create work directories
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/output
# MAGIC 
# MAGIC # Check Java
# MAGIC java -version

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Download and Setup DIGen

# COMMAND ----------

# MAGIC %sh
# MAGIC # Download TPC-DI Tools (if URL provided)
# MAGIC # Uncomment and update URL:
# MAGIC # cd /dbfs/tmp/tpc-di-setup
# MAGIC # curl -L -o TPCDI_Tools.zip "YOUR_TPCDI_TOOLS_URL_HERE"
# MAGIC # unzip -q -o TPCDI_Tools.zip
# MAGIC # 
# MAGIC # Rename PDGF to pdgf (required by DIGen)
# MAGIC # if [ -d "Tools/PDGF" ]; then
# MAGIC #   mv Tools/PDGF Tools/pdgf
# MAGIC # fi
# MAGIC 
# MAGIC # Or if already uploaded to DBFS:
# MAGIC # dbutils.fs.cp("dbfs:/tmp/tpc-di-tools/TPCDI_Tools.zip", "file:/tmp/tpc-di-setup/TPCDI_Tools.zip")
# MAGIC # cd /tmp/tpc-di-setup && unzip -q -o TPCDI_Tools.zip && mv Tools/PDGF Tools/pdgf

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Run DIGen

# COMMAND ----------

# MAGIC %sh
# MAGIC # Download Apache Commons CLI dependency (required for DIGen)
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC 
# MAGIC # Download commons-cli
# MAGIC curl -L -o commons-cli-1.4.jar https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar
# MAGIC 
# MAGIC echo "Apache Commons CLI downloaded"

# COMMAND ----------

# MAGIC %sh
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools
# MAGIC 
# MAGIC # Build classpath with dependencies
# MAGIC CLASSPATH="DIGen.jar:lib/commons-cli-1.4.jar"
# MAGIC 
# MAGIC # Show DIGen help
# MAGIC # Use -jar which reads Main-Class from manifest automatically
# MAGIC java -cp "$CLASSPATH" -jar DIGen.jar -h
# MAGIC 
# MAGIC # Run DIGen (adjust scale factor as needed)
# MAGIC # java -Xmx4g -cp "$CLASSPATH" -jar DIGen.jar -o /dbfs/tmp/tpc-di-setup/output/ -sf 1

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Upload Generated Files to GCS

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
# MAGIC ## Step 5: Verify Upload

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
