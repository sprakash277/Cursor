# TPC-DI Benchmark: Dataproc vs Databricks

A PySpark project implementing a TPC-DI (TPC Data Integration) benchmark on **Google Cloud Dataproc** and **Databricks** with a three-layer data architecture (Bronze, Silver, Gold) and support for both Historical and Incremental loads. The project automatically detects the execution platform and configures accordingly.

## Architecture

### Three-Layer Architecture

1. **Bronze Layer** (`src/layers/bronze_layer.py`)
   - Raw data ingestion from GCS
   - Stores data in Parquet format for efficiency
   - No transformations applied

2. **Silver Layer** (`src/layers/silver_layer.py`)
   - Data cleansing and validation
   - Business rule enforcement
   - Data quality checks

3. **Gold Layer** (`src/layers/gold_layer.py`)
   - Business-ready aggregated data
   - Enriched datasets
   - Optimized for reporting and analytics

### Load Types (TPC-DI Compliant)

- **Historical Load**: Initial load of all historical data
- **Incremental Load**: Load only new/changed data since last load

## Project Structure

```
.
├── config/
│   └── config.yaml              # Configuration file
├── scripts/
│   ├── setup_and_run_digen.sh   # Main DIGen setup/execution script
│   ├── run_digen_on_dataproc.sh # Wrapper to run DIGen on Dataproc
│   ├── download_digen.sh        # Helper to download DIGen tools
│   └── README.md                 # DIGen scripts documentation
├── src/
│   ├── data_generator/
│   │   ├── tpc_di_generator.py  # Python TPC-DI data generator (alternative)
│   │   ├── gcs_uploader.py       # GCS upload utility
│   │   └── generate_data.py     # CLI for data generation
│   ├── layers/
│   │   ├── bronze_layer.py      # Bronze layer implementation
│   │   ├── silver_layer.py      # Silver layer implementation
│   │   └── gold_layer.py        # Gold layer implementation
│   ├── tpc_di/
│   │   └── load_manager.py      # Historical/Incremental load manager
│   ├── utils/
│   │   ├── gcs_utils.py         # GCS connection utilities
│   │   ├── platform_detector.py # Platform detection (Dataproc/Databricks)
│   │   └── performance_logger.py # Performance logging
│   └── main.py                  # Main orchestration script
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Prerequisites

### For Dataproc

1. **Google Cloud Platform Setup**
   - GCP project with Dataproc API enabled
   - GCS bucket for data storage
   - Service account with appropriate permissions:
     - Storage Admin (for GCS access)
     - Dataproc Worker (for cluster operations)

2. **Environment Variables**
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   export GOOGLE_CLOUD_PROJECT="your-project-id"
   ```

### For Databricks

1. **Databricks Workspace Setup**
   - Databricks workspace with cluster access
   - Unity Catalog enabled (for volume storage)
   - Volume created for datagen output (recommended for large files)
   - GCS bucket for data storage
   - Service account or cluster service account with GCS access

2. **Volume Setup (Recommended)**
   ```sql
   -- Create volume for TPC-DI data generation output
   CREATE VOLUME IF NOT EXISTS main.default.tpc_di_data;
   ```
   
   Or use the Databricks UI:
   - Navigate to Catalog Explorer
   - Create a new Volume: `main.default.tpc_di_data`

3. **GCS Access Configuration**
   - Configure cluster with service account that has GCS access, OR
   - Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable in cluster config

### Common Prerequisites

1. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
2. **TPC-DI DIGen Tools**
   - Download TPCDI_Tools.zip from: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp
   - For Databricks: Upload to workspace (e.g., `/Workspace/Users/your-email/datagen/`)

## Configuration

Edit `config/config.yaml` to configure:

- GCS bucket name and paths
- **Dataproc** cluster settings (for Dataproc execution)
- **Databricks** settings (for Databricks execution):
  - Project ID for GCS access
  - Volume configuration (catalog, schema, volume name)
