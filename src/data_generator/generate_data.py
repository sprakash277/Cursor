"""
CLI script for generating TPC-DI benchmark data
"""
import argparse
import sys
import os
import logging
import yaml

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.data_generator.tpc_di_generator import TPC_DI_Generator
from src.data_generator.gcs_uploader import GCSUploader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config(config_path: str = "config/config.yaml"):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}. Using defaults.")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description="Generate TPC-DI benchmark data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate data with scale factor 1.0 (default)
  python src/data_generator/generate_data.py

  # Generate data with scale factor 10.0
  python src/data_generator/generate_data.py --scale-factor 10.0

  # Generate and upload to GCS
  python src/data_generator/generate_data.py --upload-to-gcs

  # Generate specific tables only
  python src/data_generator/generate_data.py --tables Date Customer Trade
        """
    )
    
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=1.0,
        help="Scale factor for data generation (1.0 = ~1GB, 10.0 = ~10GB, etc.)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/raw",
        help="Output directory for generated files (default: data/raw)"
    )
    
    parser.add_argument(
        "--upload-to-gcs",
        action="store_true",
        help="Upload generated files to GCS bucket"
    )
    
    parser.add_argument(
        "--tables",
        nargs="+",
        help="Specific tables to generate (default: all tables)"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="Path to configuration file"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Initialize generator
    generator = TPC_DI_Generator(
        scale_factor=args.scale_factor,
        output_dir=args.output_dir
    )
    
    # Generate data
    if args.tables:
        # Generate specific tables
        logger.info(f"Generating tables: {args.tables}")
        generated_files = {}
        
        if "Date" in args.tables:
            generated_files["Date"] = generator.generate_date_dimension()
        if "Time" in args.tables:
            generated_files["Time"] = generator.generate_time_dimension()
        if "Customer" in args.tables:
            generated_files["Customer"] = generator.generate_customer_dimension()
        if "Account" in args.tables:
            generated_files["Account"] = generator.generate_account_dimension()
        if "Security" in args.tables:
            generated_files["Security"] = generator.generate_security_dimension()
        if "Company" in args.tables:
            generated_files["Company"] = generator.generate_company_dimension()
        if "Trade" in args.tables:
            generated_files["Trade"] = generator.generate_trade_fact()
    else:
        # Generate all tables
        generated_files = generator.generate_all()
    
    logger.info(f"Generated {len(generated_files)} data files")
    for table_name, file_path in generated_files.items():
        logger.info(f"  {table_name}: {file_path}")
    
    # Upload to GCS if requested
    if args.upload_to_gcs:
        bucket_name = config.get("gcs", {}).get("bucket_name")
        if not bucket_name:
            logger.error("GCS bucket name not found in config. Please set it in config.yaml")
            sys.exit(1)
        
        project_id = config.get("dataproc", {}).get("project_id")
        raw_data_path = config.get("gcs", {}).get("raw_data_path", "raw")
        
        uploader = GCSUploader(bucket_name=bucket_name, project_id=project_id)
        gcs_files = uploader.upload_generated_data(
            generated_files=generated_files,
            gcs_prefix=raw_data_path
        )
        
        logger.info("Files uploaded to GCS:")
        for table_name, gcs_uri in gcs_files.items():
            logger.info(f"  {table_name}: {gcs_uri}")
    
    logger.info("Data generation completed successfully!")


if __name__ == "__main__":
    main()
