# TPC-DI Benchmark on Google Cloud Dataproc

A PySpark project implementing a TPC-DI (TPC Data Integration) benchmark on Google Cloud Dataproc with a three-layer data architecture (Bronze, Silver, Gold) and support for both Historical and Incremental loads.

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
│   │   └── performance_logger.py # Performance logging
│   └── main.py                  # Main orchestration script
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Prerequisites

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

3. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

Edit `config/config.yaml` to configure:

- GCS bucket name and paths
- Dataproc cluster settings
- TPC-DI batch size and checkpointing
- Logging configuration

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
# See scripts/databricks_notebook.py or scripts/DATABRICKS_README.md
```

See `scripts/DATABRICKS_README.md` for complete Databricks documentation.

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

## Running on Dataproc

### Submit Job to Dataproc Cluster

```bash
gcloud dataproc jobs submit pyspark \
    --cluster=your-cluster-name \
    --region=us-central1 \
    --py-files=src/utils,src/layers,src/tpc_di \
    src/main.py \
    -- --load-type historical
```

### Create and Run on New Cluster

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

## Performance Logging

The project includes comprehensive performance logging that tracks:

- Stage execution time
- Record counts processed
- Data throughput (records/sec, MB/sec)
- Stage-specific metrics

Logs are written to both console and file (configured in `config.yaml`).

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

## Troubleshooting

1. **GCS Access Issues**: Verify service account credentials and permissions
2. **Schema Mismatches**: Ensure table schemas match your data structure
3. **Performance**: Adjust Spark configurations in `create_spark_session()` based on cluster size

## License

This project is provided as-is for TPC-DI benchmarking purposes.
