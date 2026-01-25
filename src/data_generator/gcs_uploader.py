"""
GCS Uploader for TPC-DI generated data
"""
import os
from pathlib import Path
from typing import Dict, Optional
from google.cloud import storage
import logging

logger = logging.getLogger(__name__)


class GCSUploader:
    """Upload generated TPC-DI data files to GCS"""
    
    def __init__(self, bucket_name: str, project_id: Optional[str] = None):
        """
        Initialize GCS uploader
        
        Args:
            bucket_name: GCS bucket name
            project_id: GCP project ID (optional)
        """
        self.bucket_name = bucket_name
        self.client = storage.Client(project=project_id) if project_id else storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def upload_file(self, local_path: str, gcs_path: str) -> str:
        """
        Upload a single file to GCS
        
        Args:
            local_path: Local file path
            gcs_path: GCS destination path
            
        Returns:
            GCS URI
        """
        logger.info(f"Uploading {local_path} to gs://{self.bucket_name}/{gcs_path}")
        
        blob = self.bucket.blob(gcs_path)
        blob.upload_from_filename(local_path)
        
        gcs_uri = f"gs://{self.bucket_name}/{gcs_path}"
        logger.info(f"Uploaded: {gcs_uri}")
        return gcs_uri
    
    def upload_directory(self, local_dir: str, gcs_prefix: str,
                        file_pattern: str = "*.txt") -> Dict[str, str]:
        """
        Upload all files from a directory to GCS
        
        Args:
            local_dir: Local directory path
            gcs_prefix: GCS path prefix
            file_pattern: File pattern to match
            
        Returns:
            Dictionary mapping local paths to GCS URIs
        """
        local_path = Path(local_dir)
        uploaded_files = {}
        
        for file_path in local_path.glob(file_pattern):
            relative_path = file_path.relative_to(local_path)
            gcs_path = f"{gcs_prefix}/{relative_path}" if gcs_prefix else str(relative_path)
            
            gcs_uri = self.upload_file(str(file_path), gcs_path)
            uploaded_files[str(file_path)] = gcs_uri
        
        return uploaded_files
    
    def upload_generated_data(self, generated_files: Dict[str, str],
                             gcs_prefix: str = "raw") -> Dict[str, str]:
        """
        Upload generated TPC-DI data files to GCS
        
        Args:
            generated_files: Dictionary mapping table names to local file paths
            gcs_prefix: GCS path prefix (e.g., "raw")
            
        Returns:
            Dictionary mapping table names to GCS URIs
        """
        logger.info(f"Uploading {len(generated_files)} files to GCS...")
        
        gcs_files = {}
        for table_name, local_path in generated_files.items():
            file_name = Path(local_path).name
            gcs_path = f"{gcs_prefix}/{file_name}"
            
            gcs_uri = self.upload_file(local_path, gcs_path)
            gcs_files[table_name] = gcs_uri
        
        logger.info("All files uploaded to GCS successfully!")
        return gcs_files
