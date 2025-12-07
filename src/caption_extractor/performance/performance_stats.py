"""Performance statistics tracking and reporting."""

import os
import time
import logging
import threading
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict
from dataclasses import dataclass, field, asdict


@dataclass
class ModelStats:
    """Statistics for a specific model."""
    model_name: str
    request_count: int = 0
    request_times: List[float] = field(default_factory=list)
    total_time: float = 0.0
    avg_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    
    def add_request(self, processing_time: float):
        """Add a new request timing.
        
        Args:
            processing_time: Time taken to process the request in seconds
        """
        self.request_count += 1
        self.request_times.append(processing_time)
        self.total_time += processing_time
        self.avg_time = self.total_time / self.request_count
        self.min_time = min(self.min_time, processing_time)
        self.max_time = max(self.max_time, processing_time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'model_name': self.model_name,
            'request_count': self.request_count,
            'total_time': round(self.total_time, 3),
            'avg_time': round(self.avg_time, 3),
            'min_time': round(self.min_time, 3) if self.min_time != float('inf') else 0.0,
            'max_time': round(self.max_time, 3),
            'request_times': [round(t, 3) for t in self.request_times]
        }


@dataclass
class RequestTypeStats:
    """Statistics for a specific request type."""
    request_type: str
    total_requests: int = 0
    models: Dict[str, ModelStats] = field(default_factory=dict)
    
    def add_request(self, model_name: str, processing_time: float):
        """Add a request for a specific model.
        
        Args:
            model_name: Name of the model used
            processing_time: Time taken to process the request in seconds
        """
        self.total_requests += 1
        
        if model_name not in self.models:
            self.models[model_name] = ModelStats(model_name=model_name)
        
        self.models[model_name].add_request(processing_time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'request_type': self.request_type,
            'total_requests': self.total_requests,
            'models': {
                model_name: stats.to_dict() 
                for model_name, stats in self.models.items()
            }
        }


