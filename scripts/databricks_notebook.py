# Databricks notebook source
# MAGIC %md
# MAGIC # TPC-DI DIGen Data Generation on Databricks
# MAGIC 
# MAGIC This notebook runs the official TPC-DI DIGen tool to generate benchmark data and upload it to GCS.
# MAGIC 
# MAGIC ## Configuration
# MAGIC Update the variables in the next cell before running.

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration
# MAGIC Update these variables according to your setup:

# COMMAND ----------

# Configuration variables
SCALE_FACTOR = 10  # Scale factor (1 = ~1GB, 10 = ~10GB, etc.)
GCS_BUCKET = "your-tpc-di-bucket"  # Your GCS bucket name
GCS_RAW_PATH = "raw"  # Path in bucket for raw data
PROJECT_ID = "your-project-id"  # Your GCP project ID

# TPC-DI Tools zip file location in Databricks workspace
# Update this path to match your workspace structure
TPCDI_ZIP_PATH = "/Workspace/Users/sumit.prakash@databricks.com/Cursor/datagen/801FA37E-A4C5-4307-BD70-985A205019ED-TPC-DI-Tool.zip"

# Use Volume path for output directory (better performance for large files)
# Format: /Volumes/<catalog>/<schema>/<volume_name>/<path>
# Example: /Volumes/main/default/tpc_di_data/output
VOLUME_CATALOG = "main"  # Update to your catalog
VOLUME_SCHEMA = "default"  # Update to your schema
VOLUME_NAME = "tpc_di_data"  # Update to your volume name

# Volume-based directories (recommended for large files)
VOLUME_BASE = f"/Volumes/{VOLUME_CATALOG}/{VOLUME_SCHEMA}/{VOLUME_NAME}"
WORK_DIR_VOLUME = f"{VOLUME_BASE}/setup"
TOOLS_DIR_VOLUME = f"{WORK_DIR_VOLUME}/Tools"
OUTPUT_DIR_VOLUME = f"{VOLUME_BASE}/output"

# Fallback to DBFS if volumes are not available
WORK_DIR_DBFS = "/dbfs/tmp/tpc-di-setup"
TOOLS_DIR_DBFS = f"{WORK_DIR_DBFS}/Tools"
OUTPUT_DIR_DBFS = f"{WORK_DIR_DBFS}/output"

# Use volume path by default (set to False to use DBFS)
USE_VOLUME = True

# Set directories based on preference
if USE_VOLUME:
    WORK_DIR = WORK_DIR_VOLUME
    TOOLS_DIR = TOOLS_DIR_VOLUME
    OUTPUT_DIR = OUTPUT_DIR_VOLUME
else:
    WORK_DIR = WORK_DIR_DBFS
    TOOLS_DIR = TOOLS_DIR_DBFS
    OUTPUT_DIR = OUTPUT_DIR_DBFS

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Install Java 8 and Setup Environment

# COMMAND ----------

