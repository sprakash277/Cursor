"""
TPC-DI Load Manager: Handles Historical and Incremental loads per TPC-DI specifications
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, max as spark_max, lit
from typing import Dict, List, Optional
from datetime import datetime
import os

from src.utils.performance_logger import PerformanceLogger
from src.utils.gcs_utils import GCSUtils
from src.layers.bronze_layer import BronzeLayer
from src.layers.silver_layer import SilverLayer
from src.layers.gold_layer import GoldLayer


class TPC_DI_LoadManager:
    """
    Manages Historical and Incremental loads according to TPC-DI specifications
    
    TPC-DI Spec:
    - Historical Load: Initial load of all historical data
    - Incremental Load: Load only new/changed data since last load
    """
    
    def __init__(self, spark: SparkSession, gcs_utils: GCSUtils,
                 bronze_layer: BronzeLayer, silver_layer: SilverLayer,
                 gold_layer: GoldLayer, perf_logger: PerformanceLogger,
                 checkpoint_path: str):
        """
        Initialize TPC-DI Load Manager
        
        Args:
            spark: SparkSession instance
            gcs_utils: GCSUtils instance
            bronze_layer: BronzeLayer instance
            silver_layer: SilverLayer instance
            gold_layer: GoldLayer instance
            perf_logger: PerformanceLogger instance
            checkpoint_path: GCS path for storing load checkpoints
        """
        self.spark = spark
        self.gcs_utils = gcs_utils
        self.bronze_layer = bronze_layer
        self.silver_layer = silver_layer
        self.gold_layer = gold_layer
        self.perf_logger = perf_logger
        self.checkpoint_path = checkpoint_path
    
    def get_last_load_timestamp(self, table_name: str) -> Optional[datetime]:
        """
        Get the timestamp of the last successful load for a table
        
        Args:
            table_name: Name of the table
            
        Returns:
            Last load timestamp or None if no previous load
        """
        checkpoint_file = f"{self.checkpoint_path}/{table_name}_last_load.txt"
        
        if self.gcs_utils.file_exists(checkpoint_file):
            blob = self.gcs_utils.bucket.blob(checkpoint_file)
            timestamp_str = blob.download_as_text()
            return datetime.fromisoformat(timestamp_str.strip())
        
        return None
    
    def save_load_timestamp(self, table_name: str, timestamp: datetime):
        """
        Save the timestamp of a successful load
        
        Args:
            table_name: Name of the table
            timestamp: Timestamp to save
        """
        checkpoint_file = f"{self.checkpoint_path}/{table_name}_last_load.txt"
        blob = self.gcs_utils.bucket.blob(checkpoint_file)
        blob.upload_from_string(timestamp.isoformat())
    
    def historical_load(self, table_configs: Dict[str, Dict],
                       raw_data_path: str) -> Dict[str, DataFrame]:
        """
        Perform Historical Load: Process all historical data
        
        According to TPC-DI specs, Historical Load:
        - Processes all available historical data
        - No filtering by date/timestamp
        - Full processing through Bronze -> Silver -> Gold
        
        Args:
            table_configs: Dictionary of table configurations
                          Each config should have: file_name, schema (optional), format (optional)
            raw_data_path: GCS path to raw data files
            
        Returns:
            Dictionary of processed DataFrames
        """
        stage_name = "Historical_Load"
        self.perf_logger.log_stage_start(
            stage_name,
            {"tables": list(table_configs.keys()), "load_type": "Historical"}
        )
        
        results = {}
        
        try:
            # Process each table through the layers
            for table_name, config in table_configs.items():
                table_stage = f"{stage_name}_{table_name}"
                self.perf_logger.log_stage_start(table_stage)
                
                # Bronze: Ingest raw data
                file_name = config.get("file_name", table_name)
                file_format = config.get("format", "csv")
                schema = config.get("schema")
                
                bronze_df = self.bronze_layer.ingest_raw_file(
                    file_name=file_name,
                    raw_data_path=raw_data_path,
                    schema=schema,
                    file_format=file_format,
                    options=config.get("options")
                )
                
                # Silver: Cleanse and validate
                silver_df = self.silver_layer.process_table(
                    table_name=table_name,
                    transformations=config.get("transformations"),
                    validation_rules=config.get("validation_rules")
                )
                
                # Gold: Aggregate/enrich (if configured)
                if config.get("gold_config"):
                    gold_config = config["gold_config"]
                    if gold_config.get("aggregate"):
                        gold_df = self.gold_layer.aggregate_data(
                            silver_df,
                            table_name=table_name,
                            group_by_columns=gold_config["aggregate"].get("group_by", []),
                            aggregations=gold_config["aggregate"].get("aggregations")
                        )
                    elif gold_config.get("enrich"):
                        gold_df = self.gold_layer.enrich_data(
                            silver_df,
                            table_name=table_name,
                            enrichment_func=gold_config["enrich"]
                        )
                    else:
                        gold_df = silver_df
                else:
                    gold_df = silver_df
                
                results[table_name] = gold_df
                
                # Save checkpoint
                self.save_load_timestamp(table_name, datetime.now())
                
                self.perf_logger.log_stage_end(table_stage)
            
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=sum([df.count() for df in results.values()]),
                additional_info={"tables_processed": len(results)}
            )
            
            return results
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def incremental_load(self, table_configs: Dict[str, Dict],
                        raw_data_path: str,
                        timestamp_column: str = "UpdateDate") -> Dict[str, DataFrame]:
        """
        Perform Incremental Load: Process only new/changed data
        
        According to TPC-DI specs, Incremental Load:
        - Processes only data that has changed since last load
        - Filters by timestamp/date column
        - Merges with existing data in Silver/Gold layers
        
        Args:
            table_configs: Dictionary of table configurations
            raw_data_path: GCS path to raw data files
            timestamp_column: Column name to use for filtering incremental data
            
        Returns:
            Dictionary of processed DataFrames
        """
        stage_name = "Incremental_Load"
        self.perf_logger.log_stage_start(
            stage_name,
            {"tables": list(table_configs.keys()), "load_type": "Incremental"}
        )
        
        results = {}
        
        try:
            for table_name, config in table_configs.items():
                table_stage = f"{stage_name}_{table_name}"
                self.perf_logger.log_stage_start(table_stage)
                
                # Get last load timestamp
                last_timestamp = self.get_last_load_timestamp(table_name)
                
                if last_timestamp is None:
                    self.perf_logger.logger.warning(
                        f"No previous load found for {table_name}. "
                        f"Performing full load instead."
                    )
                    # Fall back to historical load for this table
                    file_name = config.get("file_name", table_name)
                    file_format = config.get("format", "csv")
                    schema = config.get("schema")
                    
                    bronze_df = self.bronze_layer.ingest_raw_file(
                        file_name=file_name,
                        raw_data_path=raw_data_path,
                        schema=schema,
                        file_format=file_format,
                        options=config.get("options")
                    )
                else:
                    # Bronze: Ingest only new data
                    file_name = config.get("file_name", table_name)
                    file_format = config.get("format", "csv")
                    schema = config.get("schema")
                    
                    # Read raw data
                    gcs_path = f"gs://{self.gcs_utils.bucket_name}/{raw_data_path}/{file_name}"
                    reader = self.spark.read.format(file_format)
                    
                    read_options = config.get("options", {})
                    if file_format.lower() == "csv":
                        read_options.setdefault("header", "true")
                        read_options.setdefault("inferSchema", "true")
                    
                    for key, value in read_options.items():
                        reader = reader.option(key, value)
                    
                    if schema:
                        raw_df = reader.schema(schema).load(gcs_path)
                    else:
                        raw_df = reader.load(gcs_path)
                    
                    # Filter for incremental data
                    timestamp_col = config.get("timestamp_column", timestamp_column)
                    if timestamp_col in raw_df.columns:
                        incremental_df = raw_df.filter(
                            col(timestamp_col) > lit(last_timestamp)
                        )
                    else:
                        # If no timestamp column, read all data (fallback)
                        self.perf_logger.logger.warning(
                            f"Timestamp column '{timestamp_col}' not found in {table_name}. "
                            f"Loading all data."
                        )
                        incremental_df = raw_df
                    
                    # Write incremental data to Bronze
                    bronze_output_path = (
                        f"gs://{self.gcs_utils.bucket_name}/"
                        f"{self.bronze_layer.bronze_path}/{table_name}_incremental"
                    )
                    incremental_df.write.mode("overwrite").format("parquet").save(bronze_output_path)
                    
                    # Merge with existing Bronze data
                    try:
                        existing_bronze = self.bronze_layer.load_from_bronze(table_name)
                        bronze_df = existing_bronze.union(incremental_df)
                    except:
                        # If no existing data, use incremental only
                        bronze_df = incremental_df
                    
                    # Write merged Bronze data
                    bronze_final_path = (
                        f"gs://{self.gcs_utils.bucket_name}/"
                        f"{self.bronze_layer.bronze_path}/{table_name}"
                    )
                    bronze_df.write.mode("overwrite").format("parquet").save(bronze_final_path)
                
                # Silver: Process (will handle deduplication if needed)
                silver_df = self.silver_layer.process_table(
                    table_name=table_name,
                    transformations=config.get("transformations"),
                    validation_rules=config.get("validation_rules")
                )
                
                # Gold: Update aggregations/enrichments
                if config.get("gold_config"):
                    gold_config = config["gold_config"]
                    if gold_config.get("aggregate"):
                        # For incremental, we might need to recalculate from full Silver data
                        gold_df = self.gold_layer.aggregate_data(
                            silver_df,
                            table_name=table_name,
                            group_by_columns=gold_config["aggregate"].get("group_by", []),
                            aggregations=gold_config["aggregate"].get("aggregations")
                        )
                    elif gold_config.get("enrich"):
                        gold_df = self.gold_layer.enrich_data(
                            silver_df,
                            table_name=table_name,
                            enrichment_func=gold_config["enrich"]
                        )
                    else:
                        gold_df = silver_df
                else:
                    gold_df = silver_df
                
                results[table_name] = gold_df
                
                # Save checkpoint
                self.save_load_timestamp(table_name, datetime.now())
                
                self.perf_logger.log_stage_end(table_stage)
            
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=sum([df.count() for df in results.values()]),
                additional_info={"tables_processed": len(results)}
            )
            
            return results
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
