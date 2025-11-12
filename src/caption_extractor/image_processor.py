"""Image processing and batch operations."""

import os
import time
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm

from .ocr_processor import OCRProcessor


class ImageProcessor:
    """Handles batch image processing with threading support."""
    
    def __init__(self, config_manager, ocr_processor: OCRProcessor):
        """Initialize the image processor.
        
        Args:
            config_manager: Configuration manager instance
            ocr_processor: OCR processor instance
        """
        self.config_manager = config_manager
        self.ocr_processor = ocr_processor
        self.logger = logging.getLogger(__name__)
        self.stats_lock = Lock()
        self.processing_stats = {
            'total_images': 0,
            'processed_images': 0,
            'failed_images': 0,
            'total_time': 0.0,
            'processing_times': [],
            'errors': []
        }
    
    def get_image_files(self, folder_path: str) -> List[str]:
        """Get list of image files from folder.
        
        Args:
            folder_path: Path to the folder containing images
            
        Returns:
            List of image file paths
        """
        if not os.path.exists(folder_path):
            self.logger.error(f"Input folder does not exist: {folder_path}")
            return []
        
        supported_formats = self.config_manager.get_supported_formats()
        image_files = []
        
        try:
            for file_path in Path(folder_path).rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in supported_formats:
                    image_files.append(str(file_path))
            
            self.logger.info(f"Found {len(image_files)} image files in {folder_path}")
            return sorted(image_files)
            
        except Exception as e:
            self.logger.error(f"Error scanning folder {folder_path}: {e}")
            return []
    
    def process_single_image(self, image_path: str) -> Tuple[str, bool, float, Dict[str, Any]]:
        """Process a single image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (image_path, success, processing_time, result_data)
        """
        start_time = time.time()
        
        try:
            # Extract text using OCR
            performance_config = self.config_manager.get_performance_config()
            extracted_data = self.ocr_processor.extract_text(image_path, performance_config)
            
            # Format the extracted text
            formatted_data = self.ocr_processor.format_extracted_text(extracted_data)
            
            # Add metadata
            result_data = {
                'image_file': os.path.basename(image_path),
                'image_path': image_path,
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'processing_time': 0.0,  # Will be updated below
                **formatted_data
            }
            
            processing_time = time.time() - start_time
            result_data['processing_time'] = round(processing_time, 3)
            
            # Save result to YAML file in same folder as image
            self._save_result_to_yaml(image_path, result_data)
            
            return image_path, True, processing_time, result_data
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Error processing {image_path}: {e}"
            self.logger.error(error_msg)
            
            return image_path, False, processing_time, {'error': str(e)}
    
    def _save_result_to_yaml(self, image_path: str, result_data: Dict[str, Any]) -> None:
        """Save processing result to YAML file.
        
        Args:
            image_path: Path to the processed image
            result_data: Processing result data
        """
        try:
            # Create output file path (same folder as image, .yml extension)
            image_file = Path(image_path)
            output_path = image_file.parent / f"{image_file.stem}.yml"
            
            # Save to YAML file
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(result_data, f, default_flow_style=False, 
                         allow_unicode=True, indent=2)
            
            self.logger.debug(f"Saved result to: {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving result for {image_path}: {e}")
            raise
    
    def _update_stats(self, image_path: str, success: bool, processing_time: float, 
                     error: str = None) -> None:
        """Update processing statistics.
        
        Args:
            image_path: Path to the processed image
            success: Whether processing was successful
            processing_time: Time taken to process the image
            error: Error message if processing failed
        """
        with self.stats_lock:
            self.processing_stats['processed_images'] += 1
            self.processing_stats['total_time'] += processing_time
            self.processing_stats['processing_times'].append(processing_time)
            
            if success:
                self.logger.debug(f"Successfully processed {os.path.basename(image_path)} "
                                f"in {processing_time:.3f}s")
            else:
                self.processing_stats['failed_images'] += 1
                if error:
                    self.processing_stats['errors'].append({
                        'image': image_path,
                        'error': error,
                        'time': processing_time
                    })
    
    def process_images_batch(self, image_files: List[str]) -> Dict[str, Any]:
        """Process images in batch with threading support.
        
        Args:
            image_files: List of image file paths to process
            
        Returns:
            Processing statistics and results
        """
        if not image_files:
            self.logger.warning("No image files to process")
            return self.get_processing_report()
        
        # Initialize stats
        self.processing_stats['total_images'] = len(image_files)
        self.processing_stats['processed_images'] = 0
        self.processing_stats['failed_images'] = 0
        self.processing_stats['total_time'] = 0.0
        self.processing_stats['processing_times'] = []
        self.processing_stats['errors'] = []
        
        num_threads = self.config_manager.get_num_threads()
        show_progress = self.config_manager.is_progress_enabled()
        
        self.logger.info(f"Starting batch processing of {len(image_files)} images "
                        f"using {num_threads} threads")
        
        start_time = time.time()
        
        # Setup progress bar if enabled
        progress_bar = None
        if show_progress:
            progress_bar = tqdm(total=len(image_files), 
                              desc="Processing images", 
                              unit="img")
        
        try:
            # Process images concurrently
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Submit all tasks
                future_to_image = {
                    executor.submit(self.process_single_image, image_path): image_path
                    for image_path in image_files
                }
                
                # Process completed tasks
                for future in as_completed(future_to_image):
                    image_path = future_to_image[future]
                    
                    try:
                        img_path, success, proc_time, result_data = future.result()
                        
                        # Update progress bar with current file
                        if progress_bar:
                            progress_bar.set_postfix({
                                'current': os.path.basename(img_path),
                                'time': f'{proc_time:.2f}s'
                            })
                            progress_bar.update(1)
                        
                        # Update statistics
                        error_msg = result_data.get('error') if not success else None
                        self._update_stats(img_path, success, proc_time, error_msg)
                        
                    except Exception as e:
                        self.logger.error(f"Unexpected error processing {image_path}: {e}")
                        self._update_stats(image_path, False, 0.0, str(e))
                        
                        if progress_bar:
                            progress_bar.update(1)
            
        finally:
            if progress_bar:
                progress_bar.close()
        
        total_batch_time = time.time() - start_time
        self.processing_stats['batch_time'] = total_batch_time
        
        # Generate and log final report
        report = self.get_processing_report()
        self._log_final_report(report)
        
        return report
    
    def get_processing_report(self) -> Dict[str, Any]:
        """Generate processing statistics report.
        
        Returns:
            Processing report dictionary
        """
        stats = self.processing_stats
        
        # Calculate averages
        avg_time = (sum(stats['processing_times']) / len(stats['processing_times']) 
                   if stats['processing_times'] else 0.0)
        
        success_rate = ((stats['processed_images'] - stats['failed_images']) / 
                       max(stats['processed_images'], 1)) * 100
        
        report = {
            'summary': {
                'total_images': stats['total_images'],
                'processed_images': stats['processed_images'],
                'successful_images': stats['processed_images'] - stats['failed_images'],
                'failed_images': stats['failed_images'],
                'success_rate': round(success_rate, 2)
            },
            'timing': {
                'total_processing_time': round(stats['total_time'], 3),
                'batch_time': round(stats.get('batch_time', 0.0), 3),
                'average_time_per_image': round(avg_time, 3),
                'min_time': round(min(stats['processing_times']), 3) if stats['processing_times'] else 0.0,
                'max_time': round(max(stats['processing_times']), 3) if stats['processing_times'] else 0.0
            },
            'errors': stats['errors']
        }
        
        return report
    
    def _log_final_report(self, report: Dict[str, Any]) -> None:
        """Log the final processing report.
        
        Args:
            report: Processing report dictionary
        """
        summary = report['summary']
        timing = report['timing']
        
        self.logger.info("=" * 60)
        self.logger.info("PROCESSING REPORT")
        self.logger.info("=" * 60)
        self.logger.info(f"Total images: {summary['total_images']}")
        self.logger.info(f"Successfully processed: {summary['successful_images']}")
        self.logger.info(f"Failed: {summary['failed_images']}")
        self.logger.info(f"Success rate: {summary['success_rate']}%")
        self.logger.info("-" * 40)
        self.logger.info(f"Total processing time: {timing['total_processing_time']}s")
        self.logger.info(f"Total batch time: {timing['batch_time']}s")
        self.logger.info(f"Average time per image: {timing['average_time_per_image']}s")
        self.logger.info(f"Min/Max time: {timing['min_time']}s / {timing['max_time']}s")
        
        if report['errors']:
            self.logger.info("-" * 40)
            self.logger.info(f"Errors ({len(report['errors'])}):")
            for error in report['errors']:
                self.logger.error(f"  {os.path.basename(error['image'])}: {error['error']}")
        
        self.logger.info("=" * 60)