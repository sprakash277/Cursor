#!/usr/bin/env python3
"""Temporary script to read Excel file structure"""
import sys
try:
    import pandas as pd
    df = pd.read_excel('/Users/sumit.prakash/Downloads/sanskriti-2.xlsx')
    print("Columns:", df.columns.tolist())
    print("\nShape:", df.shape)
    print("\nFirst 10 rows:")
    print(df.head(10).to_string())
    print("\nUnique values in each column:")
    for col in df.columns:
        unique_vals = df[col].dropna().unique()[:10]
        print(f"{col}: {len(df[col].dropna().unique())} unique values, sample: {list(unique_vals)}")
except ImportError:
    print("pandas not installed. Please install: pip install pandas openpyxl")
    sys.exit(1)
except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