class PerformanceStatsManager:
    """Manage performance statistics tracking and reporting."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the performance statistics manager.
        
        Args:
            config: Configuration dictionary
        """
        self.logger = logging.getLogger(__name__)
        self.config = config or {}
        
        # Performance statistics storage
        self.stats: Dict[str, RequestTypeStats] = {}
        self.start_time = time.time()
        
        # Thread safety
        self.lock = threading.Lock()
        
        # Periodic logging configuration
        self.periodic_logging_enabled = False
        self.log_location = None
        self.log_periodicity = 600  # Default 10 minutes
        self.logging_thread = None
        self.stop_logging_event = threading.Event()
        
        # Initialize from config
        self._load_config()
        
        self.logger.info("PerformanceStatsManager initialized")
    
    def _load_config(self):
        """Load performance configuration."""
        perf_config = self.config.get('performance_logging', {})
        
        self.periodic_logging_enabled = perf_config.get('enabled', False)
        self.log_location = perf_config.get('log_location', 'logs/performance')
        self.log_periodicity = perf_config.get('periodicity_seconds', 600)
        
        if self.periodic_logging_enabled:
            self.logger.info(
                f"Periodic performance logging enabled: "
                f"location={self.log_location}, "
                f"periodicity={self.log_periodicity}s"
            )
    
    def track_request(
        self, 
        request_type: str, 
        model_name: str, 
        processing_time: float
    ):
        """Track a request's performance statistics.
        
        Args:
            request_type: Type of request (e.g., 'image', 'text', 'translation', 'ocr')
            model_name: Name of the model used
            processing_time: Time taken to process the request in seconds
        """
        with self.lock:
            if request_type not in self.stats:
                self.stats[request_type] = RequestTypeStats(request_type=request_type)
                self.logger.info(f"Created new request type: {request_type}")
            
            self.stats[request_type].add_request(model_name, processing_time)
            
            self.logger.info(
                f"Tracked request: type={request_type}, "
                f"model={model_name}, time={processing_time:.3f}s, "
                f"total_for_type={self.stats[request_type].total_requests}"
            )
    
    def get_stats(self, request_type: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics.
        
        Args:
            request_type: Specific request type to get stats for (None = all)
            
        Returns:
            Dictionary containing performance statistics
        """
        with self.lock:
            uptime = time.time() - self.start_time
            
            if request_type:
                # Return stats for specific request type
                if request_type not in self.stats:
                    return {
                        'request_type': request_type,
                        'total_requests': 0,
                        'models': {},
                        'uptime_seconds': round(uptime, 2)
                    }
                
                stats_dict = self.stats[request_type].to_dict()
                stats_dict['uptime_seconds'] = round(uptime, 2)
                return stats_dict
            
            # Return all stats
            all_stats = {
                'uptime_seconds': round(uptime, 2),
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'request_types': {}
            }
            
            total_requests = 0
            for req_type, req_stats in self.stats.items():
                all_stats['request_types'][req_type] = req_stats.to_dict()
                total_requests += req_stats.total_requests
            
            all_stats['total_requests'] = total_requests
            
            return all_stats
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of performance statistics.
        
        Returns:
            Dictionary with summary statistics
        """
        with self.lock:
            summary = {
                'uptime_seconds': round(time.time() - self.start_time, 2),
                'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
                'request_types': []
            }
            
            total_requests = 0
            
            for req_type, req_stats in self.stats.items():
                type_summary = {
                    'request_type': req_type,
                    'total_requests': req_stats.total_requests,
                    'models_used': len(req_stats.models),
                    'model_breakdown': []
                }
                
                for model_name, model_stats in req_stats.models.items():
                    type_summary['model_breakdown'].append({
                        'model': model_name,
                        'count': model_stats.request_count,
                        'avg_time': round(model_stats.avg_time, 3),
                        'min_time': round(model_stats.min_time, 3) if model_stats.min_time != float('inf') else 0.0,
                        'max_time': round(model_stats.max_time, 3)
                    })
                
                summary['request_types'].append(type_summary)
                total_requests += req_stats.total_requests
            
            summary['total_requests'] = total_requests
            
            return summary
    
    def save_stats_to_file(self, filepath: Optional[str] = None):
        """Save performance statistics to a YAML file.
        
        Args:
            filepath: Path to save the file (default: use configured location)
        """
        if filepath is None:
            if self.log_location is None:
                self.logger.warning("No log location configured, skipping save")
                return
            
            # Create directory if it doesn't exist
            log_dir = Path(self.log_location)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # Use a single fixed filename that gets overwritten
            filepath = log_dir / "performance_stats.yml"
        
        stats_data = self.get_stats()
        stats_data['saved_at'] = datetime.now().isoformat()
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(stats_data, f, default_flow_style=False, sort_keys=False)
            
            self.logger.info(f"Performance statistics saved to: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save performance statistics: {e}", exc_info=True)
    
    def _periodic_logging_worker(self):
        """Worker function for periodic logging thread."""
        self.logger.info("Periodic performance logging thread started")
        
        while not self.stop_logging_event.wait(self.log_periodicity):
            try:
                self.save_stats_to_file()
            except Exception as e:
                self.logger.error(f"Error in periodic logging: {e}", exc_info=True)
        
        self.logger.info("Periodic performance logging thread stopped")
    
    def start_periodic_logging(self):
        """Start periodic performance logging to file."""
        if not self.periodic_logging_enabled:
            self.logger.info("Periodic logging not enabled in configuration")
            return
        
        if self.logging_thread and self.logging_thread.is_alive():
            self.logger.warning("Periodic logging already running")
            return
        
        self.stop_logging_event.clear()
        self.logging_thread = threading.Thread(
            target=self._periodic_logging_worker,
            daemon=True,
            name="PerformanceLoggingThread"
        )
        self.logging_thread.start()
        
        self.logger.info(
            f"Started periodic performance logging "
            f"(interval: {self.log_periodicity}s)"
        )
    
    def stop_periodic_logging(self):
        """Stop periodic performance logging."""
        if not self.logging_thread or not self.logging_thread.is_alive():
            return
        
        self.logger.info("Stopping periodic performance logging")
        self.stop_logging_event.set()
        
        # Wait for thread to finish (with timeout)
        self.logging_thread.join(timeout=5)
        
        if self.logging_thread.is_alive():
            self.logger.warning("Periodic logging thread did not stop gracefully")
    
    def reset_stats(self):
        """Reset all performance statistics."""
        with self.lock:
            self.stats.clear()
            self.start_time = time.time()
            self.logger.info("Performance statistics reset")
    
    def shutdown(self):
        """Shutdown the performance stats manager."""
        self.logger.info("Shutting down PerformanceStatsManager")
        
        # Stop periodic logging
        self.stop_periodic_logging()
        
        # Save final stats
        if self.periodic_logging_enabled:
            self.save_stats_to_file()
        
        self.logger.info("PerformanceStatsManager shutdown complete")
