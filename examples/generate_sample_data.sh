#!/bin/bash
# Example script to generate sample TPC-DI data

echo "Generating TPC-DI sample data with scale factor 1.0..."
python src/data_generator/generate_data.py --scale-factor 1.0 --output-dir data/raw

echo ""
echo "Data generation complete! Files are in data/raw/"
echo ""
echo "To upload to GCS, run:"
echo "python src/data_generator/generate_data.py --scale-factor 1.0 --upload-to-gcs"
