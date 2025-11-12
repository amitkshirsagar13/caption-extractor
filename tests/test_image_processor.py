"""Tests for ImageProcessor class."""

import unittest
import tempfile
import os
import yaml
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from caption_extractor.config_manager import ConfigManager
from caption_extractor.image_processor import ImageProcessor
from caption_extractor.ocr_processor import OCRProcessor


class TestImageProcessor(unittest.TestCase):
    """Test cases for ImageProcessor."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        
        # Create test configuration
        self.config_file = os.path.join(self.temp_dir, 'test_config.yml')
        test_config = {
            'logging': {'level': 'INFO', 'format': '%(message)s', 'file': 'test.log'},
            'model': {'model_dir': 'test_models', 'use_gpu': False, 'lang': 'en'},
            'data': {
                'input_folder': os.path.join(self.temp_dir, 'test_images'),
                'supported_formats': ['.jpg', '.png', '.txt']  # Include .txt for testing
            },
            'processing': {'num_threads': 2, 'show_progress': False, 'enable_timing': True},
            'performance': {'max_image_size': [1024, 1024], 'auto_resize': True}
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Create test image directory
        self.test_images_dir = os.path.join(self.temp_dir, 'test_images')
        os.makedirs(self.test_images_dir, exist_ok=True)
        
        # Create mock files for testing (not actual images, just for file discovery)
        self.test_files = [
            'image1.jpg',
            'image2.png', 
            'document.txt',
            'image3.JPG',  # Test case sensitivity
        ]
        
        for filename in self.test_files:
            file_path = os.path.join(self.test_images_dir, filename)
            with open(file_path, 'w') as f:
                f.write('test content')
        
        # Setup config manager and mocks
        self.config_manager = ConfigManager(self.config_file)
        self.mock_ocr_processor = Mock(spec=OCRProcessor)
        
        # Setup image processor
        self.image_processor = ImageProcessor(self.config_manager, self.mock_ocr_processor)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_image_files(self):
        """Test getting image files from directory."""
        image_files = self.image_processor.get_image_files(self.test_images_dir)
        
        # Should find .jpg, .png, .txt files (all in supported_formats)
        self.assertEqual(len(image_files), 4)
        
        # Check that files are sorted
        self.assertTrue(all(image_files[i] <= image_files[i+1] for i in range(len(image_files)-1)))
    
    def test_get_image_files_nonexistent_folder(self):
        """Test getting image files from non-existent directory."""
        image_files = self.image_processor.get_image_files('/nonexistent/path')
        self.assertEqual(len(image_files), 0)
    
    def test_get_image_files_empty_folder(self):
        """Test getting image files from empty directory."""
        empty_dir = os.path.join(self.temp_dir, 'empty')
        os.makedirs(empty_dir, exist_ok=True)
        
        image_files = self.image_processor.get_image_files(empty_dir)
        self.assertEqual(len(image_files), 0)
    
    @patch('time.time')
    def test_process_single_image_success(self, mock_time):
        """Test successful processing of a single image."""
        # Setup time mock
        mock_time.side_effect = [1000.0, 1001.5]  # 1.5 second processing time
        
        # Setup OCR processor mock
        mock_extracted_data = [
            {'text': 'Sample text', 'confidence': 0.95, 'bbox': [[0, 0], [100, 0], [100, 20], [0, 20]]}
        ]
        self.mock_ocr_processor.extract_text.return_value = mock_extracted_data
        self.mock_ocr_processor.format_extracted_text.return_value = {
            'text_lines': [{'text': 'Sample text', 'confidence': 0.95, 'bbox': [[0, 0], [100, 0], [100, 20], [0, 20]]}],
            'full_text': 'Sample text',
            'total_elements': 1,
            'avg_confidence': 0.95
        }
        
        # Test image file
        test_image = os.path.join(self.test_images_dir, 'image1.jpg')
        
        # Process image
        result = self.image_processor.process_single_image(test_image)
        
        # Verify result
        image_path, success, processing_time, result_data = result
        self.assertEqual(image_path, test_image)
        self.assertTrue(success)
        self.assertEqual(processing_time, 1.5)
        self.assertIn('image_file', result_data)
        self.assertIn('full_text', result_data)
        
        # Verify YAML file was created
        yaml_file = os.path.join(self.test_images_dir, 'image1.yml')
        self.assertTrue(os.path.exists(yaml_file))
    
    @patch('time.time')
    def test_process_single_image_failure(self, mock_time):
        """Test handling of processing failure."""
        # Setup time mock
        mock_time.side_effect = [1000.0, 1000.5]  # 0.5 second processing time
        
        # Setup OCR processor mock to raise exception
        self.mock_ocr_processor.extract_text.side_effect = Exception("OCR failed")
        
        # Test image file
        test_image = os.path.join(self.test_images_dir, 'image1.jpg')
        
        # Process image
        result = self.image_processor.process_single_image(test_image)
        
        # Verify result
        image_path, success, processing_time, result_data = result
        self.assertEqual(image_path, test_image)
        self.assertFalse(success)
        self.assertEqual(processing_time, 0.5)
        self.assertIn('error', result_data)
    
    def test_get_processing_report_empty(self):
        """Test getting processing report with no processed images."""
        report = self.image_processor.get_processing_report()
        
        self.assertEqual(report['summary']['total_images'], 0)
        self.assertEqual(report['summary']['processed_images'], 0)
        self.assertEqual(report['timing']['average_time_per_image'], 0.0)
    
    def test_update_stats(self):
        """Test updating processing statistics."""
        # Update stats with successful processing
        self.image_processor._update_stats('test.jpg', True, 1.5)
        
        # Update stats with failed processing
        self.image_processor._update_stats('test2.jpg', False, 0.8, "Error message")
        
        # Check stats
        stats = self.image_processor.processing_stats
        self.assertEqual(stats['processed_images'], 2)
        self.assertEqual(stats['failed_images'], 1)
        self.assertEqual(len(stats['processing_times']), 2)
        self.assertEqual(len(stats['errors']), 1)
    
    def test_save_result_to_yaml(self):
        """Test saving result to YAML file."""
        test_image = os.path.join(self.test_images_dir, 'test_save.jpg')
        
        # Create test image file
        with open(test_image, 'w') as f:
            f.write('test')
        
        # Test data
        result_data = {
            'image_file': 'test_save.jpg',
            'text_lines': [{'text': 'Sample', 'confidence': 0.9}],
            'full_text': 'Sample'
        }
        
        # Save to YAML
        self.image_processor._save_result_to_yaml(test_image, result_data)
        
        # Verify YAML file exists and has correct content
        yaml_file = os.path.join(self.test_images_dir, 'test_save.yml')
        self.assertTrue(os.path.exists(yaml_file))
        
        with open(yaml_file, 'r') as f:
            loaded_data = yaml.safe_load(f)
        
        self.assertEqual(loaded_data['image_file'], 'test_save.jpg')
        self.assertEqual(loaded_data['full_text'], 'Sample')


if __name__ == '__main__':
    unittest.main()