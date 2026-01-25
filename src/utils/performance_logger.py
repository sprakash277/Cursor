"""
Performance logging utilities for measuring throughput and stage performance
"""
import time
import logging
from datetime import datetime
from typing import Dict, Optional
from functools import wraps
from pyspark.sql import DataFrame


class PerformanceLogger:
    """Logger for tracking performance metrics"""
    
    def __init__(self, log_path: Optional[str] = None, log_level: str = "INFO"):
        """
        Initialize performance logger
        
        Args:
            log_path: Path to log file (optional)
            log_level: Logging level
        """
        self.logger = logging.getLogger("PerformanceLogger")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if path provided
        if log_path:
            file_handler = logging.FileHandler(log_path)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        self.metrics: Dict[str, Dict] = {}
    
    def log_stage_start(self, stage_name: str, additional_info: Optional[Dict] = None):
        """
        Log the start of a processing stage
        
        Args:
            stage_name: Name of the stage
            additional_info: Additional information to log
        """
        self.metrics[stage_name] = {
            'start_time': time.time(),
            'start_datetime': datetime.now().isoformat(),
            'additional_info': additional_info or {}
        }
        self.logger.info(f"Stage '{stage_name}' started at {self.metrics[stage_name]['start_datetime']}")
        if additional_info:
            self.logger.info(f"Stage '{stage_name}' info: {additional_info}")
    
    def log_stage_end(self, stage_name: str, record_count: Optional[int] = None, 
                     data_size_mb: Optional[float] = None, 
                     additional_info: Optional[Dict] = None):
        """
        Log the end of a processing stage with performance metrics
        
        Args:
            stage_name: Name of the stage
            record_count: Number of records processed
            data_size_mb: Size of data processed in MB
            additional_info: Additional information to log
        """
        if stage_name not in self.metrics:
            self.logger.warning(f"Stage '{stage_name}' end logged without start")
            return
        
        end_time = time.time()
        duration = end_time - self.metrics[stage_name]['start_time']
        
        self.metrics[stage_name].update({
            'end_time': end_time,
            'end_datetime': datetime.now().isoformat(),
            'duration_seconds': duration,
            'record_count': record_count,
            'data_size_mb': data_size_mb
        })
        
        if additional_info:
            self.metrics[stage_name]['additional_info'].update(additional_info)
        
        # Calculate throughput
        throughput_info = {}
        if record_count:
            throughput_info['records_per_second'] = record_count / duration if duration > 0 else 0
        if data_size_mb:
            throughput_info['mb_per_second'] = data_size_mb / duration if duration > 0 else 0
        
        self.logger.info(
            f"Stage '{stage_name}' completed in {duration:.2f} seconds"
        )
        if record_count:
            self.logger.info(
                f"Stage '{stage_name}' processed {record_count:,} records "
                f"({throughput_info.get('records_per_second', 0):,.2f} records/sec)"
            )
        if data_size_mb:
            self.logger.info(
                f"Stage '{stage_name}' processed {data_size_mb:.2f} MB "
                f"({throughput_info.get('mb_per_second', 0):.2f} MB/sec)"
            )
        
        self.metrics[stage_name].update(throughput_info)
    
    def log_dataframe_info(self, stage_name: str, df: DataFrame):
        """
        Log DataFrame information and update metrics
        
        Args:
            stage_name: Name of the stage
            df: PySpark DataFrame
        """
        try:
            record_count = df.count()
            # Estimate size (rough calculation)
            schema_size = sum([field.dataType.simpleString() for field in df.schema.fields])
            estimated_size_mb = (record_count * schema_size) / (1024 * 1024)  # Rough estimate
            
            self.log_dataframe_info_detailed(stage_name, df, record_count, estimated_size_mb)
        except Exception as e:
            self.logger.warning(f"Could not log DataFrame info for '{stage_name}': {str(e)}")
    
    def log_dataframe_info_detailed(self, stage_name: str, df: DataFrame, 
                                   record_count: int, data_size_mb: float):
        """
        Log detailed DataFrame information
        
        Args:
            stage_name: Name of the stage
            df: PySpark DataFrame
            record_count: Number of records
            data_size_mb: Estimated size in MB
        """
        self.logger.info(f"DataFrame '{stage_name}' schema: {df.schema}")
        self.logger.info(
            f"DataFrame '{stage_name}': {record_count:,} records, "
            f"estimated size: {data_size_mb:.2f} MB"
        )
    
    def get_metrics_summary(self) -> Dict:
        """
        Get summary of all logged metrics
        
        Returns:
            Dictionary containing all metrics
        """
        return self.metrics
    
    def print_summary(self):
        """Print a formatted summary of all metrics"""
        self.logger.info("=" * 80)
        self.logger.info("PERFORMANCE SUMMARY")
        self.logger.info("=" * 80)
        
        for stage_name, metrics in self.metrics.items():
            self.logger.info(f"\nStage: {stage_name}")
            self.logger.info(f"  Duration: {metrics.get('duration_seconds', 0):.2f} seconds")
            if metrics.get('record_count'):
                self.logger.info(f"  Records: {metrics['record_count']:,}")
                self.logger.info(
                    f"  Throughput: {metrics.get('records_per_second', 0):,.2f} records/sec"
                )
            if metrics.get('data_size_mb'):
                self.logger.info(f"  Data Size: {metrics['data_size_mb']:.2f} MB")
                self.logger.info(
                    f"  Data Throughput: {metrics.get('mb_per_second', 0):.2f} MB/sec"
                )
        
        self.logger.info("=" * 80)


def measure_performance(perf_logger: PerformanceLogger, stage_name: str):
    """
    Decorator to measure performance of a function
    
    Args:
        perf_logger: PerformanceLogger instance
        stage_name: Name of the stage
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            perf_logger.log_stage_start(stage_name)
            try:
                result = func(*args, **kwargs)
                # Try to get record count if result is a DataFrame
                record_count = None
                data_size_mb = None
                if isinstance(result, DataFrame):
                    record_count = result.count()
                perf_logger.log_stage_end(stage_name, record_count, data_size_mb)
                return result
            except Exception as e:
                perf_logger.logger.error(f"Stage '{stage_name}' failed: {str(e)}")
                raise
        return wrapper
    return decorator
