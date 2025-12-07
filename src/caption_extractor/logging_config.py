"""Centralized logging configuration for Caption Extractor.

This module provides a unified logging setup that configures both file and console
handlers based on the application configuration. All modules should use this to
ensure consistent logging behavior.
"""

import os
import logging
import sys
from typing import Optional, Dict, Any
from pathlib import Path


def setup_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """Setup logging configuration for the application.
    
    This function configures logging to output to both console and file with
    the same format and level. It should be called once at application startup.
    
    Args:
        config: Configuration dictionary containing logging settings.
                Expected format:
                {
                    'logging': {
                        'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
                        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        'file': 'logs/caption_extractor.log'
                    }
                }
                If None, uses default settings.
    """
    # Extract logging configuration
    log_config = config.get('logging', {}) if config else {}
    log_level = log_config.get('level', 'INFO').upper()
    log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    log_file = log_config.get('file', 'logs/caption_extractor.log')
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level, logging.INFO)
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)
    
    # Remove any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    formatter = logging.Formatter(log_format)
    
    # Create file handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log the initialization
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {log_level}, File: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    This is a convenience function that returns a properly configured logger.
    The logger will inherit settings from the root logger configured by setup_logging().
    
    Args:
        name: Name of the logger (typically __name__ from the calling module)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def reconfigure_logging(level: Optional[str] = None) -> None:
    """Reconfigure logging level at runtime.
    
    This allows changing the logging level without restarting the application.
    
    Args:
        level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    if level:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
        
        logger = logging.getLogger(__name__)
        logger.info(f"Logging level changed to: {level.upper()}")
