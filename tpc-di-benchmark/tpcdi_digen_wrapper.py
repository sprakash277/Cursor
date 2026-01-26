"""
TPC-DI DIGen Wrapper - Uses official TPC-DI DIGen tool to generate data
"""

import os
import subprocess
import shutil
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.files import DbfsFileInfo
import yaml


class TPCIDIGenWrapper:
    """Wrapper for TPC-DI DIGen tool"""
    
    def __init__(self, digen_path: str = None, java_path: str = "java"):
        """
        Initialize DIGen wrapper
        
        Args:
            digen_path: Path to DIGen.jar (if None, will look in common locations)
            java_path: Path to Java executable (default: "java")
        """
        self.java_path = java_path
        self.digen_path = digen_path or self._find_digen()
        
        if not self.digen_path or not Path(self.digen_path).exists():
            raise FileNotFoundError(
                f"DIGen.jar not found at {digen_path}. "
                "Please download from https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp"
            )
    
    def _find_digen(self) -> str:
        """Try to find DIGen.jar in common locations"""
        common_paths = [
            "./Tools/DIGen.jar",
            "./tpcdi_tools/DIGen.jar",
            "/tmp/tpcdi_tools/DIGen.jar",
            os.path.expanduser("~/tpcdi_tools/DIGen.jar"),
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        return None
    
    def check_java(self) -> bool:
        """Check if Java is available"""
        try:
            result = subprocess.run(
                [self.java_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"Java version check:")
            print(result.stderr if result.stderr else result.stdout)
            return True
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            print(f"Java not found: {e}")
            return False
    
    def check_pdgf(self) -> bool:
        """Check if PDGF directory exists (must be lowercase 'pdgf')"""
        digen_dir = Path(self.digen_path).parent
        pdgf_path = digen_dir / "pdgf"
        
        if pdgf_path.exists() and pdgf_path.is_dir():
            return True
        
        # Check for uppercase PDGF
        pdgf_upper = digen_dir / "PDGF"
        if pdgf_upper.exists() and pdgf_upper.is_dir():
            print(f"Warning: Found 'PDGF' directory, but need lowercase 'pdgf'")
            print(f"Please rename: mv {pdgf_upper} {pdgf_path}")
            return False
        
        print(f"Warning: pdgf directory not found at {pdgf_path}")
        return False
    
    def generate_data(
        self,
        scale_factor: int = 1,
        output_dir: str = "./tpcdi_data",
        validate: bool = True
    ) -> str:
        """
        Generate TPC-DI data using DIGen tool
        
        Args:
            scale_factor: Scale factor (1 = ~1GB, 10 = ~10GB, etc.)
            output_dir: Output directory for generated data
            validate: Whether to validate Java and PDGF before running
            
        Returns:
            Path to output directory
        """
        if validate:
            if not self.check_java():
                raise RuntimeError("Java is required but not found")
            
            if not self.check_pdgf():
                print("Warning: PDGF directory check failed, but continuing...")
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Get DIGen directory (must run from Tools directory)
        digen_dir = Path(self.digen_path).parent
        digen_jar = Path(self.digen_path).name
        
        print(f"\n{'='*60}")
        print(f"TPC-DI DIGen Data Generation")
        print(f"{'='*60}")
        print(f"Scale Factor: {scale_factor}")
        print(f"Output Directory: {output_path.absolute()}")
        print(f"DIGen JAR: {self.digen_path}")
        print(f"{'='*60}\n")
        
        # Run DIGen
        cmd = [
            self.java_path,
            "-jar",
            digen_jar,
            "-o", str(output_path.absolute()),
            "-sf", str(scale_factor)
        ]
        
        print(f"Running: {' '.join(cmd)}")
        print(f"Working directory: {digen_dir}\n")
        
        try:
            result = subprocess.run(
                cmd,
                cwd=str(digen_dir),
                check=True,
                capture_output=False,  # Show output in real-time
                text=True
            )
            
            print(f"\n✓ Data generation completed successfully!")
            print(f"  Output: {output_path.absolute()}")
            
            # List generated files
            self._list_generated_files(output_path)
            
            return str(output_path.absolute())
            
        except subprocess.CalledProcessError as e:
            print(f"\n✗ Data generation failed with exit code {e.returncode}")
            raise
        except Exception as e:
            print(f"\n✗ Error: {str(e)}")
            raise
    
    def _list_generated_files(self, output_path: Path):
        """List generated files"""
        print(f"\nGenerated files:")
        for file_path in sorted(output_path.rglob("*")):
            if file_path.is_file():
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"  {file_path.relative_to(output_path)} ({size_mb:.2f} MB)")
    
    def upload_to_databricks(
        self,
        local_path: str,
        workspace_url: str,
        token: str,
        dbfs_path: str = "dbfs:/tmp/tpcdi"
    ):
        """
        Upload generated data to Databricks DBFS
        
        Args:
            local_path: Local path to generated data
            workspace_url: Databricks workspace URL
            token: Databricks token
            dbfs_path: DBFS destination path
        """
        print(f"\n{'='*60}")
        print(f"Uploading to Databricks")
        print(f"{'='*60}")
        print(f"Source: {local_path}")
        print(f"Destination: {dbfs_path}")
        print(f"{'='*60}\n")
        
        w = WorkspaceClient(host=workspace_url, token=token)
        local_path_obj = Path(local_path)
        
        # Remove dbfs: prefix if present
        dbfs_dest = dbfs_path.replace("dbfs:", "")
        
        # Upload files
        uploaded_count = 0
        for file_path in local_path_obj.rglob("*"):
            if file_path.is_file():
                relative_path = file_path.relative_to(local_path_obj)
                dbfs_file_path = f"{dbfs_dest}/{relative_path}"
                
                # Create parent directory if needed
                dbfs_dir = "/".join(dbfs_file_path.split("/")[:-1])
                try:
                    w.dbfs.mkdirs(dbfs_dir)
                except:
                    pass  # Directory might already exist
                
                # Upload file
                print(f"Uploading: {relative_path} -> {dbfs_file_path}")
                with open(file_path, 'rb') as f:
                    w.dbfs.put(dbfs_file_path, contents=f.read(), overwrite=True)
                
                uploaded_count += 1
        
        print(f"\n✓ Uploaded {uploaded_count} files to Databricks")
    
    def create_databricks_notebook(
        self,
        dbfs_path: str = "dbfs:/tmp/tpcdi",
        catalog: str = "hive_metastore",
        schema: str = "tpcdi"
    ) -> str:
        """
        Generate Databricks notebook code to load DIGen output into tables
        
        Args:
            dbfs_path: DBFS path where data is stored
            catalog: Catalog name
            schema: Schema name
            
        Returns:
            Notebook code as string
        """
        notebook_code = f"""
# Databricks notebook source
# MAGIC %md
# MAGIC # TPC-DI Data Loading from DIGen Output
# MAGIC 
# MAGIC This notebook loads TPC-DI data generated by the official DIGen tool into Databricks tables.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------
dbfs_path = "{dbfs_path}"
catalog = "{catalog}"
schema = "{schema}"

# COMMAND ----------
# MAGIC %md
# MAGIC ## Create Schema

# COMMAND ----------
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {{catalog}}.{{schema}}")
print(f"✓ Created schema: {{catalog}}.{{schema}}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Load Dimension Tables

# COMMAND ----------
from pyspark.sql import SparkSession
from pyspark.sql.functions import *

spark = SparkSession.builder.appName("TPC-DI-Loader").getOrCreate()

# COMMAND ----------
# MAGIC %md
# MAGIC ### DimDate

# COMMAND ----------
# Load Date dimension (DIGen generates Date.txt or Date_*.txt for large scale factors)
# Try both naming patterns
try:
    date_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Date.txt")
except:
    # For large scale factors, files might be split
    date_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Date_*.txt")

# Add column names based on TPC-DI spec
date_columns = [
    "SK_DateID", "DateValue", "DateDesc", "CalendarYearID", 
    "CalendarYearDesc", "CalendarQtrID", "CalendarQtrDesc",
    "CalendarMonthID", "CalendarMonthDesc", "CalendarWeekID",
    "CalendarWeekDesc", "DayOfWeekNum", "DayOfWeekDesc",
    "FiscalYearID", "FiscalYearDesc", "FiscalQtrID", "FiscalQtrDesc",
    "HolidayFlag"
]

# Rename columns if they match expected count
if len(date_df.columns) == len(date_columns):
    for old_col, new_col in zip(date_df.columns, date_columns):
        date_df = date_df.withColumnRenamed(old_col, new_col)

# Write as Delta table
date_df.write \\
    .format("delta") \\
    .mode("overwrite") \\
    .saveAsTable(f"{{catalog}}.{{schema}}.DimDate")

print(f"✓ Loaded DimDate: {{date_df.count()}} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ### DimTime

# COMMAND ----------
# Load Time dimension (DIGen generates Time.txt or Time_*.txt)
try:
    time_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Time.txt")
except:
    time_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Time_*.txt")

# Add column names based on TPC-DI spec
time_columns = [
    "SK_TimeID", "TimeValue", "HourID", "HourDesc",
    "MinuteID", "MinuteDesc", "SecondID", "SecondDesc",
    "MarketHoursFlag", "OfficeHoursFlag"
]

if len(time_df.columns) == len(time_columns):
    for old_col, new_col in zip(time_df.columns, time_columns):
        time_df = time_df.withColumnRenamed(old_col, new_col)

time_df.write \\
    .format("delta") \\
    .mode("overwrite") \\
    .saveAsTable(f"{{catalog}}.{{schema}}.DimTime")

print(f"✓ Loaded DimTime: {{time_df.count()}} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ### DimCustomer

# COMMAND ----------
# Load Customer dimension (DIGen generates Customer.txt or Customer_*.txt)
try:
    customer_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Customer.txt")
except:
    customer_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Customer_*.txt")

# Note: Column names depend on DIGen version - adjust as needed
# TPC-DI spec defines many columns for DimCustomer
customer_df.write \\
    .format("delta") \\
    .mode("overwrite") \\
    .saveAsTable(f"{{catalog}}.{{schema}}.DimCustomer")

print(f"✓ Loaded DimCustomer: {{customer_df.count()}} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ### DimSecurity

# COMMAND ----------
# Load Security dimension (DIGen generates Security.txt or Security_*.txt)
try:
    security_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Security.txt")
except:
    security_df = spark.read \\
        .option("delimiter", "|") \\
        .option("header", "false") \\
        .csv(f"{{dbfs_path}}/Security_*.txt")

security_df.write \\
    .format("delta") \\
    .mode("overwrite") \\
    .saveAsTable(f"{{catalog}}.{{schema}}.DimSecurity")

print(f"✓ Loaded DimSecurity: {{security_df.count()}} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Load Fact Tables

# COMMAND ----------
# MAGIC %md
# MAGIC ### FactDailyMarket

# COMMAND ----------
# Load Daily Market fact (DIGen generates DailyMarket.txt or DailyMarket_*.txt)
# For large scale factors, files are typically split
daily_market_df = spark.read \\
    .option("delimiter", "|") \\
    .option("header", "false") \\
    .csv(f"{{dbfs_path}}/DailyMarket*.txt")

daily_market_df.write \\
    .format("delta") \\
    .mode("overwrite") \\
    .saveAsTable(f"{{catalog}}.{{schema}}.FactDailyMarket")

print(f"✓ Loaded FactDailyMarket: {{daily_market_df.count()}} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ### FactTrade

# COMMAND ----------
# Load Trade fact (DIGen generates Trade.txt or Trade_*.txt)
# For large scale factors, files are typically split
trade_df = spark.read \\
    .option("delimiter", "|") \\
    .option("header", "false") \\
    .csv(f"{{dbfs_path}}/Trade*.txt")

trade_df.write \\
    .format("delta") \\
    .mode("overwrite") \\
    .saveAsTable(f"{{catalog}}.{{schema}}.FactTrade")

print(f"✓ Loaded FactTrade: {{trade_df.count()}} rows")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------
print("\\n" + "="*60)
print("TPC-DI Data Loading Complete")
print("="*60)
print(f"Schema: {{catalog}}.{{schema}}")
print(f"\\nTables created:")
for table in ["DimDate", "DimTime", "DimCustomer", "DimSecurity", "FactDailyMarket", "FactTrade"]:
    try:
        count = spark.sql(f"SELECT COUNT(*) as cnt FROM {{catalog}}.{{schema}}.{{table}}").collect()[0]['cnt']
        print(f"  {{table}}: {{count:,}} rows")
    except Exception as e:
        print(f"  {{table}}: Error - {{str(e)}}")
"""
        
        return notebook_code


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TPC-DI DIGen Wrapper")
    parser.add_argument("--digen-path", help="Path to DIGen.jar")
    parser.add_argument("--java-path", default="java", help="Path to Java executable")
    parser.add_argument("--scale-factor", type=int, default=1, help="Scale factor")
    parser.add_argument("--output-dir", default="./tpcdi_data", help="Output directory")
    parser.add_argument("--upload", action="store_true", help="Upload to Databricks after generation")
    parser.add_argument("--workspace-url", help="Databricks workspace URL")
    parser.add_argument("--token", help="Databricks token")
    parser.add_argument("--dbfs-path", default="dbfs:/tmp/tpcdi", help="DBFS path")
    parser.add_argument("--generate-notebook", action="store_true", help="Generate Databricks notebook code")
    
    args = parser.parse_args()
    
    try:
        wrapper = TPCIDIGenWrapper(args.digen_path, args.java_path)
        
        # Generate data
        output_path = wrapper.generate_data(args.scale_factor, args.output_dir)
        
        # Upload to Databricks if requested
        if args.upload:
            if not args.workspace_url or not args.token:
                print("Error: --workspace-url and --token required for upload")
                exit(1)
            wrapper.upload_to_databricks(output_path, args.workspace_url, args.token, args.dbfs_path)
        
        # Generate notebook if requested
        if args.generate_notebook:
            notebook_code = wrapper.create_databricks_notebook(args.dbfs_path)
            notebook_path = Path(args.output_dir) / "load_tpcdi_data.py"
            with open(notebook_path, 'w') as f:
                f.write(notebook_code)
            print(f"\n✓ Notebook code saved to: {notebook_path}")
            
    except Exception as e:
        print(f"Error: {str(e)}")
        exit(1)
