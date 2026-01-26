"""
TPC-DI Data Generator for Databricks (Alternative Implementation)

NOTE: For full TPC-DI specification compliance, use the official DIGen tool
via tpcdi_digen_wrapper.py instead of this script.

This script provides a Spark-based alternative that generates TPC-DI-like data
directly in Databricks without requiring the DIGen tool.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from databricks import sql
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.compute import DataSecurityMode, ClusterSpec
import time


class TPCIDataGenerator:
    """Generate TPC-DI data on Databricks"""
    
    def __init__(self, workspace_url: str, token: str, cluster_id: str = None):
        """
        Initialize the TPC-DI data generator
        
        Args:
            workspace_url: Databricks workspace URL
            token: Databricks personal access token
            cluster_id: Optional cluster ID to use
        """
        self.workspace_url = workspace_url
        self.token = token
        self.cluster_id = cluster_id
        self.w = WorkspaceClient(host=workspace_url, token=token)
        
    def download_digen(self, output_dir: str = "/tmp/tpcdi_tools"):
        """
        Download and setup TPC-DI DIGen tool
        
        Args:
            output_dir: Directory to extract tools
        """
        print("Note: TPC-DI DIGen tool must be downloaded manually from:")
        print("https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp")
        print(f"Extract to: {output_dir}")
        print("\nAfter extraction, ensure the 'PDGF' directory is renamed to 'pdgf' (lowercase)")
        
    def generate_data_databricks(self, scale_factor: int = 1, output_path: str = "dbfs:/tmp/tpcdi"):
        """
        Generate TPC-DI data using Databricks
        
        Args:
            scale_factor: Scale factor for data generation (1 = ~1GB)
            output_path: DBFS path to store generated data
        """
        print(f"Generating TPC-DI data with scale factor {scale_factor}...")
        
        # Create notebook code for data generation
        notebook_code = f"""
# Databricks notebook source
# MAGIC %md
# MAGIC # TPC-DI Data Generation
# MAGIC 
# MAGIC This notebook generates TPC-DI benchmark data following the TPC-DI specification.

# COMMAND ----------
# MAGIC %md
# MAGIC ## Setup

# COMMAND ----------
scale_factor = {scale_factor}
output_path = "{output_path}"

# COMMAND ----------
# MAGIC %md
# MAGIC ## Generate Dimension Tables

# COMMAND ----------
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime, timedelta

spark = SparkSession.builder.appName("TPC-DI-Generator").getOrCreate()

# COMMAND ----------
# MAGIC %md
# MAGIC ### Date Dimension

# COMMAND ----------
# Generate date dimension (2000-01-01 to 2020-12-31)
start_date = datetime(2000, 1, 1)
end_date = datetime(2020, 12, 31)
dates = []
current_date = start_date

