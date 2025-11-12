"""Tests for ConfigManager class."""

import unittest
import tempfile
import os
import yaml
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from caption_extractor.config_manager import ConfigManager


class TestConfigManager(unittest.TestCase):
    """Test cases for ConfigManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yml')
        
        # Create a test configuration
        self.test_config = {
            'logging': {
                'level': 'DEBUG',
                'format': '%(asctime)s - %(message)s',
                'file': 'test.log'
            },
            'model': {
                'model_dir': 'test_models',
                'use_gpu': False,
                'lang': 'en'
            },
            'data': {
                'input_folder': 'test_data',
                'supported_formats': ['.jpg', '.png']
            },
            'processing': {
                'num_threads': 2,
                'show_progress': False,
                'enable_timing': True
            }
        }
        
        # Write test config to file
        with open(self.config_file, 'w') as f:
            yaml.dump(self.test_config, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_manager = ConfigManager(self.config_file)
        self.assertIsNotNone(config_manager.config)
        self.assertEqual(config_manager.get_num_threads(), 2)
        self.assertEqual(config_manager.get_input_folder(), 'test_data')
    
    def test_get_model_dir(self):
        """Test getting model directory."""
        config_manager = ConfigManager(self.config_file)
        self.assertEqual(config_manager.get_model_dir(), 'test_models')
    
    def test_get_supported_formats(self):
        """Test getting supported image formats."""
        config_manager = ConfigManager(self.config_file)
        formats = config_manager.get_supported_formats()
        self.assertEqual(formats, ['.jpg', '.png'])
    
    def test_get_ocr_config(self):
        """Test getting OCR configuration."""
        config_manager = ConfigManager(self.config_file)
        ocr_config = config_manager.get_ocr_config()
        self.assertIn('model_dir', ocr_config)
        self.assertEqual(ocr_config['use_gpu'], False)
    
    def test_missing_config_file(self):
        """Test handling of missing configuration file."""
        with self.assertRaises(FileNotFoundError):
            ConfigManager('nonexistent_config.yml')
    
    def test_invalid_yaml_config(self):
        """Test handling of invalid YAML configuration."""
        invalid_config_file = os.path.join(self.temp_dir, 'invalid.yml')
        with open(invalid_config_file, 'w') as f:
            f.write('invalid: yaml: content: [')
        
        with self.assertRaises(yaml.YAMLError):
            ConfigManager(invalid_config_file)


if __name__ == '__main__':
    unittest.main()