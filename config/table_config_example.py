"""
Example table configurations for TPC-DI benchmark

This file demonstrates how to configure tables for the TPC-DI benchmark.
Copy and modify these configurations in src/main.py based on your data structure.
"""
from pyspark.sql.functions import sum, avg, count, upper, trim, col, to_date
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, DateType

# Example: Simple dimension table
DIM_DATE_CONFIG = {
    "file_name": "Date.txt",
    "format": "csv",
    "options": {
        "header": "true",
        "delimiter": "|",
        "inferSchema": "true"
    }
}

# Example: Fact table with transformations and aggregations
FACT_SALES_CONFIG = {
    "file_name": "Sales.txt",
    "format": "csv",
    "timestamp_column": "UpdateDate",  # Required for incremental loads
    "options": {
        "header": "true",
        "delimiter": "|"
    },
    "transformations": {
        # Custom transformations for Silver layer
        "Amount": lambda x: x.cast("decimal(18,2)"),
        "Status": lambda x: upper(trim(x))
    },
    "validation_rules": {
        # Validation rules for Silver layer
        "Amount": lambda col: col > 0,
        "DateKey": lambda col: col.isNotNull()
    },
    "gold_config": {
        "aggregate": {
            "group_by": ["DateKey", "ProductKey"],
            "aggregations": {
                "Amount": sum,
                "Quantity": sum,
                "Price": avg
            }
        }
    }
}

# Example: Table with custom schema
CUSTOM_TABLE_CONFIG = {
    "file_name": "CustomTable.txt",
    "format": "csv",
    "schema": StructType([
        StructField("ID", IntegerType(), True),
        StructField("Name", StringType(), True),
        StructField("Amount", DecimalType(18, 2), True),
        StructField("Date", DateType(), True)
    ]),
    "options": {
        "header": "true",
        "delimiter": ","
    }
}

# Example: Table with enrichment function
ENRICHED_TABLE_CONFIG = {
    "file_name": "BaseTable.txt",
    "format": "csv",
    "options": {
        "header": "true",
        "delimiter": "|"
    },
    "gold_config": {
        "enrich": lambda df: df.withColumn(
            "EnrichedColumn",
            col("BaseColumn") * 1.1
        )
    }
}

# Complete example table_configs dictionary
EXAMPLE_TABLE_CONFIGS = {
    "DimDate": DIM_DATE_CONFIG,
    "FactSales": FACT_SALES_CONFIG,
    "CustomTable": CUSTOM_TABLE_CONFIG,
    "EnrichedTable": ENRICHED_TABLE_CONFIG
}
