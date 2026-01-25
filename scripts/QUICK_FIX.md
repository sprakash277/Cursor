# Quick Fix: NoClassDefFoundError for Apache Commons CLI

## The Problem

When running DIGen, you may see:
```
Exception in thread "main" java.lang.NoClassDefFoundError: org/apache/commons/cli/ParseException
```

## The Solution

DIGen requires Apache Commons CLI on the classpath. The updated scripts now automatically download and include this dependency.

### Automatic Fix (Recommended)

The scripts (`setup_and_run_digen.sh` and `setup_and_run_digen_databricks.sh`) now automatically:
1. Download Apache Commons CLI from Maven Central
2. Add it to the classpath when running DIGen
3. Handle the dependency transparently

Just run the scripts as normal - they'll handle it automatically!

### Manual Fix

If you need to fix it manually:

```bash
# 1. Create lib directory
mkdir -p Tools/lib

# 2. Download Apache Commons CLI
cd Tools/lib
curl -L -o commons-cli-1.4.jar \
  https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar

# 3. Run DIGen with classpath
cd ..
java -cp DIGen.jar:lib/commons-cli-1.4.jar -jar DIGen.jar -o /output/ -sf 1
```

### Using the Fix Script

```bash
# Run the dedicated fix script
./scripts/fix_digen_dependencies.sh /path/to/Tools

# Then run DIGen normally (script will use classpath)
```

### In Databricks Notebook

```python
# MAGIC %sh
# MAGIC # Download dependency
# MAGIC mkdir -p /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools/lib
# MAGIC curl -L -o commons-cli-1.4.jar https://repo1.maven.org/maven2/commons-cli/commons-cli/1.4/commons-cli-1.4.jar
# MAGIC 
# MAGIC # Run with classpath
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools
# MAGIC CLASSPATH="DIGen.jar:lib/commons-cli-1.4.jar"
# MAGIC java -Xmx4g -cp "$CLASSPATH" -jar DIGen.jar -o /dbfs/tmp/tpc-di-setup/output/ -sf 1
```

## What Changed

The updated scripts now:
- ✅ Automatically download Apache Commons CLI if missing
- ✅ Build proper classpath with dependencies
- ✅ Try multiple execution methods for compatibility
- ✅ Provide clear error messages if download fails

## Verification

After running, verify the dependency is present:
```bash
ls -la Tools/lib/commons-cli-*.jar
```

You should see:
```
commons-cli-1.4.jar
```

## Still Having Issues?

See `TROUBLESHOOTING.md` for more detailed solutions.
