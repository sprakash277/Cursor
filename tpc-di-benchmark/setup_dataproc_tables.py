"""
Setup TPC-DI tables in Dataproc
"""

from pyspark.sql import SparkSession
import yaml


def create_tables(spark: SparkSession, gcs_path: str, schema: str = "tpcdi"):
    """
    Create external tables in Dataproc pointing to GCS data
    
    Args:
        spark: SparkSession
        gcs_path: GCS path to data (e.g., gs://bucket/tpcdi)
        schema: Schema name (default: tpcdi)
    """
    print(f"Creating tables in schema {schema}...")
    
    # Create schema
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    print(f"✓ Created schema: {schema}")
    
    # Table definitions
    tables = {
        "DimDate": "DimDate",
        "DimTime": "DimTime",
        "DimCustomer": "DimCustomer",
        "DimSecurity": "DimSecurity",
        "FactDailyMarket": "FactDailyMarket",
        "FactTrade": "FactTrade"
    }
    
    for table_name, data_path in tables.items():
        location = f"{gcs_path}/{data_path}"
        
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {schema}.{table_name}
        USING PARQUET
        LOCATION '{location}'
        """
        
        try:
            spark.sql(create_sql)
            print(f"✓ Created table: {schema}.{table_name}")
            
            # Verify table
            count = spark.sql(f"SELECT COUNT(*) as cnt FROM {schema}.{table_name}").collect()[0]['cnt']
            print(f"  Rows: {count:,}")
            
        except Exception as e:
            print(f"✗ Error creating table {table_name}: {str(e)}")
    
    print("\n✓ Table setup complete!")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup TPC-DI tables in Dataproc")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--gcs-path", help="GCS path to data (overrides config)")
    parser.add_argument("--schema", default="tpcdi", help="Schema name")
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    gcs_path = args.gcs_path or f"gs://{config['dataproc']['bucket_name']}/tpcdi"
    
    # Initialize Spark
    spark = SparkSession.builder \
        .appName("TPC-DI-Table-Setup") \
        .getOrCreate()
    
    try:
        create_tables(spark, gcs_path, args.schema)
    finally:
        spark.stop()
