# TPC-DI Benchmark: Databricks vs Dataproc

This project benchmarks the performance of Databricks and Dataproc on TPC-DI (Transaction Processing Performance Council - Data Integration) workloads.

## Overview

TPC-DI is a benchmark specification for data integration workloads. This project:
1. Generates TPC-DI compliant synthetic data using Databricks
2. Runs benchmark queries on both Databricks and Dataproc
3. Compares performance metrics between the two platforms

## Prerequisites

- **Java 7+** (Java 8+ recommended) - Required for TPC-DI DIGen tool
- **Python 3.8+**
- **TPC-DI DIGen Tool** - Download from [TPC.org](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp)
- Databricks workspace with appropriate permissions
- Google Cloud Project with Dataproc API enabled
- Access to both platforms with authentication tokens/credentials

See [SETUP_DIGEN.md](SETUP_DIGEN.md) for detailed DIGen setup instructions.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your actual credentials:
- Databricks workspace URL and token
- GCP project ID and bucket name
- Service account credentials path

### 3. Update Configuration

Edit `config.yaml` to match your setup:
- Scale factor for data generation
- Databricks cluster/warehouse IDs
- Dataproc cluster configuration
- Query file paths

## Usage

### Step 1: Download TPC-DI DIGen Tool

1. Download the TPCDI_Tools zip file from:
   https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp

2. Extract the zip file:
   ```bash
   unzip TPCDI_Tools.zip
   cd Tools
   ```

3. **Important**: Rename the `PDGF` directory to lowercase `pdgf`:
   ```bash
   mv PDGF pdgf
   ```

### Step 2: Generate TPC-DI Data Using DIGen

#### Option A: Using the Python Wrapper (Recommended)

```bash
python tpcdi_digen_wrapper.py \
    --digen-path ./Tools/DIGen.jar \
    --scale-factor 1 \
    --output-dir ./tpcdi_data \
    --generate-notebook
```

This will:
- Run the official DIGen tool to generate data
- Create a Databricks notebook for loading the data

#### Option B: Using DIGen Directly

```bash
cd Tools
java -jar DIGen.jar -o ../tpcdi_data/ -sf 1
```

The `-sf` parameter is the scale factor (1 = ~1GB, 10 = ~10GB, etc.)

### Step 3: Upload Data to Databricks

#### Option A: Using the Wrapper Script

```bash
python tpcdi_digen_wrapper.py \
    --digen-path ./Tools/DIGen.jar \
    --scale-factor 1 \
    --output-dir ./tpcdi_data \
    --upload \
    --workspace-url https://your-workspace.cloud.databricks.com \
    --token your-token \
    --dbfs-path dbfs:/tmp/tpcdi
```

#### Option B: Using Databricks CLI

```bash
databricks fs cp -r ./tpcdi_data dbfs:/tmp/tpcdi/
```

### Step 4: Load Data into Databricks Tables

1. Copy the generated notebook code from `tpcdi_data/load_tpcdi_data.py` (if using wrapper)
2. Create a new Databricks notebook
3. Paste the code and run it on your cluster

The notebook will create:
- **Dimension Tables**: DimDate, DimTime, DimCustomer, DimSecurity
- **Fact Tables**: FactDailyMarket, FactTrade

### Step 2: Create Tables

After data generation, create external tables in Databricks:

```sql
CREATE SCHEMA IF NOT EXISTS hive_metastore.tpcdi;

CREATE TABLE IF NOT EXISTS hive_metastore.tpcdi.DimDate
USING PARQUET
LOCATION 'dbfs:/tmp/tpcdi/DimDate';

-- Repeat for other tables (DimTime, DimCustomer, DimSecurity, FactDailyMarket, FactTrade)
```

### Step 3: Copy Data to Dataproc

Copy the generated data from Databricks to GCS for Dataproc:

```bash
# Using databricks-cli or dbutils
databricks fs cp -r dbfs:/tmp/tpcdi gs://your-bucket/tpcdi/
```

Or use the Databricks UI to download and upload to GCS.

### Step 4: Create Tables in Dataproc

Create tables in Dataproc pointing to the GCS data:

```sql
CREATE SCHEMA IF NOT EXISTS tpcdi;

CREATE TABLE IF NOT EXISTS tpcdi.DimDate
USING PARQUET
LOCATION 'gs://your-bucket/tpcdi/DimDate';

-- Repeat for other tables
```

### Step 5: Run Benchmark

```bash
python benchmark.py --config config.yaml --iterations 3
```

This will:
- Run each query multiple times on both platforms
- Calculate average execution times
- Generate a comparison report

## Project Structure

```
tpc-di-benchmark/
├── config.yaml                 # Configuration file
├── requirements.txt            # Python dependencies
├── databricks_tpcdi_generator.py  # Data generation script
├── benchmark.py                # Benchmark runner
├── queries/                    # SQL query files
│   ├── q1.sql
│   └── q2.sql
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## TPC-DI Specification

This implementation follows the TPC-DI v1.1.0 specification. The benchmark includes:

### Dimension Tables
- **DimDate**: Date dimension with calendar and fiscal attributes
- **DimTime**: Time dimension for intraday analysis
- **DimCustomer**: Customer information
- **DimSecurity**: Security/stock information

### Fact Tables
- **FactDailyMarket**: Daily market data (OHLCV)
- **FactTrade**: Individual trade transactions

## Benchmark Queries

The benchmark includes sample queries that test:
1. **Query 1**: Aggregation on daily market data
2. **Query 2**: Customer trade analysis with joins

You can add more queries by:
1. Creating SQL files in the `queries/` directory
2. Adding entries to `config.yaml` under `benchmark.queries`

## Results

Benchmark results are saved as:
- `benchmark_results.json`: Detailed results with all iterations
- `benchmark_results.csv`: Summary comparison table

## Notes

- **Data Generation**: This project uses the official TPC-DI DIGen tool for data generation, ensuring full TPC-DI specification compliance
- **Scale Factor**: Determines data volume: SF=1 ≈ 1GB, SF=10 ≈ 10GB
- **Java Requirement**: DIGen requires Java 7+ (Java 8+ recommended)
- **PDGF Directory**: The DIGen tool requires a `pdgf` directory (lowercase) - make sure to rename `PDGF` to `pdgf` after extraction
- **Cluster Configuration**: Ensure both platforms have similar cluster configurations for fair comparison
- **Performance Metrics**: Network latency and cluster startup time are not included in query execution times

## Troubleshooting

### Databricks Connection Issues
- Verify your workspace URL and token
- Ensure your token has appropriate permissions
- Check that the SQL warehouse is running

### Dataproc Connection Issues
- Verify GCP credentials are set: `export GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json`
- Ensure Dataproc API is enabled in your GCP project
- Check cluster is running and accessible

### Data Generation Issues
- For large scale factors, ensure sufficient cluster resources
- Monitor DBFS storage limits
- Consider using Delta Lake format for better performance

## License

This project is for benchmarking purposes. TPC-DI is a trademark of the Transaction Processing Performance Council.

## References

- [TPC-DI Specification](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp)
- [Databricks Documentation](https://docs.databricks.com/)
- [Google Cloud Dataproc Documentation](https://cloud.google.com/dataproc/docs)
