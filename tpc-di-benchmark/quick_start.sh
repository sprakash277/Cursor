#!/bin/bash
# Quick start script for TPC-DI benchmark setup

set -e

echo "=========================================="
echo "TPC-DI Benchmark Quick Start"
echo "=========================================="
echo ""

# Check for Java
if ! command -v java &> /dev/null; then
    echo "Error: Java is required but not found"
    echo "Please install Java 7+ and try again"
    exit 1
fi

echo "✓ Java found: $(java -version 2>&1 | head -n 1)"
echo ""

# Check for DIGen
DIGEN_PATH="./Tools/DIGen.jar"
if [ ! -f "$DIGEN_PATH" ]; then
    echo "Warning: DIGen.jar not found at $DIGEN_PATH"
    echo ""
    echo "Please:"
    echo "1. Download TPCDI_Tools from:"
    echo "   https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp"
    echo "2. Extract and ensure PDGF is renamed to pdgf (lowercase)"
    echo "3. Place DIGen.jar in ./Tools/DIGen.jar"
    echo ""
    read -p "Press Enter to continue anyway, or Ctrl+C to exit..."
fi

# Default values
SCALE_FACTOR=${1:-1}
OUTPUT_DIR=${2:-"./tpcdi_data"}

echo "Configuration:"
echo "  Scale Factor: $SCALE_FACTOR"
echo "  Output Directory: $OUTPUT_DIR"
echo ""

# Generate data
echo "Step 1: Generating TPC-DI data..."
python tpcdi_digen_wrapper.py \
    --digen-path "$DIGEN_PATH" \
    --scale-factor "$SCALE_FACTOR" \
    --output-dir "$OUTPUT_DIR" \
    --generate-notebook

echo ""
echo "✓ Data generation complete!"
echo ""
echo "Next steps:"
echo "1. Upload data to Databricks:"
echo "   python tpcdi_digen_wrapper.py --upload --workspace-url <url> --token <token>"
echo ""
echo "2. Or use Databricks CLI:"
echo "   databricks fs cp -r $OUTPUT_DIR dbfs:/tmp/tpcdi/"
echo ""
echo "3. Load data using the generated notebook: $OUTPUT_DIR/load_tpcdi_data.py"
echo ""