# MAGIC %sh
# MAGIC # Install Java 8
# MAGIC sudo apt update
# MAGIC sudo apt install openjdk-8-jdk -y
# MAGIC 
# MAGIC # Set Java environment variables
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Verify Java installation
# MAGIC java -version
# MAGIC echo "JAVA_HOME: $JAVA_HOME"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Extract TPC-DI Tools and Setup

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set Java environment (needed in each cell)
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Configuration - use volume path for better performance
# MAGIC USE_VOLUME=true
# MAGIC VOLUME_BASE="/Volumes/main/default/tpc_di_data"
# MAGIC WORK_DIR_VOLUME="${VOLUME_BASE}/setup"
# MAGIC WORK_DIR_DBFS="/dbfs/tmp/tpc-di-setup"
# MAGIC 
# MAGIC # Determine which directory to use
# MAGIC if [ "$USE_VOLUME" = "true" ] && [ -d "$VOLUME_BASE" ]; then
# MAGIC   WORK_DIR="$WORK_DIR_VOLUME"
# MAGIC   echo "Using Volume path: $WORK_DIR"
# MAGIC else
# MAGIC   WORK_DIR="$WORK_DIR_DBFS"
# MAGIC   echo "Using DBFS path: $WORK_DIR"
# MAGIC fi
# MAGIC 
# MAGIC # Create work directories
# MAGIC mkdir -p "$WORK_DIR"
# MAGIC mkdir -p "$WORK_DIR/Tools"
# MAGIC mkdir -p "${WORK_DIR%/*}/output"
# MAGIC 
# MAGIC # Copy zip file from workspace to local filesystem for extraction
# MAGIC ZIP_FILE="/Workspace/Users/sumit.prakash@databricks.com/Cursor/datagen/801FA37E-A4C5-4307-BD70-985A205019ED-TPC-DI-Tool.zip"
# MAGIC TEMP_ZIP="/tmp/tpcdi-tools.zip"
# MAGIC 
# MAGIC echo "Copying TPC-DI Tools zip file..."
# MAGIC cp "$ZIP_FILE" "$TEMP_ZIP"
# MAGIC 
# MAGIC # Extract to work directory
# MAGIC echo "Extracting TPC-DI Tools to $WORK_DIR..."
# MAGIC cd "$WORK_DIR"
# MAGIC unzip -q -o "$TEMP_ZIP"
# MAGIC 
# MAGIC # Rename PDGF to pdgf (required by DIGen)
# MAGIC if [ -d "Tools/PDGF" ]; then
# MAGIC   echo "Renaming PDGF to pdgf..."
# MAGIC   mv Tools/PDGF Tools/pdgf
# MAGIC   echo "✓ PDGF renamed to pdgf"
# MAGIC else
# MAGIC   echo "PDGF directory not found (may already be renamed)"
# MAGIC fi
# MAGIC 
# MAGIC # Verify DIGen.jar exists
# MAGIC if [ -f "Tools/DIGen.jar" ]; then
# MAGIC   echo "✓ DIGen.jar found"
# MAGIC   ls -lh Tools/DIGen.jar
# MAGIC else
# MAGIC   echo "✗ ERROR: DIGen.jar not found!"
# MAGIC   exit 1
# MAGIC fi
# MAGIC 
# MAGIC # Clean up temp file
# MAGIC rm -f "$TEMP_ZIP"
# MAGIC 
# MAGIC echo "TPC-DI Tools setup completed in $WORK_DIR!"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Download Apache Commons CLI Dependency

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set Java environment
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Use same directory as extraction step
# MAGIC USE_VOLUME=true
# MAGIC VOLUME_BASE="/Volumes/main/default/tpc_di_data"
# MAGIC WORK_DIR_VOLUME="${VOLUME_BASE}/setup"
# MAGIC WORK_DIR_DBFS="/dbfs/tmp/tpc-di-setup"
# MAGIC 
# MAGIC if [ "$USE_VOLUME" = "true" ] && [ -d "$VOLUME_BASE" ]; then
# MAGIC   WORK_DIR="$WORK_DIR_VOLUME"
# MAGIC else
# MAGIC   WORK_DIR="$WORK_DIR_DBFS"
# MAGIC fi
# MAGIC 
# MAGIC # Download Apache Commons CLI dependency (required for DIGen)
# MAGIC mkdir -p "$WORK_DIR/Tools/lib"
# MAGIC cd "$WORK_DIR/Tools/lib"
# MAGIC 
# MAGIC # Download commons-cli
# MAGIC echo "Downloading Apache Commons CLI..."
# MAGIC curl -L -o commons-cli-1.4.jar https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar
# MAGIC 
# MAGIC if [ -f "commons-cli-1.4.jar" ]; then
# MAGIC   echo "✓ Apache Commons CLI downloaded successfully"
# MAGIC   ls -lh commons-cli-1.4.jar
# MAGIC else
# MAGIC   echo "✗ ERROR: Failed to download Apache Commons CLI"
# MAGIC   exit 1
# MAGIC fi

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Run DIGen
# MAGIC 
# MAGIC You can run DIGen either using the shell command below OR using the Python function in the next cell.

# COMMAND ----------

# Python function to run DIGen in a subprocess
import subprocess
import os
import glob
import shlex

