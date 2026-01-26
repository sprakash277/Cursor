"""
Benchmark script to compare Databricks vs Dataproc performance on TPC-DI queries
"""

import time
import json
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
from databricks import sql
from google.cloud import dataproc_v1
from google.cloud import storage
from pyspark.sql import SparkSession
import pandas as pd


class BenchmarkRunner:
    """Run benchmarks on Databricks and Dataproc"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize benchmark runner with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.results = []
        
    def run_databricks_query(self, query: str, query_name: str) -> Dict[str, Any]:
        """
        Execute a query on Databricks and measure performance
        
        Args:
            query: SQL query to execute
            query_name: Name of the query
            
        Returns:
            Dictionary with performance metrics
        """
        print(f"\n{'='*60}")
        print(f"Running {query_name} on Databricks...")
        print(f"{'='*60}")
        
        workspace_url = self.config['databricks']['workspace_url']
        token = self.config['databricks']['token']
        catalog = self.config['databricks']['catalog']
        schema = self.config['databricks']['schema']
        
        # Replace schema references in query
        query = query.replace('${catalog}', catalog).replace('${schema}', schema)
        
        start_time = time.time()
        
        try:
            with sql.connect(
                server_hostname=workspace_url.replace('https://', ''),
                http_path=f"/sql/1.0/warehouses/{self.config['databricks'].get('warehouse_id', '')}",
                access_token=token
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(query)
                    results = cursor.fetchall()
                    
                    execution_time = time.time() - start_time
                    
                    # Get query execution details (if available)
                    metrics = {
                        'platform': 'Databricks',
                        'query_name': query_name,
                        'execution_time_seconds': execution_time,
                        'rows_returned': len(results),
                        'timestamp': datetime.now().isoformat(),
                        'status': 'success'
                    }
                    
                    print(f"✓ Query completed in {execution_time:.2f} seconds")
                    print(f"  Rows returned: {len(results)}")
                    
                    return metrics
                    
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"✗ Query failed: {str(e)}")
            return {
                'platform': 'Databricks',
                'query_name': query_name,
                'execution_time_seconds': execution_time,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'failed'
            }
    
    def run_dataproc_query(self, query: str, query_name: str) -> Dict[str, Any]:
        """
        Execute a query on Dataproc and measure performance
        
        Args:
            query: SQL query to execute
            query_name: Name of the query
            
        Returns:
            Dictionary with performance metrics
        """
        print(f"\n{'='*60}")
        print(f"Running {query_name} on Dataproc...")
        print(f"{'='*60}")
        
        project_id = self.config['dataproc']['project_id']
        region = self.config['dataproc']['region']
        cluster_name = self.config['dataproc']['cluster_name']
        bucket_name = self.config['dataproc']['bucket_name']
        
        start_time = time.time()
        
        try:
            # Initialize Spark session on Dataproc
            spark = SparkSession.builder \
                .appName(f"TPC-DI-Benchmark-{query_name}") \
                .getOrCreate()
            
            # Execute query
            result_df = spark.sql(query)
            results = result_df.collect()
            
            execution_time = time.time() - start_time
            
            metrics = {
                'platform': 'Dataproc',
                'query_name': query_name,
                'execution_time_seconds': execution_time,
                'rows_returned': len(results),
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }
            
            print(f"✓ Query completed in {execution_time:.2f} seconds")
            print(f"  Rows returned: {len(results)}")
            
            spark.stop()
            
            return metrics
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"✗ Query failed: {str(e)}")
            return {
                'platform': 'Dataproc',
                'query_name': query_name,
                'execution_time_seconds': execution_time,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'failed'
            }
    
    def load_query(self, query_path: str) -> str:
        """Load SQL query from file"""
        with open(query_path, 'r') as f:
            return f.read()
    
    def run_benchmark(self, num_iterations: int = 3):
        """
        Run all benchmark queries on both platforms
        
        Args:
            num_iterations: Number of times to run each query (for averaging)
        """
        print("\n" + "="*60)
        print("TPC-DI Benchmark: Databricks vs Dataproc")
        print("="*60)
        
        queries = self.config['benchmark']['queries']
        
        for query_config in queries:
            query_name = query_config['name']
            query_file = query_config.get('sql_file', f'queries/{query_name}.sql')
            
            if not Path(query_file).exists():
                print(f"Warning: Query file {query_file} not found, skipping...")
                continue
            
            query = self.load_query(query_file)
            
            # Run on Databricks
            databricks_results = []
            for i in range(num_iterations):
                print(f"\nIteration {i+1}/{num_iterations} on Databricks...")
                result = self.run_databricks_query(query, query_name)
                databricks_results.append(result)
                time.sleep(2)  # Brief pause between runs
            
            # Run on Dataproc
            dataproc_results = []
            for i in range(num_iterations):
                print(f"\nIteration {i+1}/{num_iterations} on Dataproc...")
                result = self.run_dataproc_query(query, query_name)
                dataproc_results.append(result)
                time.sleep(2)  # Brief pause between runs
            
            # Calculate averages
            db_avg_time = sum(r['execution_time_seconds'] for r in databricks_results if r['status'] == 'success') / len([r for r in databricks_results if r['status'] == 'success'])
            dp_avg_time = sum(r['execution_time_seconds'] for r in dataproc_results if r['status'] == 'success') / len([r for r in dataproc_results if r['status'] == 'success'])
            
            self.results.append({
                'query': query_name,
                'databricks': {
                    'avg_time': db_avg_time,
                    'results': databricks_results
                },
                'dataproc': {
                    'avg_time': dp_avg_time,
                    'results': dataproc_results
                },
                'speedup': dp_avg_time / db_avg_time if db_avg_time > 0 else 0
            })
    
    def generate_report(self, output_path: str = "benchmark_results.json"):
        """Generate benchmark report"""
        print("\n" + "="*60)
        print("Benchmark Results Summary")
        print("="*60)
        
        for result in self.results:
            print(f"\nQuery: {result['query']}")
            print(f"  Databricks avg: {result['databricks']['avg_time']:.2f}s")
            print(f"  Dataproc avg:   {result['dataproc']['avg_time']:.2f}s")
            print(f"  Speedup:        {result['speedup']:.2f}x")
        
        # Save detailed results
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nDetailed results saved to: {output_path}")
        
        # Generate comparison DataFrame
        df_data = []
        for result in self.results:
            df_data.append({
                'Query': result['query'],
                'Databricks (s)': result['databricks']['avg_time'],
                'Dataproc (s)': result['dataproc']['avg_time'],
                'Speedup': f"{result['speedup']:.2f}x"
            })
        
        df = pd.DataFrame(df_data)
        print("\n" + df.to_string(index=False))
        
        # Save CSV
        csv_path = output_path.replace('.json', '.csv')
        df.to_csv(csv_path, index=False)
        print(f"\nSummary CSV saved to: {csv_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run TPC-DI benchmark")
    parser.add_argument("--config", default="config.yaml", help="Config file path")
    parser.add_argument("--iterations", type=int, default=3, help="Number of iterations per query")
    
    args = parser.parse_args()
    
    runner = BenchmarkRunner(args.config)
    runner.run_benchmark(args.iterations)
    runner.generate_report()
