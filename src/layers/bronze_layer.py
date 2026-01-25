"""
Bronze Layer: Raw data ingestion from GCS
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.types import StructType
from typing import Optional, Dict
import os

from src.utils.performance_logger import PerformanceLogger
from src.utils.gcs_utils import GCSUtils


class BronzeLayer:
    """Bronze layer for raw data ingestion"""
    
    def __init__(self, spark: SparkSession, gcs_utils: GCSUtils, 
                 bronze_path: str, perf_logger: PerformanceLogger):
        """
        Initialize Bronze layer
        
        Args:
            spark: SparkSession instance
            gcs_utils: GCSUtils instance
            bronze_path: GCS path for bronze layer storage
            perf_logger: PerformanceLogger instance
        """
        self.spark = spark
        self.gcs_utils = gcs_utils
        self.bronze_path = bronze_path
        self.perf_logger = perf_logger
    
    def ingest_raw_file(self, file_name: str, raw_data_path: str, 
                       schema: Optional[StructType] = None,
                       file_format: str = "csv",
                       options: Optional[Dict] = None) -> DataFrame:
        """
        Ingest raw file from GCS into Bronze layer
        
        Args:
            file_name: Name of the file to ingest
            raw_data_path: GCS path to raw data
            schema: Optional schema for the data
            file_format: File format (csv, parquet, json, etc.)
            options: Additional options for reading the file
            
        Returns:
            DataFrame containing the raw data
        """
        stage_name = f"Bronze_Ingest_{file_name}"
        self.perf_logger.log_stage_start(
            stage_name,
            {"file": file_name, "format": file_format}
        )
        
        try:
            # Construct full GCS path
            gcs_path = f"gs://{self.gcs_utils.bucket_name}/{raw_data_path}/{file_name}"
            
            # Read options
            read_options = options or {}
            if file_format.lower() == "csv":
                read_options.setdefault("header", "true")
                read_options.setdefault("inferSchema", "true")
            
            # Read data
            reader = self.spark.read.format(file_format)
            for key, value in read_options.items():
                reader = reader.option(key, value)
            
            if schema:
                df = reader.schema(schema).load(gcs_path)
            else:
                df = reader.load(gcs_path)
            
            # Log DataFrame info
            record_count = df.count()
            self.perf_logger.log_dataframe_info(stage_name, df)
            
            # Write to Bronze layer (Parquet format for efficiency)
            bronze_output_path = f"gs://{self.gcs_utils.bucket_name}/{self.bronze_path}/{file_name}"
            df.write.mode("overwrite").format("parquet").save(bronze_output_path)
            
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=record_count,
                additional_info={"output_path": bronze_output_path}
            )
            
            return df
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def load_from_bronze(self, table_name: str) -> DataFrame:
        """
        Load data from Bronze layer
        
        Args:
            table_name: Name of the table/file in bronze layer
            
        Returns:
            DataFrame from bronze layer
        """
        bronze_path = f"gs://{self.gcs_utils.bucket_name}/{self.bronze_path}/{table_name}"
        return self.spark.read.parquet(bronze_path)
    
    def ingest_multiple_files(self, file_list: list, raw_data_path: str,
                             schema_map: Optional[Dict[str, StructType]] = None,
                             file_format: str = "csv") -> Dict[str, DataFrame]:
        """
        Ingest multiple raw files
        
        Args:
            file_list: List of file names to ingest
            raw_data_path: GCS path to raw data
            schema_map: Optional mapping of file names to schemas
            file_format: File format
            
        Returns:
            Dictionary mapping file names to DataFrames
        """
        results = {}
        for file_name in file_list:
            schema = schema_map.get(file_name) if schema_map else None
            df = self.ingest_raw_file(file_name, raw_data_path, schema, file_format)
            results[file_name] = df
        return results