- TPC-DI batch size and checkpointing
- Logging configuration

The platform is automatically detected, but you can override it using the `--platform` flag.

## Usage

### 1. Generate TPC-DI Data

You have two options for generating TPC-DI benchmark data:

#### Option A: Official TPC-DI DIGen (Recommended)

Use the official TPC-DI Data Generator (DIGen). This is the standard tool used for TPC-DI benchmarks.

**For Dataproc:**
```bash
# Make scripts executable
chmod +x scripts/*.sh

# Run on existing Dataproc cluster via SSH
./scripts/run_digen_on_dataproc.sh ssh 1 your-bucket raw your-project-id cluster-name us-central1
```

See `scripts/README.md` for complete Dataproc documentation.

**For Databricks:**
```python
# Use the Databricks notebook template
# See scripts/databricks_notebook.py
```

**Key Features for Databricks:**
- Uses **Volume paths** for datagen output (better performance for large files)
- Automatically unzips TPC-DI Tools zip file from workspace
- Uploads generated data directly to GCS
- Falls back to DBFS if volumes are not available

**Databricks Notebook Setup:**
1. Import `scripts/databricks_notebook.py` as a Databricks notebook
2. Update configuration variables:
   - `TPCDI_ZIP_PATH`: Path to your TPC-DI Tools zip in workspace
   - `VOLUME_CATALOG`, `VOLUME_SCHEMA`, `VOLUME_NAME`: Your volume configuration
   - `GCS_BUCKET`, `GCS_RAW_PATH`, `PROJECT_ID`: Your GCS settings
3. Run the notebook cells sequentially

The notebook will:
- Extract the TPC-DI Tools zip file
- Run DIGen with output to volume path (`/Volumes/.../tpc_di_data/output`)
- Upload generated files to GCS bucket

**Getting DIGen:**
- Download TPCDI_Tools.zip from: https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp
- Or use the download helper: `./scripts/download_digen.sh`

#### Option B: Python Data Generator (Alternative)

The project includes a Python-based data generator for quick testing:

```bash
# Generate all tables with default scale factor (1.0)
python src/data_generator/generate_data.py

# Generate with custom scale factor (10.0 = ~10GB)
python src/data_generator/generate_data.py --scale-factor 10.0

# Generate specific tables only
python src/data_generator/generate_data.py --tables Date Customer Trade

# Generate and upload directly to GCS
python src/data_generator/generate_data.py --upload-to-gcs --scale-factor 1.0
```

#### Generated Tables

**Official DIGen** generates comprehensive TPC-DI tables including:
- Dimension tables: Date, Time, Customer, Account, Security, Company, Broker, etc.
- Fact tables: Trade, CashTransaction, Holding, DailyMarket, etc.
- Reference tables: Industry, StatusType, TaxRate, TradeType, etc.

**Python Generator** creates simplified versions:
- **Date.txt** - Date dimension (2000-2030)
- **Time.txt** - Time dimension (24-hour granularity)
- **Customer.txt** - Customer dimension (~50K records per SF)
- **Account.txt** - Account dimension (~30K records per SF)
- **Security.txt** - Security dimension (~5K records per SF)
- **Company.txt** - Company dimension (~1K records per SF)
- **Trade.txt** - Trade fact table (~100K records per SF)

#### Scale Factor

The scale factor controls data volume:
- Scale Factor 1.0 ≈ 1GB of data
- Scale Factor 10.0 ≈ 10GB of data
- Scale Factor 100.0 ≈ 100GB of data

### 2. Prepare Raw Data

If you have existing TPC-DI data files, upload them to the GCS bucket at the path specified in `config.yaml` under `gcs.raw_data_path`.

Alternatively, use the data generator (see step 1) to create synthetic data.

### 3. Configure Tables

Edit `src/main.py` to define your table configurations in the `table_configs` dictionary. Example:

