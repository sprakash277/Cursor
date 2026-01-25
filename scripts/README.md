# TPC-DI DIGen Scripts

Scripts for downloading and running the official TPC-DI Data Generator (DIGen) on Google Cloud Dataproc.

## Scripts Overview

### 1. `setup_and_run_digen.sh`
Main script that runs on the Dataproc master node to:
- Download and setup DIGen
- Generate TPC-DI data files
- Upload generated files to GCS

**Usage on Dataproc Master:**
```bash
# Set environment variables
export SCALE_FACTOR=1
export GCS_BUCKET=your-tpc-di-bucket
export GCS_RAW_PATH=raw
export PROJECT_ID=your-project-id

# Run the script
bash setup_and_run_digen.sh
```

### 2. `run_digen_on_dataproc.sh`
Wrapper script to execute DIGen on Dataproc cluster from your local machine.

**Usage:**
```bash
# Method 1: Via SSH (recommended for existing cluster)
./run_digen_on_dataproc.sh ssh 1 your-bucket raw your-project-id cluster-name us-central1

# Method 2: As initialization action (creates new cluster)
./run_digen_on_dataproc.sh init 1 your-bucket raw your-project-id cluster-name us-central1

# Method 3: As Dataproc job
./run_digen_on_dataproc.sh job 1 your-bucket raw your-project-id cluster-name us-central1
```

### 3. `download_digen.sh`
Helper script to download DIGen tools locally (for preparation/upload to GCS).

**Usage:**
```bash
export TPCDI_TOOLS_URL="https://www.tpc.org/.../TPCDI_Tools.zip"
./download_digen.sh
```

## Quick Start

### Option 1: Run on Existing Dataproc Cluster (Recommended)

1. **Upload setup script to GCS:**
   ```bash
   gsutil cp scripts/setup_and_run_digen.sh gs://your-bucket/scripts/
   ```

2. **SSH into Dataproc master:**
   ```bash
   gcloud compute ssh your-cluster-m \
       --zone=us-central1-a
   ```

3. **On master node, download and run:**
   ```bash
   # Download script
   gsutil cp gs://your-bucket/scripts/setup_and_run_digen.sh /tmp/
   chmod +x /tmp/setup_and_run_digen.sh
   
   # Set environment variables
   export SCALE_FACTOR=1
   export GCS_BUCKET=your-tpc-di-bucket
   export GCS_RAW_PATH=raw
   export PROJECT_ID=your-project-id
   
   # Run
   /tmp/setup_and_run_digen.sh
   ```

### Option 2: Use Wrapper Script

```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run via SSH
./scripts/run_digen_on_dataproc.sh ssh 1 your-bucket raw your-project-id cluster-name us-central1
```

### Option 3: Pre-download DIGen and Upload to GCS

1. **Download DIGen locally:**
   ```bash
   # Set download URL (get from TPC website)
   export TPCDI_TOOLS_URL="https://www.tpc.org/.../TPCDI_Tools.zip"
   ./scripts/download_digen.sh
   ```

2. **Upload to GCS:**
   ```bash
   gsutil -m cp -r digen_tools/Tools gs://your-bucket/tpc-di-tools/
   ```

3. **Modify `setup_and_run_digen.sh`** to download from GCS instead of external URL.

## Getting TPC-DI Tools

The official TPC-DI Tools (including DIGen.jar) can be downloaded from:
- **URL:** https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp
- **File:** TPCDI_Tools.zip
- **Requirements:** Java 7 or higher

## Configuration

Update these variables in the scripts or set as environment variables:

- `SCALE_FACTOR`: Data volume scale (1 = ~1GB, 10 = ~10GB, etc.)
- `GCS_BUCKET`: Your GCS bucket name
- `GCS_RAW_PATH`: Path in bucket for raw data (e.g., "raw")
- `PROJECT_ID`: Your GCP project ID
- `CLUSTER_NAME`: Dataproc cluster name
- `REGION`: GCP region (e.g., "us-central1")

## DIGen Command Line Options

To see all DIGen options:
```bash
java -jar DIGen.jar -h
```

Common options:
- `-o <dir>`: Output directory (required)
- `-sf <n>`: Scale factor (required)
- `-h`: Show help

## Generated Files

DIGen generates the following files (pipe-delimited text):
- `BatchDate.txt`
- `HR.csv`
- `Customer.txt`
- `Account.txt`
- `Security.txt`
- `Company.txt`
- `Financial.txt`
- `Industry.txt`
- `StatusType.txt`
- `TaxRate.txt`
- `Trade.txt`
- `TradeHistory.txt`
- `CashTransaction.txt`
- `Holding.txt`
- `HoldingHistory.txt`
- `DailyMarket.txt`
- `Prospect.txt`
- `WatchItem.txt`
- `WatchHistory.txt`
- `TradeType.txt`
- `Date.txt`
- `Time.txt`
- `DimDate.txt`
- `DimTime.txt`
- `DimCustomer.txt`
- `DimAccount.txt`
- `DimSecurity.txt`
- `DimCompany.txt`
- `DimBroker.txt`
- `DimTrade.txt`
- `FactCashBalances.txt`
- `FactHoldings.txt`
- `FactMarketHistory.txt`
- `FactWatches.txt`

## Troubleshooting

### Java Not Found
```bash
# Install Java on Dataproc (if not already installed)
sudo apt-get update
sudo apt-get install -y openjdk-8-jdk
```

### DIGen Download Fails
- Manually download TPCDI_Tools.zip from TPC website
- Extract and upload Tools directory to GCS
- Modify script to download from GCS

### GCS Upload Fails
- Verify gsutil is installed: `which gsutil`
- Check GCS bucket permissions
- Verify service account has Storage Admin role

### Out of Memory
- Increase Dataproc master node memory
- Reduce scale factor
- Use larger machine types

## Integration with PySpark Pipeline

After generating data, run your PySpark pipeline:

```bash
python src/main.py --load-type historical
```

The pipeline will read from `gs://your-bucket/raw/` and process through Bronze → Silver → Gold layers.
