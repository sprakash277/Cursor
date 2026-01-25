"""
Silver Layer: Data cleansing, validation, and transformation
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, when, trim, upper, regexp_replace, to_date, coalesce
from pyspark.sql.types import StringType, TimestampType
from typing import Optional, Dict, List

from src.utils.performance_logger import PerformanceLogger
from src.layers.bronze_layer import BronzeLayer


class SilverLayer:
    """Silver layer for data cleansing and validation"""
    
    def __init__(self, spark: SparkSession, bronze_layer: BronzeLayer,
                 gcs_utils, silver_path: str, perf_logger: PerformanceLogger):
        """
        Initialize Silver layer
        
        Args:
            spark: SparkSession instance
            bronze_layer: BronzeLayer instance
            gcs_utils: GCSUtils instance
            silver_path: GCS path for silver layer storage
            perf_logger: PerformanceLogger instance
        """
        self.spark = spark
        self.bronze_layer = bronze_layer
        self.gcs_utils = gcs_utils
        self.silver_path = silver_path
        self.perf_logger = perf_logger
    
    def cleanse_data(self, df: DataFrame, table_name: str,
                    transformations: Optional[Dict] = None) -> DataFrame:
        """
        Cleanse and validate data from Bronze layer
        
        Args:
            df: Input DataFrame from Bronze layer
            table_name: Name of the table
            transformations: Optional dictionary of column transformations
            
        Returns:
            Cleaned DataFrame
        """
        stage_name = f"Silver_Cleanse_{table_name}"
        self.perf_logger.log_stage_start(stage_name, {"table": table_name})
        
        try:
            # Apply standard cleansing transformations
            cleaned_df = df
            
            # Trim string columns
            for field in df.schema.fields:
                if field.dataType == StringType():
                    cleaned_df = cleaned_df.withColumn(
                        field.name,
                        trim(col(field.name))
                    )
            
            # Apply custom transformations if provided
            if transformations:
                for column, transform_func in transformations.items():
                    if column in cleaned_df.columns:
                        cleaned_df = cleaned_df.withColumn(column, transform_func(col(column)))
            
            # Remove null rows (optional - can be configured per table)
            # cleaned_df = cleaned_df.na.drop()
            
            # Log results
            record_count = cleaned_df.count()
            self.perf_logger.log_dataframe_info(stage_name, cleaned_df)
            
            # Write to Silver layer
            silver_output_path = f"gs://{self.gcs_utils.bucket_name}/{self.silver_path}/{table_name}"
            cleaned_df.write.mode("overwrite").format("parquet").save(silver_output_path)
            
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=record_count,
                additional_info={"output_path": silver_output_path}
            )
            
            return cleaned_df
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def validate_data(self, df: DataFrame, table_name: str,
                     validation_rules: Optional[Dict] = None) -> DataFrame:
        """
        Validate data according to business rules
        
        Args:
            df: Input DataFrame
            table_name: Name of the table
            validation_rules: Optional dictionary of validation rules
            
        Returns:
            Validated DataFrame
        """
        stage_name = f"Silver_Validate_{table_name}"
        self.perf_logger.log_stage_start(stage_name, {"table": table_name})
        
        try:
            validated_df = df
            
            # Apply validation rules if provided
            if validation_rules:
                for column, rule_func in validation_rules.items():
                    if column in validated_df.columns:
                        validated_df = validated_df.filter(rule_func(col(column)))
            
            record_count = validated_df.count()
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=record_count
            )
            
            return validated_df
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def transform_data(self, df: DataFrame, table_name: str,
                      transformations: Optional[List] = None) -> DataFrame:
        """
        Apply business transformations to data
        
        Args:
            df: Input DataFrame
            table_name: Name of the table
            transformations: List of transformation functions
            
        Returns:
            Transformed DataFrame
        """
        stage_name = f"Silver_Transform_{table_name}"
        self.perf_logger.log_stage_start(stage_name, {"table": table_name})
        
        try:
            transformed_df = df
            
            # Apply transformations
            if transformations:
                for transform_func in transformations:
                    transformed_df = transform_func(transformed_df)
            
            record_count = transformed_df.count()
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=record_count
            )
            
            return transformed_df
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def process_table(self, table_name: str, transformations: Optional[Dict] = None,
                     validation_rules: Optional[Dict] = None) -> DataFrame:
        """
        Complete Silver layer processing for a table
        
        Args:
            table_name: Name of the table
            transformations: Optional cleansing transformations
            validation_rules: Optional validation rules
            
        Returns:
            Processed DataFrame
        """
        # Load from Bronze
        df = self.bronze_layer.load_from_bronze(table_name)
        
        # Cleanse
        df = self.cleanse_data(df, table_name, transformations)
        
        # Validate
        if validation_rules:
            df = self.validate_data(df, table_name, validation_rules)
        
        return df
    
    def load_from_silver(self, table_name: str) -> DataFrame:
        """
        Load data from Silver layer
        
        Args:
            table_name: Name of the table/file in silver layer
            
        Returns:
            DataFrame from silver layer
        """
        silver_path = f"gs://{self.gcs_utils.bucket_name}/{self.silver_path}/{table_name}"
        return self.spark.read.parquet(silver_path)
