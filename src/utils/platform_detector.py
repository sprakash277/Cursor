"""
Platform detection utility for Dataproc vs Databricks
"""
import os
from typing import Optional, Literal


Platform = Literal["dataproc", "databricks", "local"]


class PlatformDetector:
    """Detect the execution platform (Dataproc, Databricks, or Local)"""
    
    @staticmethod
    def detect() -> Platform:
        """
        Detect the current execution platform
        
        Returns:
            Platform name: "dataproc", "databricks", or "local"
        """
        # Check for Databricks
        if PlatformDetector._is_databricks():
            return "databricks"
        
        # Check for Dataproc
        if PlatformDetector._is_dataproc():
            return "dataproc"
        
        # Default to local
        return "local"
    
    @staticmethod
    def _is_databricks() -> bool:
        """Check if running on Databricks"""
        # Databricks sets these environment variables
        databricks_indicators = [
            "DATABRICKS_RUNTIME_VERSION",
            "SPARK_CONF_DIR",
            "DATABRICKS_ROOT_VIRTUALENV_ENV"
        ]
        
        for indicator in databricks_indicators:
            if os.getenv(indicator):
                return True
        
        # Check for Databricks-specific paths
        databricks_paths = [
            "/databricks",
            "/dbfs",
            "/Volumes"
        ]
        
        for path in databricks_paths:
            if os.path.exists(path):
                return True
        
        return False
    
    @staticmethod
    def _is_dataproc() -> bool:
        """Check if running on Dataproc"""
        # Dataproc sets these environment variables
        dataproc_indicators = [
            "SPARK_HOME",
            "HADOOP_HOME"
        ]
        
        # Check for Dataproc-specific metadata
        try:
            import requests
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/attributes/dataproc-cluster-name"
            headers = {"Metadata-Flavor": "Google"}
            response = requests.get(metadata_url, headers=headers, timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        
        # Check environment variables
        for indicator in dataproc_indicators:
            if os.getenv(indicator):
                # Additional check: if running on GCP
                if os.getenv("GOOGLE_CLOUD_PROJECT"):
                    return True
        
        return False
    
    @staticmethod
    def get_spark_config(platform: Optional[Platform] = None) -> dict:
        """
        Get platform-specific Spark configuration
        
        Args:
            platform: Platform name (auto-detected if None)
            
        Returns:
            Dictionary of Spark configuration options
        """
        if platform is None:
            platform = PlatformDetector.detect()
        
        config = {
            "spark.sql.adaptive.enabled": "true",
            "spark.sql.adaptive.coalescePartitions.enabled": "true",
            "spark.serializer": "org.apache.spark.serializer.KryoSerializer"
        }
        
        if platform == "databricks":
            # Databricks-specific optimizations
            config.update({
                "spark.databricks.io.cache.enabled": "true",
                "spark.databricks.delta.optimizeWrite.enabled": "true",
                "spark.databricks.delta.autoCompact.enabled": "true"
            })
        elif platform == "dataproc":
            # Dataproc-specific optimizations
            config.update({
                "spark.sql.adaptive.skewJoin.enabled": "true",
                "spark.sql.adaptive.localShuffleReader.enabled": "true"
            })
        
        return config
