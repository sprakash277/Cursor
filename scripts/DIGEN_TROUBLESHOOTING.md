# TPC-DI DIGen Troubleshooting Guide

## Common Errors and Solutions

### Error: "Command 'YES' is unknown" or "Command 'EXIT_CODE=$?' is unknown"

**Problem:** DIGen is running in interactive mode and reading subsequent shell commands from stdin as commands to its interactive shell.

**Solution:** 
- Redirect stdin to `/dev/null` when running DIGen
- Set `PDG_AGREE=YES` as an environment variable BEFORE running DIGen
- The environment variable handles license agreement, and redirecting stdin prevents interactive mode

**Correct command:**
```bash
export PDG_AGREE=YES
java -Xmx8g -cp "DIGen.jar:lib/commons-cli-1.4.jar" org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader -o /output/ -sf 1 < /dev/null
```

**Incorrect commands (DO NOT USE):**
```bash
yes YES | java -Xmx8g -cp "..." ...  # This causes errors!
java -Xmx8g -cp "..." ...  # Without < /dev/null, reads shell commands as input!
```

### Error: "Cannot start again while data generation process is already running"

**Problem:** DIGen detected a previous run or lock file exists.

**Solution:**
1. Check for lock files: `ls -la Tools/.pdgf*`
2. Remove lock file: `rm -f Tools/.pdgf.lock`
3. Check for running processes: `pgrep -f DIGen.jar`
4. Kill any stuck processes: `pkill -f DIGen.jar`
5. Clean output directory if needed: `rm -rf output/*`

### Error: "Illegal try to restart a died worker thread"

**Problem:** This usually occurs after the previous errors cause DIGen to crash.

**Solution:**
1. Clean up lock files and processes (see above)
2. Ensure `PDG_AGREE=YES` is set correctly
3. Restart from a clean state
4. Check Java heap size - may need to increase: `-Xmx8g` or higher

### Error: "NoClassDefFoundError: org/apache/commons/cli/Options"

**Problem:** Apache Commons CLI dependency is missing or not in classpath.

**Solution:**
1. Download commons-cli: 
   ```bash
   mkdir -p Tools/lib
   cd Tools/lib
   curl -L -o commons-cli-1.4.jar https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar
   ```

2. Use `-cp` WITHOUT `-jar`:
   ```bash
   java -cp "Tools/DIGen.jar:Tools/lib/commons-cli-1.4.jar" org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader -o output/ -sf 1
   ```

### Error: "PDGF directory not found" or "PDGF to pdgf rename required"

**Problem:** TPC-DI Tools zip extracts with `PDGF` directory, but DIGen expects `pdgf` (lowercase).

**Solution:**
```bash
cd Tools
if [ -d "PDGF" ]; then
  mv PDGF pdgf
  echo "✓ Renamed PDGF to pdgf"
fi
```

## Why Redirect Stdin?

DIGen runs in an interactive mode by default and reads from stdin. When you run it in a shell script, any commands that come after the Java command (like `EXIT_CODE=$?`, `if`, `echo`, etc.) get read by DIGen's interactive shell as commands, causing errors like:
- "Command 'EXIT_CODE=$?' is unknown"
- "Command 'if' is unknown"
- "Command 'echo' is unknown"

**Solution:** Redirect stdin to `/dev/null`:
```bash
java ... < /dev/null
```

This prevents DIGen from reading anything from stdin, forcing it to run non-interactively.

## Best Practices

### 1. Always Set PDG_AGREE Before Running
```bash
export PDG_AGREE=YES
# Then run DIGen
```

### 2. Always Redirect Stdin
```bash
java ... < /dev/null
```

### 2. Use Absolute Paths for Classpath
```bash
CLASSPATH="/full/path/to/DIGen.jar:/full/path/to/lib/commons-cli-1.4.jar"
```

### 3. Clean Up Before Running
```bash
# Remove lock files
rm -f Tools/.pdgf.lock

# Check for running processes
pgrep -f DIGen.jar

# Ensure output directory exists and is writable
mkdir -p output
chmod 755 output
```

### 4. Verify Environment
```bash
# Check Java version (should be 8+)
java -version

# Check PDG_AGREE is set
echo $PDG_AGREE  # Should output: YES

# Check classpath files exist
ls -lh Tools/DIGen.jar
ls -lh Tools/lib/commons-cli-*.jar
```

## Complete Working Example

```bash
#!/bin/bash
set -e

# Configuration
SCALE_FACTOR=1
OUTPUT_DIR="/dbfs/tmp/tpc-di-setup/output"
WORK_DIR="/dbfs/tmp/tpc-di-setup"

# Set Java environment
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH

# CRITICAL: Set PDG agreement BEFORE running
export PDG_AGREE=YES

# Clean up any existing processes or locks
rm -f "$WORK_DIR/Tools/.pdgf.lock"
pkill -f DIGen.jar || true

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Navigate to Tools directory
cd "$WORK_DIR/Tools"

# Verify files exist
if [ ! -f "DIGen.jar" ]; then
  echo "ERROR: DIGen.jar not found!"
  exit 1
fi

if [ ! -f "lib/commons-cli-1.4.jar" ]; then
  echo "ERROR: commons-cli-1.4.jar not found!"
  exit 1
fi

# Build classpath with absolute paths
CLASSPATH="$WORK_DIR/Tools/DIGen.jar:$WORK_DIR/Tools/lib/commons-cli-1.4.jar"

# Main class
MAIN_CLASS="org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"

# Run DIGen (NO pipe, NO -jar flag, redirect stdin to prevent interactive mode)
echo "Running DIGen with scale factor: $SCALE_FACTOR"
echo "Output directory: $OUTPUT_DIR"
echo "PDG_AGREE: $PDG_AGREE"

# CRITICAL: Redirect stdin to /dev/null to prevent DIGen from reading shell commands
java -Xmx8g -cp "$CLASSPATH" $MAIN_CLASS -o "$OUTPUT_DIR/" -sf $SCALE_FACTOR < /dev/null

DIGEN_EXIT=$?
if [ $DIGEN_EXIT -eq 0 ]; then
  echo "✓ Data generation completed successfully!"
  ls -lh "$OUTPUT_DIR"/*.txt
else
  echo "✗ Data generation failed!"
  exit 1
fi
```

## Databricks-Specific Notes

1. **Volume Paths:** Use `/Volumes/...` for better performance with large files
2. **DBFS Paths:** Use `/dbfs/...` as fallback (slower but works everywhere)
3. **Environment Variables:** Set in each `%sh` cell (they don't persist between cells)
4. **Java Installation:** May need to install Java 8 in each cell:
   ```bash
   sudo apt update && sudo apt install openjdk-8-jdk -y
   export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
   ```

## Still Having Issues?

1. Check DIGen logs in the output directory
2. Verify all prerequisites are met (Java 8+, commons-cli, correct directory structure)
3. Try running with a smaller scale factor first (e.g., `-sf 1`)
4. Check disk space: `df -h`
5. Check memory: `free -h`
6. Review full error output for specific error messages