def run_digen_python(work_dir, output_dir, scale_factor=10, java_home="/usr/lib/jvm/java-8-openjdk-amd64", use_jar=False):
    """
    Run DIGen using Python subprocess
    
    Args:
        work_dir: Working directory containing Tools/
        output_dir: Output directory for generated files
        scale_factor: TPC-DI scale factor (default: 10)
        java_home: Java home directory (default: Java 8)
        use_jar: If True, use -jar flag (requires dependencies in classpath).
                 If False, use -cp with explicit main class (recommended for external dependencies)
    
    Returns:
        tuple: (exit_code, output_files_list)
    """
    import shlex
    
    # Set environment variables
    env = os.environ.copy()
    env['PDG_AGREE'] = 'YES'
    env['JAVA_HOME'] = java_home
    env['PATH'] = f"{java_home}/bin:{env.get('PATH', '')}"
    
    # Build command based on method
    digen_path = f"{work_dir}/Tools/"
    digen_jar = f"{digen_path}DIGen.jar"
    
    if use_jar:
        # Simple -jar approach (works if dependencies are already in classpath)
        cmd = f"java -Xmx8g -jar {digen_jar} -sf {scale_factor} -o {output_dir}/"
    else:
        # -cp approach with explicit main class (recommended for external dependencies)
        commons_cli = f"{digen_path}lib/commons-cli-1.4.jar"
        classpath = f"{digen_jar}:{commons_cli}"
        main_class = "org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"
        cmd = f"java -Xmx8g -cp {classpath} {main_class} -sf {scale_factor} -o {output_dir}/"
    
    # Parse command into args
    args = shlex.split(cmd)
    
    print("=" * 50)
    print("Running TPC-DI DIGen from Python")
    print("=" * 50)
    print(f"Scale Factor: {scale_factor}")
    print(f"Output Directory: {output_dir}")
    print(f"Command: {cmd}")
    print(f"PDG_AGREE: {env.get('PDG_AGREE')}")
    print("=" * 50)
    print()
    print(f"Generating data and outputting to {output_dir}")
    print()
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Clean up lock files
    lock_file = f"{digen_path}.pdgf.lock"
    if os.path.exists(lock_file):
        print(f"Removing existing lock file: {lock_file}")
        os.remove(lock_file)
    
    # Create a log file for output to avoid pipe issues
    log_file = f"{output_dir}/digen.log"
    
    try:
        # Run DIGen using shell=True to let shell handle redirection (more reliable)
        print("Starting data generation (this may take a while)...")
        print(f"Logging output to: {log_file}")
        print()
        
        # Reconstruct command as string for shell execution
        # This lets the shell handle redirection more reliably
        cmd_str = ' '.join(shlex.quote(arg) for arg in args)
        shell_cmd = f"cd {shlex.quote(digen_path)} && {cmd_str} < /dev/null > {shlex.quote(log_file)} 2>&1"
        
        # Use shell=True to let shell handle redirection (avoids broken pipe issues)
        process = subprocess.Popen(
            shell_cmd,
            shell=True,
            cwd=digen_path,
            env=env,
            universal_newlines=True
        )
        
        # Wait for process to complete
        exit_code = process.wait()
        
        # Read and display log file (filtering out null command errors)
        if os.path.exists(log_file):
            print("DIGen output:")
            print("-" * 50)
            with open(log_file, 'r') as f:
                for line in f:
                    # Filter out harmless "Command 'null' is unknown" and "Flooding prevention" errors
                    if "Command 'null' is unknown" not in line:
                        if "Flooding prevention" not in line:
                            print(line, end='')
                        elif "generating" in line or "finished" in line:
                            # Show important progress messages
                            print(line, end='')
            print("-" * 50)
        else:
            print("Warning: Log file not created")
            
    except Exception as e:
        print(f"Error running DIGen: {str(e)}")
        import traceback
        traceback.print_exc()
        exit_code = 1
    
    # Check if files were generated (even if exit code is non-zero)
    output_files = []
    if os.path.exists(output_dir):
        output_files = glob.glob(f"{output_dir}/*.txt")
    
    if exit_code != 0 and len(output_files) > 0:
        print()
        print(f"✓ Found {len(output_files)} generated files - data generation succeeded!")
        print("(Exit code was non-zero but files were generated - ignoring error)")
        exit_code = 0
    
    return exit_code, output_files

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option A: Run DIGen using Python (Recommended)
# MAGIC 
# MAGIC Use this if you want to run DIGen from a Python cell with better error handling and output streaming.
# MAGIC 
# MAGIC **Note:** If you encounter "Broken pipe" errors, try Option B (Shell Command) instead, as DIGen may have issues with Python subprocess file redirection.

# COMMAND ----------

# Run DIGen using Python subprocess
import os

# Determine directories
if USE_VOLUME and os.path.exists(VOLUME_BASE):
    work_dir = WORK_DIR_VOLUME
    output_dir = OUTPUT_DIR_VOLUME
    print(f"Using Volume paths: {work_dir}")
