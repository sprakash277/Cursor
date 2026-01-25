# Running TPC-DI DIGen on Databricks

This guide explains how to run the official TPC-DI DIGen tool on Databricks clusters to generate benchmark data and upload it to GCS.

## Prerequisites

1. **Databricks Workspace** with a running cluster
2. **GCS Access** configured (via service account or cluster credentials)
3. **TPC-DI Tools** - Download from: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp
4. **Java 7+** (usually pre-installed on Databricks clusters)

## Method 1: Using Databricks Notebook (Recommended)

### Step 1: Create a New Notebook

1. Open your Databricks workspace
2. Create a new Python notebook
3. Copy the code from `scripts/databricks_notebook.py` or use the notebook template below

### Step 2: Configure Variables

Update these variables in the notebook:
```python
SCALE_FACTOR = 1  # 1 = ~1GB, 10 = ~10GB, etc.
GCS_BUCKET = "your-tpc-di-bucket"
GCS_RAW_PATH = "raw"
PROJECT_ID = "your-project-id"
```

### Step 3: Upload TPC-DI Tools

**Option A: Upload via UI**
1. Go to Workspace → Upload Data
2. Upload `TPCDI_Tools.zip` to `dbfs:/tmp/tpc-di-tools/`
3. Extract in notebook:

```python
# MAGIC %sh
# MAGIC cd /dbfs/tmp/tpc-di-tools
# MAGIC unzip -q -o TPCDI_Tools.zip
# MAGIC if [ -d "Tools/PDGF" ]; then mv Tools/PDGF Tools/pdgf; fi
```

**Option B: Download in Notebook**
```python
# MAGIC %sh
# MAGIC cd /dbfs/tmp/tpc-di-setup
# MAGIC curl -L -o TPCDI_Tools.zip "YOUR_TPCDI_TOOLS_URL"
# MAGIC unzip -q -o TPCDI_Tools.zip
# MAGIC if [ -d "Tools/PDGF" ]; then mv Tools/PDGF Tools/pdgf; fi
```

### Step 4: Run DIGen

```python
# MAGIC %sh
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools
# MAGIC java -Xmx4g -jar DIGen.jar -o /dbfs/tmp/tpc-di-setup/output/ -sf 1
```

### Step 5: Upload to GCS

```python
from pyspark.dbutils import DBUtils
import glob
import os

dbutils = DBUtils()
output_dir = "/dbfs/tmp/tpc-di-setup/output"
gcs_bucket = "your-tpc-di-bucket"
gcs_path = "raw"

txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
for file_path in txt_files:
    filename = os.path.basename(file_path)
    gcs_dest = f"gs://{gcs_bucket}/{gcs_path}/{filename}"
    dbutils.fs.cp(f"file://{file_path}", gcs_dest)
    print(f"Uploaded {filename}")
```

## Method 2: Using Cluster Init Script

### Step 1: Upload Setup Script

```bash
# Using databricks-cli
databricks fs cp scripts/setup_and_run_digen_databricks.sh dbfs:/tmp/tpc-di-setup/

# Or using dbutils in notebook
dbutils.fs.put("dbfs:/tmp/tpc-di-setup/setup_and_run_digen_databricks.sh", 
                open("scripts/setup_and_run_digen_databricks.sh").read())
```

### Step 2: Configure Cluster Init Script

1. Go to **Clusters** → Select your cluster → **Edit**
2. Go to **Advanced Options** → **Init Scripts**
3. Add init script path: `dbfs:/tmp/tpc-di-setup/setup_and_run_digen_databricks.sh`
4. Add environment variables:
   - `SCALE_FACTOR=1`
   - `GCS_BUCKET=your-tpc-di-bucket`
   - `GCS_RAW_PATH=raw`
   - `PROJECT_ID=your-project-id`
5. **Restart** the cluster

### Step 3: Verify Execution

Check cluster logs or run in a notebook:
```python
# Check if files were generated
dbutils.fs.ls("dbfs:/tmp/tpc-di-setup/output/")

# Check if files were uploaded to GCS
dbutils.fs.ls("gs://your-bucket/raw/")
```

## Method 3: Using Helper Script

### Run Locally

```bash
# Make script executable
chmod +x scripts/run_digen_on_databricks.sh

# Upload script and get instructions
./scripts/run_digen_on_databricks.sh manual 1 your-bucket raw your-project-id
```

This will:
1. Upload the setup script to DBFS
2. Provide notebook code to execute it

## Quick Start Notebook Template

