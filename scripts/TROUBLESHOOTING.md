# TPC-DI DIGen Troubleshooting Guide

## Common Issues and Solutions

### 1. NoClassDefFoundError: org.apache.commons.cli.ParseException

**Error:**
```
Exception in thread "main" java.lang.NoClassDefFoundError: org/apache/commons/cli/ParseException
```

**Cause:**
DIGen.jar requires Apache Commons CLI library on the classpath, but it's not bundled with the JAR.

**Solution:**

**Option A: Use the fix script (Recommended)**
```bash
# Run the dependency fix script
./scripts/fix_digen_dependencies.sh /path/to/Tools

# Then run DIGen with classpath
cd /path/to/Tools
java -cp DIGen.jar:lib/commons-cli-1.4.jar -jar DIGen.jar -o /output/ -sf 1
```

**Option B: Manual download**
```bash
# Create lib directory
mkdir -p Tools/lib

# Download Apache Commons CLI
cd Tools/lib
curl -L -o commons-cli-1.4.jar \
  https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar

# Run with classpath
cd ..
java -cp DIGen.jar:lib/commons-cli-1.4.jar -jar DIGen.jar -o /output/ -sf 1
```

**Option C: In Databricks notebook**
```python
# MAGIC %sh
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC curl -L -o commons-cli-1.4.jar https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar
# MAGIC 
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools
# MAGIC CLASSPATH="DIGen.jar:lib/commons-cli-1.4.jar"
# MAGIC java -Xmx4g -cp "$CLASSPATH" -jar DIGen.jar -o /dbfs/tmp/tpc-di-setup/output/ -sf 1
```

### 2. Java Not Found

**Error:**
```
java: command not found
```

**Solution:**
```bash
# Check if Java is installed
which java
java -version

# On Databricks/Dataproc, Java should be pre-installed
# If not, install:
sudo apt-get update
sudo apt-get install -y openjdk-8-jdk

# Or use system Java
export JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
export PATH=$JAVA_HOME/bin:$PATH
```

### 3. Out of Memory Error

**Error:**
```
java.lang.OutOfMemoryError: Java heap space
```

**Solution:**
Increase Java heap size:
```bash
# Increase from default to 4GB
java -Xmx4g -cp DIGen.jar:lib/commons-cli-1.4.jar -jar DIGen.jar -o /output/ -sf 1

# For larger scale factors, use 8GB or more
java -Xmx8g -cp DIGen.jar:lib/commons-cli-1.4.jar -jar DIGen.jar -o /output/ -sf 10
```

### 4. PDGF Directory Not Found

**Error:**
```
Error: PDGF directory not found
```

**Solution:**
The PDGF directory must be renamed to lowercase `pdgf`:
```bash
cd Tools
if [ -d "PDGF" ]; then
    mv PDGF pdgf
fi
```

### 5. Permission Denied

**Error:**
```
Permission denied: /output/
```

**Solution:**
```bash
# Create output directory with proper permissions
mkdir -p /output
chmod 755 /output

# On Databricks, use /dbfs/ for persistent storage
mkdir -p /dbfs/tmp/tpc-di-setup/output
```

### 6. GCS Upload Fails

**Error:**
```
AccessDeniedException: 403 Forbidden
```

**Solution:**

**For Databricks:**
```python
# Verify service account has Storage Admin role
# Check cluster configuration for service account

# Test GCS access
dbutils.fs.ls("gs://your-bucket/")
```

**For Dataproc:**
```bash
# Verify service account permissions
gcloud projects get-iam-policy your-project-id

# Test gsutil
gsutil ls gs://your-bucket/
```

### 7. DIGen.jar Not Found

**Error:**
```
DIGen.jar not found
```

**Solution:**
1. Download TPCDI_Tools.zip from TPC website
2. Extract: `unzip TPCDI_Tools.zip`
3. Rename PDGF: `mv Tools/PDGF Tools/pdgf`
4. Verify: `ls Tools/DIGen.jar`

### 8. Scale Factor Too Large

**Error:**
```
Out of disk space
```

**Solution:**
- Use smaller scale factor
- Clean up temporary files
- Use larger disk for cluster
- Generate in batches

### 9. ClassNotFoundException with Different Class

If you see a different missing class, check what's needed:

```bash
# Extract JAR to see dependencies
unzip -l DIGen.jar | grep -i "META-INF/MANIFEST.MF"
unzip -p DIGen.jar META-INF/MANIFEST.MF | grep -i "class-path"

# Check what classes are referenced
jar tf DIGen.jar | grep -i "import\|require"
```

### 10. Script Execution Fails on Databricks

**Error:**
```
Script not executable or path not found
```

**Solution:**
```python
# In Databricks notebook, use %sh magic command
# MAGIC %sh
# MAGIC chmod +x /tmp/setup_digen.sh
# MAGIC /tmp/setup_digen.sh
```

## Quick Diagnostic Commands

```bash
# Check Java
java -version

# Check DIGen location
ls -la Tools/DIGen.jar

# Check dependencies
ls -la Tools/lib/

# Check classpath
echo $CLASSPATH

# Test DIGen with verbose output
java -cp Tools/DIGen.jar:Tools/lib/commons-cli-1.4.jar -jar Tools/DIGen.jar -h

# Check disk space
df -h

# Check memory
free -h
```

## Getting Help

1. Check TPC-DI specification: https://www.tpc.org/tpcdi/
2. Review script logs for detailed error messages
3. Verify all prerequisites are met
4. Check cluster/node resources (memory, disk, CPU)

## Prevention

To avoid common issues:

1. **Always download dependencies first:**
   ```bash
   ./scripts/fix_digen_dependencies.sh Tools
   ```

2. **Use the provided scripts** which handle dependencies automatically

3. **Check Java version** before running:
   ```bash
   java -version  # Should be 7 or higher
   ```

4. **Verify disk space** for output:
   ```bash
   df -h /output
   ```

5. **Test with small scale factor first:**
   ```bash
   java -cp DIGen.jar:lib/commons-cli-1.4.jar -jar DIGen.jar -o /output/ -sf 0.1
   ```
