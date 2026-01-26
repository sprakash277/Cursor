"""
Helper script to copy TPC-DI data from Databricks to GCS for Dataproc
"""

import os
import subprocess
from pathlib import Path
from google.cloud import storage
from databricks.sdk import WorkspaceClient
import yaml


def copy_databricks_to_gcs(
    workspace_url: str,
    token: str,
    dbfs_path: str,
    gcs_bucket: str,
    gcs_prefix: str = "tpcdi"
):
    """
    Copy data from Databricks DBFS to Google Cloud Storage
    
    Args:
        workspace_url: Databricks workspace URL
        token: Databricks token
        dbfs_path: DBFS path to copy from (e.g., dbfs:/tmp/tpcdi)
        gcs_bucket: GCS bucket name
        gcs_prefix: GCS prefix/path (default: tpcdi)
    """
    print(f"Copying data from {dbfs_path} to gs://{gcs_bucket}/{gcs_prefix}/")
    
    # Initialize clients
    w = WorkspaceClient(host=workspace_url, token=token)
    gcs_client = storage.Client()
    bucket = gcs_client.bucket(gcs_bucket)
    
    # List files in DBFS
    print("Listing files in DBFS...")
    try:
        files = w.dbfs.list(path=dbfs_path.replace("dbfs:", ""))
        
        for file_info in files:
            if file_info.is_dir:
                # Recursively handle directories
                sub_path = f"{dbfs_path}/{file_info.path}"
                copy_databricks_to_gcs(
                    workspace_url, token, sub_path, gcs_bucket,
                    f"{gcs_prefix}/{file_info.path}"
                )
            else:
                # Download from DBFS and upload to GCS
                print(f"  Copying {file_info.path}...")
                
                # Download from DBFS
                with w.dbfs.open(file_info.path) as dbfs_file:
                    content = dbfs_file.read()
                    
                    # Upload to GCS
                    blob = bucket.blob(f"{gcs_prefix}/{file_info.path}")
                    blob.upload_from_string(content)
                    
                print(f"    ✓ Copied to gs://{gcs_bucket}/{gcs_prefix}/{file_info.path}")
                
    except Exception as e:
        print(f"Error: {str(e)}")
        print("\nAlternative: Use Databricks CLI or dbutils to copy files")
        print(f"  databricks fs cp -r {dbfs_path} gs://{gcs_bucket}/{gcs_prefix}/")
        print("\nOr use dbutils in a Databricks notebook:")
        print(f"  dbutils.fs.cp('{dbfs_path}', 'gs://{gcs_bucket}/{gcs_prefix}/', recurse=True)")


def copy_using_cli(dbfs_path: str, gcs_bucket: str, gcs_prefix: str = "tpcdi"):
    """
    Alternative method using Databricks CLI (if available)
    """
    print(f"Using Databricks CLI to copy data...")
    print(f"From: {dbfs_path}")
    print(f"To: gs://{gcs_bucket}/{gcs_prefix}/")
    
    cmd = [
        "databricks",
        "fs",
        "cp",
        "-r",
        dbfs_path,
        f"gs://{gcs_bucket}/{gcs_prefix}/"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Copy completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        print("\nMake sure:")
        print("  1. Databricks CLI is installed: pip install databricks-cli")
        print("  2. You're authenticated: databricks configure --token")
        print("  3. You have write access to the GCS bucket")
    except FileNotFoundError:
        print("✗ Databricks CLI not found")
        print("  Install it with: pip install databricks-cli")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Copy TPC-DI data from Databricks to GCS")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--dbfs-path", help="DBFS path (overrides config)")
    parser.add_argument("--gcs-bucket", help="GCS bucket (overrides config)")
    parser.add_argument("--gcs-prefix", default="tpcdi", help="GCS prefix")
    parser.add_argument("--use-cli", action="store_true", help="Use Databricks CLI instead of SDK")
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    dbfs_path = args.dbfs_path or config['databricks']['storage_path']
    gcs_bucket = args.gcs_bucket or config['dataproc']['bucket_name']
    
    if args.use_cli:
        copy_using_cli(dbfs_path, gcs_bucket, args.gcs_prefix)
    else:
        workspace_url = config['databricks']['workspace_url']
        token = os.getenv('DATABRICKS_TOKEN') or config['databricks'].get('token')
        
        if not token:
            print("Error: DATABRICKS_TOKEN not set. Set it in .env or config.yaml")
            exit(1)
        
        copy_databricks_to_gcs(workspace_url, token, dbfs_path, gcs_bucket, args.gcs_prefix)