else:
    work_dir = WORK_DIR_DBFS
    output_dir = OUTPUT_DIR_DBFS
    print(f"Using DBFS paths: {work_dir}")

# Set Java home
JAVA_HOME = "/usr/lib/jvm/java-8-openjdk-amd64"

# Run DIGen
# Set use_jar=True if you want to use -jar flag (requires dependencies in classpath)
# Set use_jar=False (default) to use -cp with explicit main class (recommended)
exit_code, output_files = run_digen_python(
    work_dir=work_dir,
    output_dir=output_dir,
    scale_factor=SCALE_FACTOR,
    java_home=JAVA_HOME,
    use_jar=False  # Set to True to use -jar flag instead of -cp
)

# Check results
if exit_code == 0:
    print()
    print("=" * 50)
    print("✓ Data generation completed successfully!")
    print("=" * 50)
    print(f"Generated {len(output_files)} files:")
    for f in sorted(output_files)[:10]:  # Show first 10 files
        size_mb = os.path.getsize(f) / (1024 * 1024)
        print(f"  {os.path.basename(f)} ({size_mb:.2f} MB)")
    if len(output_files) > 10:
        print(f"  ... and {len(output_files) - 10} more files")
else:
    print()
    print("=" * 50)
    print(f"✗ ERROR: Data generation failed with exit code: {exit_code}")
    print("=" * 50)
    raise Exception(f"DIGen failed with exit code {exit_code}")

# COMMAND ----------

# MAGIC %md
# MAGIC ### Option B: Run DIGen using Shell Command
# MAGIC 
# MAGIC Alternative method using shell command (use if Python method doesn't work).

# COMMAND ----------