```python
table_configs = {
    "DimDate": {
        "file_name": "Date.txt",
        "format": "csv",
        "options": {"header": "true", "delimiter": "|"}
    },
    "FactSales": {
        "file_name": "Sales.txt",
        "format": "csv",
        "timestamp_column": "UpdateDate",  # For incremental loads
        "transformations": {...},
        "gold_config": {
            "aggregate": {
                "group_by": ["DateKey", "ProductKey"],
                "aggregations": {"Amount": sum, "Quantity": sum}
            }
        }
    }
}
```

### 4. Run Historical Load

```bash
python src/main.py --load-type historical
```

### 5. Run Incremental Load

```bash
python src/main.py --load-type incremental
```

## Running the Pipeline

### Platform Auto-Detection

The pipeline automatically detects whether it's running on Dataproc or Databricks. You can also explicitly specify the platform:

```bash
python src/main.py --load-type historical --platform dataproc
python src/main.py --load-type historical --platform databricks
```

### Running on Dataproc

#### Submit Job to Existing Cluster

```bash
gcloud dataproc jobs submit pyspark \
    --cluster=your-cluster-name \
    --region=us-central1 \
    --py-files=src/utils,src/layers,src/tpc_di \
    src/main.py \
    -- --load-type historical
```

#### Create and Run on New Cluster

```bash
gcloud dataproc clusters create tpc-di-cluster \
    --region=us-central1 \
    --num-workers=4 \
    --worker-machine-type=n1-standard-4 \
    --master-machine-type=n1-standard-4

gcloud dataproc jobs submit pyspark \
    --cluster=tpc-di-cluster \
    --region=us-central1 \
    --py-files=src/utils,src/layers,src/tpc_di \
    src/main.py \
    -- --load-type historical
```

### Running on Databricks

#### Option 1: Databricks Notebook

1. Create a new notebook in your Databricks workspace
2. Import the code from `src/main.py`
3. Configure your settings in `config/config.yaml`
4. Run the notebook

#### Option 2: Databricks Jobs API

```bash
databricks jobs create --json-file job_config.json
```

Example `job_config.json`:
```json
{
  "name": "TPC-DI Historical Load",
  "new_cluster": {
    "spark_version": "13.3.x-scala2.12",
    "node_type_id": "i3.xlarge",
    "num_workers": 4
  },
  "libraries": [
    {"pypi": {"package": "pyspark==3.5.0"}},
    {"pypi": {"package": "google-cloud-storage==2.14.0"}},
    {"pypi": {"package": "pyyaml==6.0.1"}}
  ],
  "spark_python_task": {
    "python_file": "dbfs:/path/to/src/main.py",
    "parameters": ["--load-type", "historical"]
  }
}
```

#### Option 3: Databricks CLI

```bash
# Upload code to DBFS
databricks fs cp -r src dbfs:/tpc-di/src

# Run job
databricks jobs run-now --job-id <job-id> \
  --python-params '["--load-type", "historical"]'
```

## Performance Logging

The project includes comprehensive performance logging that tracks:

- Stage execution time
- Record counts processed
- Data throughput (records/sec, MB/sec)
- Stage-specific metrics
- Platform-specific optimizations

Logs are written to both console and file (configured in `config.yaml`).

### Platform-Specific Optimizations

**Dataproc:**
- Adaptive query execution enabled
- Skew join optimization
- Local shuffle reader optimization

**Databricks:**
- Databricks I/O cache enabled
- Delta Lake optimizations (if using Delta)
- Auto-compaction enabled

## TPC-DI Compliance

This implementation follows TPC-DI specifications for:

- **Historical Load**: Processes all available historical data without filtering
- **Incremental Load**: Filters data based on timestamp columns and merges with existing data
- **Checkpointing**: Tracks last load timestamps for incremental processing
- **Data Quality**: Implements validation and cleansing in Silver layer

## Customization

### Adding Custom Transformations

In Silver layer, add transformations in table config:

```python
"transformations": {
    "Amount": lambda x: x.cast("decimal(18,2)"),
    "Status": lambda x: upper(trim(x))
}
```

