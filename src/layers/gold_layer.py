"""
Gold Layer: Business-ready aggregated and enriched data
"""
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import sum, avg, count, max, min, col
from typing import Optional, Dict, List

from src.utils.performance_logger import PerformanceLogger
from src.layers.silver_layer import SilverLayer


class GoldLayer:
    """Gold layer for business-ready aggregated data"""
    
    def __init__(self, spark: SparkSession, silver_layer: SilverLayer,
                 gcs_utils, gold_path: str, perf_logger: PerformanceLogger):
        """
        Initialize Gold layer
        
        Args:
            spark: SparkSession instance
            silver_layer: SilverLayer instance
            gcs_utils: GCSUtils instance
            gold_path: GCS path for gold layer storage
            perf_logger: PerformanceLogger instance
        """
        self.spark = spark
        self.silver_layer = silver_layer
        self.gcs_utils = gcs_utils
        self.gold_path = gold_path
        self.perf_logger = perf_logger
    
    def aggregate_data(self, df: DataFrame, table_name: str,
                      group_by_columns: List[str],
                      aggregations: Optional[Dict] = None) -> DataFrame:
        """
        Aggregate data for business reporting
        
        Args:
            df: Input DataFrame from Silver layer
            table_name: Name of the table
            group_by_columns: Columns to group by
            aggregations: Dictionary of column -> aggregation function mappings
            
        Returns:
            Aggregated DataFrame
        """
        stage_name = f"Gold_Aggregate_{table_name}"
        self.perf_logger.log_stage_start(
            stage_name,
            {"table": table_name, "group_by": group_by_columns}
        )
        
        try:
            # Default aggregations if not provided
            if not aggregations:
                # Get numeric columns for default aggregations
                numeric_cols = [field.name for field in df.schema.fields 
                              if field.dataType.simpleString() in ['int', 'bigint', 'double', 'float', 'decimal']]
                aggregations = {col_name: sum for col_name in numeric_cols}
            
            # Build aggregation expressions
            agg_exprs = []
            for col_name, agg_func in aggregations.items():
                if col_name in df.columns:
                    agg_exprs.append(agg_func(col(col_name)).alias(f"{agg_func.__name__}_{col_name}"))
            
            # Perform aggregation
            if agg_exprs:
                aggregated_df = df.groupBy(*group_by_columns).agg(*agg_exprs)
            else:
                aggregated_df = df.groupBy(*group_by_columns).agg(count("*").alias("count"))
            
            record_count = aggregated_df.count()
            self.perf_logger.log_dataframe_info(stage_name, aggregated_df)
            
            # Write to Gold layer
            gold_output_path = f"gs://{self.gcs_utils.bucket_name}/{self.gold_path}/{table_name}"
            aggregated_df.write.mode("overwrite").format("parquet").save(gold_output_path)
            
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=record_count,
                additional_info={"output_path": gold_output_path}
            )
            
            return aggregated_df
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def join_tables(self, tables: Dict[str, DataFrame], join_conditions: Dict[str, str],
                   table_name: str, join_type: str = "inner") -> DataFrame:
        """
        Join multiple tables from Silver layer
        
        Args:
            tables: Dictionary of table names to DataFrames
            join_conditions: Dictionary of join conditions
            table_name: Name for the resulting joined table
            join_type: Type of join (inner, left, right, outer)
            
        Returns:
            Joined DataFrame
        """
        stage_name = f"Gold_Join_{table_name}"
        self.perf_logger.log_stage_start(stage_name, {"tables": list(tables.keys())})
        
        try:
            if len(tables) < 2:
                raise ValueError("At least 2 tables required for join")
            
            table_list = list(tables.items())
            result_df = table_list[0][1]
            
            for i in range(1, len(table_list)):
                next_table_name, next_df = table_list[i]
                join_key = join_conditions.get(f"{table_list[i-1][0]}_{next_table_name}")
                
                if not join_key:
                    raise ValueError(f"Join condition missing for {table_list[i-1][0]} and {next_table_name}")
                
                result_df = result_df.join(next_df, join_key, join_type)
            
            record_count = result_df.count()
            self.perf_logger.log_dataframe_info(stage_name, result_df)
            
            # Write to Gold layer
            gold_output_path = f"gs://{self.gcs_utils.bucket_name}/{self.gold_path}/{table_name}"
            result_df.write.mode("overwrite").format("parquet").save(gold_output_path)
            
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=record_count,
                additional_info={"output_path": gold_output_path}
            )
            
            return result_df
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def enrich_data(self, df: DataFrame, table_name: str,
                   enrichment_func: callable) -> DataFrame:
        """
        Enrich data with additional business logic
        
        Args:
            df: Input DataFrame
            table_name: Name of the table
            enrichment_func: Function to apply enrichment logic
            
        Returns:
            Enriched DataFrame
        """
        stage_name = f"Gold_Enrich_{table_name}"
        self.perf_logger.log_stage_start(stage_name, {"table": table_name})
        
        try:
            enriched_df = enrichment_func(df)
            
            record_count = enriched_df.count()
            self.perf_logger.log_dataframe_info(stage_name, enriched_df)
            
            # Write to Gold layer
            gold_output_path = f"gs://{self.gcs_utils.bucket_name}/{self.gold_path}/{table_name}"
            enriched_df.write.mode("overwrite").format("parquet").save(gold_output_path)
            
            self.perf_logger.log_stage_end(
                stage_name,
                record_count=record_count,
                additional_info={"output_path": gold_output_path}
            )
            
            return enriched_df
            
        except Exception as e:
            self.perf_logger.log_stage_end(
                stage_name,
                additional_info={"error": str(e)}
            )
            raise
    
    def load_from_gold(self, table_name: str) -> DataFrame:
        """
        Load data from Gold layer
        
        Args:
            table_name: Name of the table/file in gold layer
            
        Returns:
            DataFrame from gold layer
        """
        gold_path = f"gs://{self.gcs_utils.bucket_name}/{self.gold_path}/{table_name}"
        return self.spark.read.parquet(gold_path)