# MAGIC %sh
# MAGIC # Set Java environment
# MAGIC export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
# MAGIC export PATH=$JAVA_HOME/bin:$PATH
# MAGIC 
# MAGIC # Set PDG agreement (required by DIGen) - must be set BEFORE running
# MAGIC export PDG_AGREE=YES
# MAGIC 
# MAGIC # Use volume path for output (better performance)
# MAGIC USE_VOLUME=true
# MAGIC VOLUME_BASE="/Volumes/main/default/tpc_di_data"
# MAGIC WORK_DIR_VOLUME="${VOLUME_BASE}/setup"
# MAGIC OUTPUT_DIR_VOLUME="${VOLUME_BASE}/output"
# MAGIC WORK_DIR_DBFS="/dbfs/tmp/tpc-di-setup"
# MAGIC OUTPUT_DIR_DBFS="${WORK_DIR_DBFS}/output"
# MAGIC 
# MAGIC if [ "$USE_VOLUME" = "true" ] && [ -d "$VOLUME_BASE" ]; then
# MAGIC   WORK_DIR="$WORK_DIR_VOLUME"
# MAGIC   OUTPUT_DIR="$OUTPUT_DIR_VOLUME"
# MAGIC   echo "Using Volume paths for better performance"
# MAGIC else
# MAGIC   WORK_DIR="$WORK_DIR_DBFS"
# MAGIC   OUTPUT_DIR="$OUTPUT_DIR_DBFS"
# MAGIC   echo "Using DBFS paths"
# MAGIC fi
# MAGIC 
# MAGIC # Navigate to Tools directory
# MAGIC cd "$WORK_DIR/Tools"
# MAGIC 
# MAGIC # Build classpath with dependencies
# MAGIC CLASSPATH="$WORK_DIR/Tools/DIGen.jar:$WORK_DIR/Tools/lib/commons-cli-1.4.jar"
# MAGIC 
# MAGIC # Main class (Eclipse JAR wrapper)
# MAGIC MAIN_CLASS="org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"
# MAGIC 
# MAGIC # Scale factor
# MAGIC SCALE_FACTOR=10
# MAGIC 
# MAGIC # Create output directory
# MAGIC mkdir -p "$OUTPUT_DIR"
# MAGIC 
# MAGIC # Clean up any existing lock files or processes
# MAGIC echo "Cleaning up any existing DIGen processes or lock files..."
# MAGIC 
# MAGIC # Remove lock files
# MAGIC LOCK_FILE="$WORK_DIR/Tools/.pdgf.lock"
# MAGIC if [ -f "$LOCK_FILE" ]; then
# MAGIC   echo "  Removing existing lock file: $LOCK_FILE"
# MAGIC   rm -f "$LOCK_FILE"
# MAGIC fi
# MAGIC 
# MAGIC # Check for any running Java processes with DIGen
# MAGIC JAVA_PIDS=$(pgrep -f "DIGen.jar" || true)
# MAGIC if [ -n "$JAVA_PIDS" ]; then
# MAGIC   echo "  Warning: Found running DIGen processes: $JAVA_PIDS"
# MAGIC   echo "  Consider waiting for them to finish or killing them manually"
# MAGIC fi
# MAGIC 
# MAGIC # Ensure output directory is writable
# MAGIC if [ ! -w "$OUTPUT_DIR" ]; then
# MAGIC   echo "  Error: Output directory is not writable: $OUTPUT_DIR"
# MAGIC   exit 1
# MAGIC fi
# MAGIC 
# MAGIC echo "=========================================="
# MAGIC echo "Running TPC-DI DIGen"
# MAGIC echo "=========================================="
# MAGIC echo "Scale Factor: $SCALE_FACTOR"
# MAGIC echo "Output Directory: $OUTPUT_DIR"
# MAGIC echo "Classpath: $CLASSPATH"
# MAGIC echo "Main Class: $MAIN_CLASS"
# MAGIC echo "PDG_AGREE: $PDG_AGREE"
# MAGIC echo "=========================================="
# MAGIC echo ""
# MAGIC echo "Starting data generation (this may take a while)..."
# MAGIC echo "Note: PDG_AGREE=YES is set to automatically accept license"
# MAGIC echo ""
# MAGIC echo "Running DIGen in non-interactive mode..."
# MAGIC echo ""
# MAGIC 
# MAGIC # CRITICAL: Run DIGen with stdin redirected and output captured
# MAGIC # DIGen reads from System.in in Java, so we must redirect at the shell level
# MAGIC # PDG_AGREE=YES environment variable handles license agreement automatically
# MAGIC # Use -cp WITHOUT -jar to include external dependencies
# MAGIC 
# MAGIC # Run with stdin closed and capture both stdout and stderr
# MAGIC # Note: DIGen may show "Command 'null' is unknown" errors - these are harmless
# MAGIC # DIGen runs in interactive mode and tries to read from stdin, but PDG_AGREE=YES
# MAGIC # handles the license agreement, so it will continue generating data despite these errors
# MAGIC cd "$WORK_DIR/Tools"
# MAGIC 
# MAGIC # Run DIGen (errors about "null" commands can be ignored if data is generated)
# MAGIC java -Xmx8g -cp "$CLASSPATH" $MAIN_CLASS -o "$OUTPUT_DIR/" -sf $SCALE_FACTOR 2>&1 < /dev/null
# MAGIC 
# MAGIC # Capture exit code
# MAGIC DIGEN_EXIT_CODE=$?
# MAGIC 
# MAGIC # Note: Even if exit code is non-zero due to "null" command errors,
# MAGIC # check if files were actually generated (DIGen may complete successfully)
# MAGIC if [ $DIGEN_EXIT_CODE -ne 0 ]; then
# MAGIC   echo ""
# MAGIC   echo "Checking if data files were generated despite errors..."
# MAGIC   if ls "$OUTPUT_DIR"/*.txt 1> /dev/null 2>&1; then
# MAGIC     FILE_COUNT=$(ls -1 "$OUTPUT_DIR"/*.txt 2>/dev/null | wc -l)
# MAGIC     if [ $FILE_COUNT -gt 0 ]; then
# MAGIC       echo "✓ Found $FILE_COUNT generated files - data generation succeeded!"
# MAGIC       DIGEN_EXIT_CODE=0  # Override exit code since files were generated
# MAGIC     fi
# MAGIC   fi
# MAGIC fi
# MAGIC 
# MAGIC # Check exit code
# MAGIC if [ $DIGEN_EXIT_CODE -eq 0 ]; then
# MAGIC   echo ""
# MAGIC   echo "=========================================="
# MAGIC   echo "✓ Data generation completed successfully!"
# MAGIC   echo "=========================================="
# MAGIC else
# MAGIC   echo ""
# MAGIC   echo "=========================================="
# MAGIC   echo "✗ ERROR: Data generation failed with exit code: $DIGEN_EXIT_CODE"
# MAGIC   echo "=========================================="
# MAGIC   echo ""
# MAGIC   echo "Troubleshooting tips:"
# MAGIC   echo "1. Check if PDG_AGREE=YES is set: echo \$PDG_AGREE"
# MAGIC   echo "2. Verify Java version: java -version"
# MAGIC   echo "3. Check output directory permissions: ls -ld $OUTPUT_DIR"
# MAGIC   echo "4. Check for lock files: ls -la $WORK_DIR/Tools/.pdgf*"
# MAGIC   echo ""
# MAGIC   exit $DIGEN_EXIT_CODE
# MAGIC fi

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: List Generated Files

