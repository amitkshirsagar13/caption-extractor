"""Configuration management for Caption Extractor."""

import os
import yaml
import logging
from typing import Dict, Any, List

from .logging_config import setup_logging


class ConfigManager:
    """Manages configuration loading and validation."""
    
    def __init__(self, config_path: str = "config.yml"):
        """Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._setup_logging()
        self._create_directories()
        self.logger = logging.getLogger(__name__)
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file.
        
        Returns:
            Configuration dictionary
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        try:
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                return config
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Error parsing configuration file: {e}")
    
    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        # Use centralized logging configuration
        setup_logging(self.config)
    
    def _create_directories(self) -> None:
        """Create necessary directories based on configuration."""
        logger = logging.getLogger(__name__)
        
        # Create model directory
        model_dir = self.get_model_dir()
        os.makedirs(model_dir, exist_ok=True)
        logger.debug(f"Model directory created/verified: {model_dir}")
        
        # Create data directory if it doesn't exist
        data_dir = self.get_input_folder()
        os.makedirs(data_dir, exist_ok=True)
        logger.debug(f"Data directory created/verified: {data_dir}")
        
        # Create logs directory (guard empty paths)
        log_file = self.config.get('logging', {}).get('file', 'logs/caption_extractor.log')
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
            logger.debug(f"Logs directory created/verified: {log_dir}")
    
    def get_model_dir(self) -> str:
        """Get model storage directory."""
        return self.config.get('model', {}).get('model_dir', 'models')
    
    def get_input_folder(self) -> str:
        """Get input folder path."""
        return self.config.get('data', {}).get('input_folder', 'data')
    
    def get_supported_formats(self) -> List[str]:
        """Get supported image formats."""
        return self.config.get('data', {}).get('supported_formats', ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'])
    
    def get_num_threads(self) -> int:
        """Get number of processing threads."""
        return self.config.get('processing', {}).get('num_threads', 4)
    def get_batch_size(self) -> int:
        """Get batch size for processing."""
        return self.config.get('processing', {}).get('batch_size', 10)
    
    def is_progress_enabled(self) -> bool:
        """Check if progress display is enabled."""
        return self.config.get('processing', {}).get('show_progress', True)
    
    def is_timing_enabled(self) -> bool:
        """Check if timing is enabled."""
        return self.config.get('processing', {}).get('enable_timing', True)
    
    def get_ocr_config(self) -> Dict[str, Any]:
        """Get OCR configuration."""
        return self.config.get('model', {})
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration."""
        return self.config.get('performance', {})

    def get_image_resize_spec(self) -> Dict[str, Any]:
        """Get image resize specification for the image agent.

        Returns a dictionary with keys:
            - enabled: bool (whether to resize before sending to image agent)
            - max_size: [width, height]
            - keep_aspect: bool (retain aspect ratio)
            - interpolation: str (one of 'area', 'linear', 'cubic')

        Defaults to resizing to 1024x1024 while keeping aspect ratio.
        """
        pipeline = self.config.get('pipeline', {})
        default = {
            'enabled': True,
            'max_size': [1024, 1024],
            'keep_aspect': True,
            'interpolation': 'area'
        }
        return pipeline.get('image_resize', default)