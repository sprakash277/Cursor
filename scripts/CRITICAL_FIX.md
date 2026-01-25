# CRITICAL FIX: Java -jar ignores -cp option!

## The Problem

When you use `java -jar`, Java **IGNORES** the `-cp` or `-classpath` option! This is why you're still getting `NoClassDefFoundError` even though you included the commons-cli JAR in the classpath.

## The Solution

**DO NOT use `-jar` when you need external dependencies!**

Instead:
1. Extract the Main-Class from the JAR manifest
2. Use `-cp` WITHOUT `-jar`
3. Specify the main class explicitly

## Correct Command

```bash
# Extract Main-Class from manifest
MAIN_CLASS=$(unzip -p DIGen.jar META-INF/MANIFEST.MF | grep -i "Main-Class:" | cut -d' ' -f2 | tr -d '\r')

# If not found, use the wrapper class (common for Eclipse JARs)
if [ -z "$MAIN_CLASS" ]; then
  MAIN_CLASS="org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"
fi

# Run with -cp (NOT -jar) to include dependencies
java -Xmx4g -cp "DIGen.jar:commons-cli-1.4.jar" $MAIN_CLASS -o /output/ -sf 1
```

## For Your Specific Case

Based on your paths, use this:

```bash
cd /Volumes/users/sumit_prakash/tpcdi/zip_file/Tools/

# Extract main class
MAIN_CLASS=$(unzip -p DIGen.jar META-INF/MANIFEST.MF | grep -i "Main-Class:" | cut -d' ' -f2 | tr -d '\r')
if [ -z "$MAIN_CLASS" ]; then
  MAIN_CLASS="org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"
fi

# Build classpath with absolute paths
CLASSPATH="/Volumes/users/sumit_prakash/tpcdi/zip_file/Tools/DIGen.jar:/Volumes/users/sumit_prakash/tpcdi/zip_file/commons-cli-1.4.jar"

# Run WITHOUT -jar
java -Xmx4g -cp "$CLASSPATH" $MAIN_CLASS -o /Volumes/users/sumit_prakash/tpcdi/zip_file/output/ -sf 1
```

## Quick Fix Script

Use the provided script:

```bash
./scripts/run_digen_correct.sh \
  /Volumes/users/sumit_prakash/tpcdi/zip_file/Tools \
  /Volumes/users/sumit_prakash/tpcdi/zip_file/output \
  1 \
  /Volumes/users/sumit_prakash/tpcdi/zip_file/commons-cli-1.4.jar
```

## In Databricks Notebook

```python
# MAGIC %sh
# MAGIC cd /dbfs/tmp/tpc-di-setup/Tools
# MAGIC 
# MAGIC # Extract main class
# MAGIC MAIN_CLASS=$(unzip -p DIGen.jar META-INF/MANIFEST.MF | grep -i "Main-Class:" | cut -d' ' -f2 | tr -d '\r')
# MAGIC if [ -z "$MAIN_CLASS" ]; then
# MAGIC   MAIN_CLASS="org.eclipse.jdt.internal.jarinjarloader.JarRsrcLoader"
# MAGIC fi
# MAGIC 
# MAGIC # Build classpath
# MAGIC CLASSPATH="DIGen.jar:lib/commons-cli-1.4.jar"
# MAGIC 
# MAGIC # Run WITHOUT -jar
# MAGIC java -Xmx4g -cp "$CLASSPATH" $MAIN_CLASS -o /dbfs/tmp/tpc-di-setup/output/ -sf 1
```

## Why This Happens

Java's `-jar` option:
- Reads the Main-Class from META-INF/MANIFEST.MF
- Uses ONLY the JAR file itself in the classpath
- **IGNORES** any `-cp` or `-classpath` options you specify

To include external dependencies, you must:
- Use `-cp` (not `-jar`)
- Specify the main class explicitly
- Include all JARs in the classpath

## Verification

After running, verify it worked:
```bash
ls -lh /output/*.txt
```

You should see generated TPC-DI data files.
