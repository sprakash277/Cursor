"""
GCS utility functions for connecting to Google Cloud Storage
"""
from google.cloud import storage
from pyspark.sql import SparkSession
import os
from typing import Optional

from src.utils.platform_detector import PlatformDetector


class GCSUtils:
    """Utility class for GCS operations"""
    
    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize GCS utilities
        
        Args:
            bucket_name: Name of the GCS bucket
            project_id: GCP project ID (optional, can be inferred from environment)
        """
        self.bucket_name = bucket_name
        self.project_id = project_id
        self.client = storage.Client(project=project_id) if project_id else storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def list_files(self, prefix: str) -> list:
        """
        List all files in GCS bucket with given prefix
        
        Args:
            prefix: Path prefix to filter files
            
        Returns:
            List of blob names
        """
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
    
    def file_exists(self, file_path: str) -> bool:
        """
        Check if a file exists in GCS bucket
        
        Args:
            file_path: Path to file in bucket
            
        Returns:
            True if file exists, False otherwise
        """
        blob = self.bucket.blob(file_path)
        return blob.exists()
    
    def get_file_size(self, file_path: str) -> int:
        """
        Get file size in bytes
        
        Args:
            file_path: Path to file in bucket
            
        Returns:
            File size in bytes
        """
        blob = self.bucket.blob(file_path)
        blob.reload()
        return blob.size
    
    @staticmethod
    def configure_spark_for_gcs(spark: SparkSession, project_id: str, platform: Optional[str] = None):
        """
        Configure Spark session for GCS access
        
        Args:
            spark: SparkSession instance
            project_id: GCP project ID
            platform: Platform name (auto-detected if None)
        """
        if platform is None:
            platform = PlatformDetector.detect()
        
        if platform == "databricks":
            # Databricks has built-in GCS support via gs:// protocol
            # Just set the project ID if needed
            spark.conf.set("fs.gs.project.id", project_id)
            
            # Use service account key if provided
            service_account_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if service_account_key:
                spark.conf.set("fs.gs.auth.service.account.json.keyfile", service_account_key)
            else:
                # Databricks can use cluster service account or user credentials
                # Check if using cluster service account
                cluster_service_account = os.getenv("DATABRICKS_CLUSTER_SERVICE_ACCOUNT")
                if cluster_service_account:
                    spark.conf.set("fs.gs.auth.service.account.email", cluster_service_account)
        else:
            # Dataproc or local - use GCS connector
            spark.conf.set("spark.hadoop.google.cloud.auth.service.account.enable", "true")
            spark.conf.set("fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
            spark.conf.set("fs.AbstractFileSystem.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS")
            spark.conf.set("fs.gs.project.id", project_id)
            
            # Use service account key if provided
            service_account_key = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if service_account_key:
                spark.conf.set("fs.gs.auth.service.account.json.keyfile", service_account_key)
