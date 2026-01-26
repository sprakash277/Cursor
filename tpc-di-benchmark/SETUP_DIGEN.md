# Setting Up TPC-DI DIGen Tool

This guide explains how to set up and use the official TPC-DI DIGen tool for data generation.

## Prerequisites

- Java 7 or higher (Java 8+ recommended)
- Python 3.8+ (for the wrapper script)
- Access to download TPC-DI tools from TPC.org

## Step 1: Download TPC-DI Tools

1. Visit the TPC website:
   https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp

2. Find and download the **TPCDI_Tools** zip file (usually under TPC-DI v1.1.0)

3. Extract the zip file:
   ```bash
   unzip TPCDI_Tools.zip
   cd Tools
   ```

## Step 2: Fix PDGF Directory

The DIGen tool requires the PDGF directory to be lowercase. After extraction:

```bash
cd Tools
mv PDGF pdgf
```

**Important**: This step is required! The tool will fail if the directory is named `PDGF` instead of `pdgf`.

## Step 3: Verify Setup

Check that you have:
- `DIGen.jar` in the Tools directory
- `pdgf/` directory (lowercase) in the Tools directory
- Java installed and accessible

Test Java:
```bash
java -version
```

Test DIGen:
```bash
cd Tools
java -jar DIGen.jar -h
```

You should see help output with available options.

## Step 4: Generate Data

### Using the Python Wrapper (Recommended)

```bash
python tpcdi_digen_wrapper.py \
    --digen-path ./Tools/DIGen.jar \
    --scale-factor 1 \
    --output-dir ./tpcdi_data \
    --generate-notebook
```

### Using DIGen Directly

```bash
cd Tools
java -jar DIGen.jar -o ../tpcdi_data/ -sf 1
```

**Options:**
- `-o <directory>`: Output directory (required)
- `-sf <number>`: Scale factor (required)
- `-h`: Show help

**Scale Factor Guide:**
- SF=1: ~1GB of data
- SF=10: ~10GB of data
- SF=100: ~100GB of data

## Step 5: Verify Generated Data

After generation, you should see files like:
- `Date.txt`
- `Time.txt`
- `Customer.txt`
- `Security.txt`
- `DailyMarket.txt`
- `Trade.txt`
- And other TPC-DI files

Check the output directory:
```bash
ls -lh tpcdi_data/
```

## Troubleshooting

### "PDGF directory not found"
- Make sure you renamed `PDGF` to `pdgf` (lowercase)
- The `pdgf` directory must be in the same directory as `DIGen.jar`

### "Java not found"
- Install Java 7 or higher
- Make sure `java` is in your PATH
- Try: `which java` to verify

### "DIGen.jar not found"
- Make sure you're running from the Tools directory
- Or specify the full path: `--digen-path /full/path/to/DIGen.jar`

### Generation takes too long
- Large scale factors take significant time
- SF=1 typically takes a few minutes
- SF=10 can take 30+ minutes
- Monitor disk space - large scale factors require significant storage

### Out of memory errors
- Increase Java heap size:
  ```bash
  java -Xmx4g -jar DIGen.jar -o output/ -sf 1
  ```
- Adjust `-Xmx` based on available RAM

## Next Steps

After generating data:
1. Upload to Databricks (see main README)
2. Load into tables using the generated notebook
3. Run benchmarks

## References

- [TPC-DI Specification](https://www.tpc.org/tpc_documents_current_versions/current_specifications5.asp)
- [TPC-DI Documentation](https://www.tpc.org/tpcdi/)