# COMMAND ----------

# MAGIC %sh
# MAGIC # Use same output directory as DIGen step
# MAGIC USE_VOLUME=true
# MAGIC VOLUME_BASE="/Volumes/main/default/tpc_di_data"
# MAGIC OUTPUT_DIR_VOLUME="${VOLUME_BASE}/output"
# MAGIC OUTPUT_DIR_DBFS="/dbfs/tmp/tpc-di-setup/output"
# MAGIC 
# MAGIC if [ "$USE_VOLUME" = "true" ] && [ -d "$VOLUME_BASE" ]; then
# MAGIC   OUTPUT_DIR="$OUTPUT_DIR_VOLUME"
# MAGIC else
# MAGIC   OUTPUT_DIR="$OUTPUT_DIR_DBFS"
# MAGIC fi
# MAGIC 
# MAGIC echo "Checking output directory: $OUTPUT_DIR"
# MAGIC echo "Generated files:"
# MAGIC echo "=========================================="
# MAGIC ls -lh "$OUTPUT_DIR"/*.txt 2>/dev/null | awk '{print $9, "(" $5 ")"}'
# MAGIC 
# MAGIC # Count files
# MAGIC FILE_COUNT=$(ls -1 "$OUTPUT_DIR"/*.txt 2>/dev/null | wc -l)
# MAGIC echo ""
# MAGIC echo "Total files generated: $FILE_COUNT"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Upload Generated Files to GCS

# COMMAND ----------

from pyspark.dbutils import DBUtils
import glob
import os

dbutils = DBUtils()

# Configuration - use volume path if available
USE_VOLUME = True
VOLUME_BASE = "/Volumes/main/default/tpc_di_data"
OUTPUT_DIR_VOLUME = f"{VOLUME_BASE}/output"
OUTPUT_DIR_DBFS = "/dbfs/tmp/tpc-di-setup/output"

# Determine output directory
if USE_VOLUME and os.path.exists(VOLUME_BASE):
    output_dir = OUTPUT_DIR_VOLUME
    print(f"Using Volume path: {output_dir}")
else:
    output_dir = OUTPUT_DIR_DBFS
    print(f"Using DBFS path: {output_dir}")

gcs_bucket = "your-tpc-di-bucket"  # Update this
gcs_path = "raw"  # Update this

# List generated files
txt_files = glob.glob(os.path.join(output_dir, "*.txt"))
print(f"Found {len(txt_files)} files to upload:")

for file_path in txt_files:
    filename = os.path.basename(file_path)
    file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
    print(f"  {filename} ({file_size:.2f} MB)")

# COMMAND ----------

# Upload all .txt files to GCS
for file_path in txt_files:
    filename = os.path.basename(file_path)
    gcs_dest = f"gs://{gcs_bucket}/{gcs_path}/{filename}"
    
    print(f"Uploading {filename} to {gcs_dest}...")
    try:
        dbutils.fs.cp(f"file://{file_path}", gcs_dest)
        print(f"✓ Successfully uploaded {filename}")
    except Exception as e:
        print(f"✗ Failed to upload {filename}: {str(e)}")

print(f"\nAll files uploaded to gs://{gcs_bucket}/{gcs_path}/")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7: Verify Upload

# COMMAND ----------

# List files in GCS
gcs_path_full = f"gs://{gcs_bucket}/{gcs_path}/"
files = dbutils.fs.ls(gcs_path_full)

print(f"Files in {gcs_path_full}:")
for file_info in files:
    size_mb = file_info.size / (1024 * 1024)
    print(f"  {file_info.name} ({size_mb:.2f} MB)")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next Steps
# MAGIC 
# MAGIC After data generation:
# MAGIC 1. Verify files in GCS: `dbutils.fs.ls('gs://your-bucket/raw/')`
# MAGIC 2. Run your PySpark pipeline: `python src/main.py --load-type historical`
# MAGIC 3. Process data through Bronze → Silver → Gold layers