### Adding Validation Rules

```python
"validation_rules": {
    "Amount": lambda col: col > 0,
    "Date": lambda col: col.isNotNull()
}
```

### Custom Gold Aggregations

```python
"gold_config": {
    "aggregate": {
        "group_by": ["DateKey", "ProductKey"],
        "aggregations": {
            "Amount": sum,
            "Quantity": sum,
            "Price": avg
        }
    }
}
```

## Dataproc vs Databricks Comparison

### Key Differences

| Feature | Dataproc | Databricks |
|---------|----------|-----------|
| **Data Generation** | Uses DBFS or local storage | Uses **Volumes** (recommended) or DBFS |
| **GCS Access** | Native GCS connector | Built-in `gs://` protocol support |
| **Performance** | Standard Spark optimizations | Databricks-specific optimizations (I/O cache, Delta) |
| **Cost** | Pay-per-use cluster | Pay-per-DBU usage |
| **Setup** | Requires cluster creation | Workspace-based, faster setup |

### When to Use Each Platform

**Use Dataproc if:**
- You're already using GCP infrastructure
- You need fine-grained control over cluster configuration
- Cost optimization through preemptible instances is important
- You prefer open-source Spark without vendor-specific features

**Use Databricks if:**
- You need faster development cycles
- You want built-in collaboration features
- You're using Delta Lake or other Databricks-specific features
- You prefer managed Spark with automatic optimizations

### Volume Path Usage (Databricks)

The Databricks notebook uses **Volume paths** for datagen output by default:

- **Volume Path**: `/Volumes/<catalog>/<schema>/<volume_name>/output`
- **Benefits**: Better performance for large files, faster I/O
- **Fallback**: Automatically falls back to DBFS if volumes are not available

To configure volumes:
1. Create a volume in Unity Catalog
2. Update `VOLUME_CATALOG`, `VOLUME_SCHEMA`, `VOLUME_NAME` in the notebook
3. Or set `USE_VOLUME = False` to use DBFS paths

## Troubleshooting

### Common Issues

1. **GCS Access Issues**
   - **Dataproc**: Verify service account credentials and permissions
   - **Databricks**: Check cluster service account or `GOOGLE_APPLICATION_CREDENTIALS` environment variable
   - Ensure service account has "Storage Object Admin" role on GCS bucket

2. **Schema Mismatches**
   - Ensure table schemas match your data structure
   - Check delimiter and header settings in table configurations

3. **Performance Issues**
   - **Dataproc**: Adjust Spark configurations in `create_spark_session()` based on cluster size
   - **Databricks**: Enable I/O cache and Delta optimizations (already configured)
   - Check partition sizes and adjust `batch_size` in config

4. **Databricks Volume Not Found**
   - Ensure Unity Catalog is enabled
   - Verify volume exists: `SHOW VOLUMES IN main.default`
   - Check volume path format: `/Volumes/<catalog>/<schema>/<volume_name>`
   - The notebook will automatically fall back to DBFS if volumes are unavailable

5. **Platform Detection Issues**
   - Manually specify platform: `--platform dataproc` or `--platform databricks`
   - Check environment variables for platform-specific indicators

6. **TPC-DI DIGen Issues (Databricks)**
   - Ensure Java 8 is installed (notebook handles this)
   - Verify TPC-DI Tools zip file path is correct
   - Check that Apache Commons CLI dependency is downloaded
   - Review DIGen output for specific error messages

## Benchmarking

This project is designed for comparing performance between Dataproc and Databricks:

1. **Generate data** using the same scale factor on both platforms
2. **Run historical load** and measure:
   - Total execution time
   - Throughput (records/sec, MB/sec)
   - Resource utilization
3. **Run incremental load** and measure:
   - Delta processing time
   - Merge performance
4. **Compare results** using the performance logs

Performance metrics are logged to both console and file for easy comparison.

## License

This project is provided as-is for TPC-DI benchmarking purposes.