```python
# Databricks notebook source

# COMMAND ----------

# Configuration
SCALE_FACTOR = 1
GCS_BUCKET = "your-tpc-di-bucket"
GCS_RAW_PATH = "raw"
PROJECT_ID = "your-project-id"

# COMMAND ----------

# MAGIC %sh
# MAGIC # Setup directories
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/{Tools,output}
# MAGIC 
# MAGIC # Download and extract TPC-DI Tools (update URL)
# MAGIC cd /dbfs/tmp/tpc-di-setup
# MAGIC # curl -L -o TPCDI_Tools.zip "YOUR_URL"
# MAGIC # unzip -q -o TPCDI_Tools.zip
# MAGIC # if [ -d "Tools/PDGF" ]; then mv Tools/PDGF Tools/pdgf; fi

# COMMAND ----------

# MAGIC %sh
# MAGIC # Run DIGen
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools
# MAGIC java -Xmx4g -jar DIGen.jar -o /dbfs/tmp/tpc-di-setup/output/ -sf ${SCALE_FACTOR}

# COMMAND ----------

# Upload to GCS
from pyspark.dbutils import DBUtils
import glob
import os

dbutils = DBUtils()
output_dir = "/dbfs/tmp/tpc-di-setup/output"

for file_path in glob.glob(os.path.join(output_dir, "*.txt")):
    filename = os.path.basename(file_path)
    gcs_dest = f"gs://{GCS_BUCKET}/{GCS_RAW_PATH}/{filename}"
    dbutils.fs.cp(f"file://{file_path}", gcs_dest)
    print(f"Uploaded {filename}")
```

## Configuration

### Environment Variables

Set these in cluster configuration or notebook:
- `SCALE_FACTOR`: Data volume (1 = ~1GB, 10 = ~10GB)
- `GCS_BUCKET`: Your GCS bucket name
- `GCS_RAW_PATH`: Path in bucket for raw data
- `PROJECT_ID`: GCP project ID
- `TPCDI_TOOLS_URL`: URL to download TPCDI_Tools.zip (optional)

### GCS Authentication

Databricks needs access to GCS. Configure via:

1. **Service Account Key**:
   - Upload JSON key to cluster
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable

2. **Cluster Service Account**:
   - Use cluster's service account with Storage Admin role

3. **dbutils**:
   - Uses cluster's default credentials

## Troubleshooting

### Java Not Found
```python
# MAGIC %sh
# MAGIC # Check Java installation
# MAGIC which java
# MAGIC java -version
# MAGIC 
# MAGIC # If not found, install
# MAGIC # sudo apt-get update && sudo apt-get install -y openjdk-8-jdk
```

### Out of Memory
Increase Java heap size:
```bash
java -Xmx8g -jar DIGen.jar -o /dbfs/tmp/tpc-di-setup/output/ -sf 1
```

### GCS Upload Fails
Check permissions:
```python
# Test GCS access
dbutils.fs.ls("gs://your-bucket/")
```

### Files Not Persisting
Use `/dbfs/` prefix for persistent storage:
```python
# Persistent (survives cluster restart)
/dbfs/tmp/tpc-di-setup/output/

# Temporary (lost on cluster restart)
/tmp/tpc-di-setup/output/
```

## Generated Files

DIGen generates these files (pipe-delimited):
- Dimension tables: Date.txt, Time.txt, Customer.txt, Account.txt, etc.
- Fact tables: Trade.txt, CashTransaction.txt, Holding.txt, etc.
- Reference tables: Industry.txt, StatusType.txt, TaxRate.txt, etc.

See TPC-DI specification for complete list.

## Integration with PySpark Pipeline

After generating data, run your pipeline:

```python
# In Databricks notebook or via job
%run ./src/main.py --load-type historical
```

Or submit as Databricks job:
```bash
databricks jobs submit \
  --python-file src/main.py \
  --cluster-id <cluster-id> \
  --parameters '["--load-type", "historical"]'
```

## Performance Tips

1. **Use larger clusters** for higher scale factors
2. **Increase Java heap**: `-Xmx8g` or higher
3. **Use DBFS** for persistent storage (`/dbfs/`)
4. **Monitor cluster metrics** during generation
5. **Use spot instances** for cost savings (if acceptable)

## Next Steps

1. Generate data using one of the methods above
2. Verify files in GCS: `dbutils.fs.ls('gs://your-bucket/raw/')`
3. Run PySpark pipeline: `python src/main.py --load-type historical`
4. Process through Bronze → Silver → Gold layers