while current_date <= end_date:
    dates.append((
        current_date.strftime("%Y-%m-%d"),
        current_date.year,
        current_date.month,
        current_date.day,
        current_date.strftime("%A"),
        current_date.strftime("%B"),
        current_date.weekday(),
        current_date.isocalendar()[1],  # week number
        "Q" + str((current_date.month - 1) // 3 + 1),
        current_date.strftime("%Y-%m")
    ))
    current_date += timedelta(days=1)

date_df = spark.createDataFrame(dates, [
    "SK_DateID", "DateValue", "DateDesc", "CalendarYearID", 
    "CalendarYearDesc", "CalendarQtrID", "CalendarQtrDesc",
    "CalendarMonthID", "CalendarMonthDesc", "CalendarWeekID",
    "CalendarWeekDesc", "DayOfWeekNum", "DayOfWeekDesc",
    "FiscalYearID", "FiscalYearDesc", "FiscalQtrID", "FiscalQtrDesc",
    "HolidayFlag"
])

# Simplified version - full TPC-DI spec has more fields
date_df = spark.createDataFrame([
    (i, d[0], d[0], d[1], str(d[1]), f"Q{(d[2]-1)//3+1}", 
     f"Q{(d[2]-1)//3+1} {d[1]}", d[2], d[9], 
     f"W{d[7]}", f"W{d[7]} {d[1]}", d[6], d[4], 
     d[1], str(d[1]), f"Q{(d[2]-1)//3+1}", f"Q{(d[2]-1)//3+1} {d[1]}", 
     "N") 
    for i, d in enumerate(dates, 1)
], [
    "SK_DateID", "DateValue", "DateDesc", "CalendarYearID", 
    "CalendarYearDesc", "CalendarQtrID", "CalendarQtrDesc",
    "CalendarMonthID", "CalendarMonthDesc", "CalendarWeekID",
    "CalendarWeekDesc", "DayOfWeekNum", "DayOfWeekDesc",
    "FiscalYearID", "FiscalYearDesc", "FiscalQtrID", "FiscalQtrDesc",
    "HolidayFlag"
])

date_df.write.mode("overwrite").parquet(f"{{output_path}}/DimDate")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Time Dimension

# COMMAND ----------
# Generate time dimension (all minutes in a day)
times = []
for hour in range(24):
    for minute in range(60):
        times.append((
            hour * 100 + minute,  # SK_TimeID
            f"{{hour:02d}}:{{minute:02d}}:00",
            hour,
            minute,
            "AM" if hour < 12 else "PM",
            "Morning" if hour < 12 else "Afternoon" if hour < 18 else "Evening"
        ))

time_df = spark.createDataFrame(times, [
    "SK_TimeID", "TimeValue", "HourID", "HourDesc",
    "MinuteID", "MinuteDesc", "SecondID", "SecondDesc",
    "MarketHoursFlag", "OfficeHoursFlag"
])

# Simplified version
time_df = spark.createDataFrame([
    (t[0], t[1], t[2], f"Hour {{t[2]}}", t[3], f"Minute {{t[3]}}", 
     0, "Second 0", "Y" if 9 <= t[2] < 16 else "N", 
     "Y" if 9 <= t[2] < 17 else "N")
    for t in times
], [
    "SK_TimeID", "TimeValue", "HourID", "HourDesc",
    "MinuteID", "MinuteDesc", "SecondID", "SecondDesc",
    "MarketHoursFlag", "OfficeHoursFlag"
])

time_df.write.mode("overwrite").parquet(f"{{output_path}}/DimTime")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Customer Dimension

# COMMAND ----------
# Generate customer dimension based on scale factor
num_customers = scale_factor * 50000  # Approximate based on TPC-DI spec

# Use Spark's rand() function instead of Python random for distributed generation
customer_ids = spark.range(1, num_customers + 1).toDF("id")

customers_df = customer_ids.select(
    col("id").alias("SK_CustomerID"),
    format_string("CUST%08d", col("id")).alias("CustomerID"),
    format_string("TaxID%09d", col("id")).alias("TaxID"),
    when(rand() < 0.6, "Individual")
     .when(rand() < 0.9, "Small Business")
     .otherwise("Large Business").alias("Status"),
    format_string("First%d", col("id")).alias("FirstName"),
    format_string("Last%d", col("id")).alias("LastName"),
    format_string("customer%d@email.com", col("id")).alias("Email1"),
    when(rand() < 0.5, "M").otherwise("F").alias("Gender"),
    when(rand() < 0.3, "S")
     .when(rand() < 0.6, "M")
     .when(rand() < 0.8, "D")
     .when(rand() < 0.9, "W")
     .otherwise("U").alias("MaritalStatus"),
    (floor(rand() * 1000) + 1).alias("AddressID"),
    (floor(rand() * 100) + 1).alias("PhoneID"),
    (floor(rand() * 100) + 1).alias("CreditRating"),
    (floor(rand() * 1000) + 1).alias("NetWorth"),
    when(rand() < 0.5, "Y").otherwise("N").alias("MarketingNameplate"),
    (floor(rand() * 10000) + 1).alias("Income"),
    lit("Y").alias("IsCurrent"),
    (floor(rand() * 10000) + 1).alias("BatchID"),
    date_add(lit("2000-01-01"), floor(rand() * 7300)).alias("EffectiveDate")
)

# Add additional required columns with default values
customers_df = customers_df.withColumn("MiddleInitial", lit(""))
customers_df = customers_df.withColumn("DOB", date_add(lit("1970-01-01"), floor(rand() * 18250)))
customers_df = customers_df.withColumn("AddressLine1", format_string("Address %d", col("AddressID")))
customers_df = customers_df.withColumn("AddressLine2", lit(""))
customers_df = customers_df.withColumn("PostalCode", format_string("%05d", floor(rand() * 99999)))
customers_df = customers_df.withColumn("City", format_string("City%d", floor(rand() * 1000)))
customers_df = customers_df.withColumn("StateProv", format_string("ST%d", floor(rand() * 50)))
customers_df = customers_df.withColumn("Country", lit("USA"))
customers_df = customers_df.withColumn("Phone1", format_string("555-%04d", floor(rand() * 9999)))
customers_df = customers_df.withColumn("Phone2", lit(""))
customers_df = customers_df.withColumn("Phone3", lit(""))
customers_df = customers_df.withColumn("Email2", lit(""))
customers_df = customers_df.withColumn("NationalTaxRateDesc", lit("Federal"))
customers_df = customers_df.withColumn("NationalTaxRate", rand() * 0.3)
customers_df = customers_df.withColumn("LocalTaxRateDesc", lit("State"))
customers_df = customers_df.withColumn("LocalTaxRate", rand() * 0.1)
customers_df = customers_df.withColumn("AgencyID", floor(rand() * 10) + 1)
customers_df = customers_df.withColumn("EndDate", lit(None).cast("date"))

# Write customer dimension
customers_df.write.mode("overwrite").parquet(f"{{output_path}}/DimCustomer")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Security Dimension

# COMMAND ----------
# Generate security dimension
num_securities = scale_factor * 5000

security_ids = spark.range(1, num_securities + 1).toDF("id")

securities_df = security_ids.select(
    col("id").alias("SK_SecurityID"),
    format_string("SYM%06d", col("id")).alias("Symbol"),
    format_string("Security %d", col("id")).alias("Name"),
    when(rand() < 0.7, "Common Stock")
     .when(rand() < 0.85, "Preferred Stock")
     .when(rand() < 0.95, "Bond")
     .otherwise("Option").alias("Status"),
    when(rand() < 0.4, "NYSE")
     .when(rand() < 0.7, "NASDAQ")
     .when(rand() < 0.9, "AMEX")
     .otherwise("OTC").alias("ExchangeID"),
    format_string("Issue%d", col("id")).alias("Issue"),
    (floor(rand() * 1000) + 1).alias("SK_CompanyID"),
    (floor(rand() * 10000000) + 1000000).alias("SharesOutstanding"),
    date_add(lit("2000-01-01"), floor(rand() * 7300)).alias("FirstTrade"),
    date_add(lit("2000-01-01"), floor(rand() * 7300)).alias("FirstTradeOnExchange"),
    (rand() * 5.0).alias("Dividend"),
    when(rand() < 0.9, "Y").otherwise("N").alias("IsCurrent"),
    (floor(rand() * 100) + 1).alias("BatchID"),
    date_add(lit("2000-01-01"), floor(rand() * 7300)).alias("EffectiveDate"),
    lit(None).cast("date").alias("EndDate")
)

securities_df.write.mode("overwrite").parquet(f"{{output_path}}/DimSecurity")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Generate Fact Tables

# COMMAND ----------
# MAGIC %md
# MAGIC ### Daily Market Fact

# COMMAND ----------
# Generate daily market fact table
num_days = 7300  # ~20 years
num_securities_per_day = min(scale_factor * 500, num_securities)

# Create date and security combinations
dates = spark.range(1, num_days + 1).toDF("SK_DateID")
securities_list = spark.range(1, num_securities_per_day + 1).toDF("SK_SecurityID")

# Cross join to get all combinations
daily_market_df = dates.crossJoin(securities_list).select(
    col("SK_DateID"),
    col("SK_SecurityID"),
    lit(930).alias("SK_TimeID"),  # 9:30 AM market open
    (rand() * 990 + 10).alias("ClosePrice"),
    (rand() * 990 + 10).alias("DayHigh"),
    (rand() * 990 + 10).alias("DayLow"),
    (floor(rand() * 999000) + 1000).alias("Volume"),
    (floor(rand() * 100) + 1).alias("BatchID")
)

daily_market_df.write.mode("overwrite").parquet(f"{{output_path}}/FactDailyMarket")

# COMMAND ----------
# MAGIC %md
# MAGIC ### Trade Fact

# COMMAND ----------
# Generate trade fact table
num_trades = scale_factor * 100000

trades_df = spark.range(1, num_trades + 1).toDF("TradeID").select(
    col("TradeID"),
    (floor(rand() * num_customers) + 1).alias("SK_CustomerID"),
    (floor(rand() * num_securities) + 1).alias("SK_SecurityID"),
    (floor(rand() * num_days) + 1).alias("SK_DateID"),
    (floor(rand() * 670) + 930).alias("SK_TimeID"),  # Between 9:30 AM and 4:00 PM
    when(rand() < 0.5, "Buy").otherwise("Sell").alias("TradeType"),
    (rand() * 990 + 10).alias("Quantity"),
    (rand() * 990 + 10).alias("BidPrice"),
    (rand() * 990 + 10).alias("AskPrice"),
    (floor(rand() * 100) + 1).alias("BatchID")
)

trades_df.write.mode("overwrite").parquet(f"{{output_path}}/FactTrade")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Summary

# COMMAND ----------
print(f"TPC-DI data generation complete!")
print(f"Scale Factor: {{scale_factor}}")
print(f"Output Path: {{output_path}}")
print(f"\\nGenerated tables:")
print(f"  - DimDate: {{date_df.count()}} rows")
print(f"  - DimTime: {{time_df.count()}} rows")
print(f"  - DimCustomer: {{customers_df.count()}} rows")
print(f"  - DimSecurity: {{securities_df.count()}} rows")
print(f"  - FactDailyMarket: {{daily_market_df.count()}} rows")
print(f"  - FactTrade: {{trades_df.count()}} rows")
"""
        
        # Create a temporary notebook file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(notebook_code)
            notebook_path = f.name
        
        print(f"Notebook code written to: {notebook_path}")
        print("\nTo use this code:")
        print("1. Copy the code above into a Databricks notebook")
        print("2. Run the notebook on your Databricks cluster")
        print(f"3. Data will be generated at: {output_path}")
        
        return notebook_path
    
    def create_tables(self, catalog: str = "hive_metastore", schema: str = "tpcdi"):
        """Create external tables pointing to the generated data"""
        print(f"Creating tables in {catalog}.{schema}...")
        
        # This would typically be done via SQL in a Databricks notebook
        sql_code = f"""
CREATE SCHEMA IF NOT EXISTS {catalog}.{schema};

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.DimDate
USING PARQUET
LOCATION 'dbfs:/tmp/tpcdi/DimDate';

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.DimTime
USING PARQUET
LOCATION 'dbfs:/tmp/tpcdi/DimTime';

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.DimCustomer
USING PARQUET
LOCATION 'dbfs:/tmp/tpcdi/DimCustomer';

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.DimSecurity
USING PARQUET
LOCATION 'dbfs:/tmp/tpcdi/DimSecurity';

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.FactDailyMarket
USING PARQUET
LOCATION 'dbfs:/tmp/tpcdi/FactDailyMarket';

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.FactTrade
USING PARQUET
LOCATION 'dbfs:/tmp/tpcdi/FactTrade';
"""
        print("\nSQL to create tables:")
        print(sql_code)
        return sql_code


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate TPC-DI data on Databricks")
    parser.add_argument("--workspace-url", required=True, help="Databricks workspace URL")
    parser.add_argument("--token", required=True, help="Databricks token")
    parser.add_argument("--scale-factor", type=int, default=1, help="Scale factor (default: 1)")
    parser.add_argument("--output-path", default="dbfs:/tmp/tpcdi", help="Output path")
    
    args = parser.parse_args()
    
    generator = TPCIDataGenerator(args.workspace_url, args.token)
    generator.generate_data_databricks(args.scale_factor, args.output_path)
