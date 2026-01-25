"""
Main orchestration script for TPC-DI benchmark on Google Cloud Dataproc
"""
import os
import sys
from pyspark.sql import SparkSession
import yaml
from typing import Dict

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.gcs_utils import GCSUtils
from src.utils.performance_logger import PerformanceLogger
from src.utils.platform_detector import PlatformDetector
from src.layers.bronze_layer import BronzeLayer
from src.layers.silver_layer import SilverLayer
from src.layers.gold_layer import GoldLayer
from src.tpc_di.load_manager import TPC_DI_LoadManager


def create_spark_session(project_id: str, app_name: str = "TPC-DI-Benchmark", platform: str = None) -> SparkSession:
    """
    Create and configure Spark session for Dataproc or Databricks
    
    Args:
        project_id: GCP project ID
        app_name: Spark application name
        platform: Platform name (auto-detected if None)
        
    Returns:
        Configured SparkSession
    """
    # Detect platform if not provided
    if platform is None:
        platform = PlatformDetector.detect()
    
    # Get platform-specific config
    platform_config = PlatformDetector.get_spark_config(platform)
    
    # Build Spark session
    builder = SparkSession.builder.appName(app_name)
    
    # Apply platform-specific configurations
    for key, value in platform_config.items():
        builder = builder.config(key, value)
    
    spark = builder.getOrCreate()
    
    # Configure for GCS
    GCSUtils.configure_spark_for_gcs(spark, project_id, platform)
    
    # Log platform info
    print(f"Running on platform: {platform}")
    print(f"Spark version: {spark.version}")
    
    return spark


def load_config(config_path: str = "config/config.yaml") -> Dict:
    """
    Load configuration from YAML file
    
    Args:
        config_path: Path to config file
        
    Returns:
        Configuration dictionary
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def main(load_type: str = "historical", platform: str = None):
    """
    Main orchestration function
    
    Args:
        load_type: Type of load - "historical" or "incremental"
        platform: Platform name (auto-detected if None)
    """
    # Load configuration
    config = load_config()
    
    # Detect platform if not provided
    if platform is None:
        platform = PlatformDetector.detect()
    
    # Get project ID based on platform
    if platform == "databricks":
        project_id = config.get("databricks", {}).get("project_id") or config.get("dataproc", {}).get("project_id")
    else:
        project_id = config.get("dataproc", {}).get("project_id")
    
    if not project_id:
        raise ValueError("Project ID not found in configuration")
    
    # Initialize Spark
    spark = create_spark_session(
        project_id=project_id,
        app_name=f"TPC-DI-{load_type.title()}-Load",
        platform=platform
    )
    
    # Initialize utilities
    gcs_utils = GCSUtils(
        bucket_name=config["gcs"]["bucket_name"],
        project_id=config["dataproc"]["project_id"]
    )
    
    perf_logger = PerformanceLogger(
        log_path=config["logging"]["performance_log_path"],
        log_level=config["logging"]["level"]
    )
    
    # Initialize layers
    bronze_layer = BronzeLayer(
        spark=spark,
        gcs_utils=gcs_utils,
        bronze_path=config["gcs"]["bronze_path"],
        perf_logger=perf_logger
    )
    
    silver_layer = SilverLayer(
        spark=spark,
        bronze_layer=bronze_layer,
        gcs_utils=gcs_utils,
        silver_path=config["gcs"]["silver_path"],
        perf_logger=perf_logger
    )
    
    gold_layer = GoldLayer(
        spark=spark,
        silver_layer=silver_layer,
        gcs_utils=gcs_utils,
        gold_path=config["gcs"]["gold_path"],
        perf_logger=perf_logger
    )
    
    # Initialize Load Manager
    load_manager = TPC_DI_LoadManager(
        spark=spark,
        gcs_utils=gcs_utils,
        bronze_layer=bronze_layer,
        silver_layer=silver_layer,
        gold_layer=gold_layer,
        perf_logger=perf_logger,
        checkpoint_path=config["tpc_di"]["checkpoint_path"]
    )
    
    # Define table configurations
    # This is a template - customize based on your TPC-DI data structure
    table_configs = {
        "DimDate": {
            "file_name": "Date.txt",
            "format": "csv",
            "options": {"header": "true", "delimiter": "|"}
        },
        "DimTime": {
            "file_name": "Time.txt",
            "format": "csv",
            "options": {"header": "true", "delimiter": "|"}
        },
        # Add more table configurations as needed
        # Example with transformations:
        # "FactSales": {
        #     "file_name": "Sales.txt",
        #     "format": "csv",
        #     "timestamp_column": "UpdateDate",
        #     "transformations": {
        #         "Amount": lambda x: x.cast("decimal(18,2)")
        #     },
        #     "gold_config": {
        #         "aggregate": {
        #             "group_by": ["DateKey", "ProductKey"],
        #             "aggregations": {"Amount": sum, "Quantity": sum}
        #         }
        #     }
        # }
    }
    
    try:
        # Execute load
        if load_type.lower() == "historical":
            perf_logger.logger.info("Starting Historical Load...")
            results = load_manager.historical_load(
                table_configs=table_configs,
                raw_data_path=config["gcs"]["raw_data_path"]
            )
        elif load_type.lower() == "incremental":
            perf_logger.logger.info("Starting Incremental Load...")
            results = load_manager.incremental_load(
                table_configs=table_configs,
                raw_data_path=config["gcs"]["raw_data_path"]
            )
        else:
            raise ValueError(f"Invalid load_type: {load_type}. Must be 'historical' or 'incremental'")
        
        # Print performance summary
        perf_logger.print_summary()
        
        perf_logger.logger.info(f"{load_type.title()} load completed successfully!")
        
    except Exception as e:
        perf_logger.logger.error(f"Load failed: {str(e)}")
        raise
    
    finally:
        spark.stop()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="TPC-DI Benchmark on Dataproc")
    parser.add_argument(
        "--load-type",
        type=str,
        default="historical",
        choices=["historical", "incremental"],
        help="Type of load to perform"
    )
    parser.add_argument(
        "--platform",
        type=str,
        default=None,
        choices=["dataproc", "databricks", "local"],
        help="Platform to run on (auto-detected if not specified)"
    )
    
    args = parser.parse_args()
    main(load_type=args.load_type, platform=args.platform)
