"""Enhanced OCR processing using PaddleOCR PP-OCRv5 with advanced configuration."""

import os
import logging
from typing import List, Dict, Any, Tuple, Optional
from paddleocr import PaddleOCR
import cv2
import numpy as np
from PIL import Image, ImageEnhance


class OCRProcessor:
    """Handles OCR operations using PaddleOCR with enhanced accuracy controls."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the OCR processor.
        
        Args:
            config: OCR configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.ocr_engine = None
        self._initialize_ocr()
    
    def _initialize_ocr(self) -> None:
        """Initialize PaddleOCR engine with configuration."""
        try:
            self.logger.info("Initializing PaddleOCR engine...")
            
            # Set environment variables to prevent conflicts
            os.environ['OMP_NUM_THREADS'] = '1'
            os.environ['OPENCV_IO_ENABLE_OPENEXR'] = '1'
            os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
            
            # Get OCR configuration section
            ocr_config = self.config.get('ocr', {})
            
            # Setup OCR parameters with enhanced controls
            ocr_params = {
                'use_angle_cls': ocr_config.get('use_angle_cls', True),
                'lang': ocr_config.get('lang', 'en'),
                'use_gpu': ocr_config.get('use_gpu', False),
                'show_log': ocr_config.get('show_log', False),
            }
            
            # Add detection parameters for better accuracy
            detection_config = ocr_config.get('detection', {})
            if detection_config.get('det_db_thresh') is not None:
                ocr_params['det_db_thresh'] = detection_config['det_db_thresh']
            if detection_config.get('det_db_box_thresh') is not None:
                ocr_params['det_db_box_thresh'] = detection_config['det_db_box_thresh']
            if detection_config.get('det_db_unclip_ratio') is not None:
                ocr_params['det_db_unclip_ratio'] = detection_config['det_db_unclip_ratio']
            if detection_config.get('use_dilation') is not None:
                ocr_params['use_dilation'] = detection_config['use_dilation']
            if detection_config.get('det_db_score_mode') is not None:
                ocr_params['det_db_score_mode'] = detection_config['det_db_score_mode']
            
            # Add recognition parameters
            recognition_config = ocr_config.get('recognition', {})
            if recognition_config.get('rec_batch_num') is not None:
                ocr_params['rec_batch_num'] = recognition_config['rec_batch_num']
            if recognition_config.get('max_text_length') is not None:
                ocr_params['max_text_length'] = recognition_config['max_text_length']
            if recognition_config.get('rec_algorithm') is not None:
                ocr_params['rec_algorithm'] = recognition_config['rec_algorithm']
            
            # Add classification parameters
            classification_config = ocr_config.get('classification', {})
            if classification_config.get('cls_batch_num') is not None:
                ocr_params['cls_batch_num'] = classification_config['cls_batch_num']
            if classification_config.get('cls_thresh') is not None:
                ocr_params['cls_thresh'] = classification_config['cls_thresh']
            
            # Set model directory if specified
            model_dir = ocr_config.get('model_dir')
            if model_dir and os.path.exists(model_dir):
                self.logger.info(f"Using model directory: {model_dir}")
            
            # Initialize with error handling
            try:
                self.logger.info("Creating PaddleOCR instance...")
                self.ocr_engine = PaddleOCR(**ocr_params)
                self.logger.info("PaddleOCR engine initialized successfully")
                
                # Test initialization
                test_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
                self.logger.info("Testing PaddleOCR with dummy image...")
                test_result = self.ocr_engine.ocr(test_image)
                self.logger.info("PaddleOCR test successful - ready for processing")
                
            except Exception as init_error:
                self.logger.error(f"PaddleOCR initialization failed: {init_error}")
                # Fallback initialization
                fallback_params = {
                    'lang': 'en',
                    'use_angle_cls': False,
                }
                self.logger.info("Attempting fallback initialization...")
                self.ocr_engine = PaddleOCR(**fallback_params)
                self.logger.info("PaddleOCR initialized with fallback parameters")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize PaddleOCR: {e}")
            raise RuntimeError(f"OCR initialization failed: {e}")
    
    def preprocess_image(self, image_path: str, preprocessing_config: Dict[str, Any] = None) -> np.ndarray:
        """Preprocess image for OCR with enhanced controls.
        
        Args:
            image_path: Path to the image file
            preprocessing_config: Preprocessing configuration
            
        Returns:
            Preprocessed image as numpy array
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            # Get preprocessing config
            preproc_config = preprocessing_config or self.config.get('preprocessing', {})
            
            # Load image
            image = cv2.imread(image_path)
            if image is None:
                pil_image = Image.open(image_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            if image is None:
                raise Exception(f"Cannot load image: {image_path}")
            
            original_shape = image.shape
            
            # Apply preprocessing steps based on config
            image = self._apply_preprocessing_steps(image, preproc_config)
            
            self.logger.debug(f"Preprocessed image {image_path}: {original_shape} -> {image.shape}")
            return image
            
        except Exception as e:
            self.logger.error(f"Error preprocessing image {image_path}: {e}")
            raise
    
    def _apply_preprocessing_steps(self, image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
        """Apply preprocessing steps to enhance OCR accuracy.
        
        Args:
            image: Input image
            config: Preprocessing configuration
            
        Returns:
            Preprocessed image
        """
        # 1. Resize if needed
        if config.get('auto_resize', True):
            max_size = tuple(config.get('max_image_size', [2048, 2048]))
            image = self._resize_image(image, max_size)
        
        # 2. Convert to grayscale if configured
        if config.get('grayscale', False):
            image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)  # Convert back for PaddleOCR
        
        # 3. Adjust brightness and contrast
        brightness = config.get('brightness', 1.0)
        contrast = config.get('contrast', 1.0)
        if brightness != 1.0 or contrast != 1.0:
            image = self._adjust_brightness_contrast(image, brightness, contrast)
        
        # 4. Apply sharpening
        if config.get('sharpen', False):
            sharpen_strength = config.get('sharpen_strength', 1.0)
            image = self._apply_sharpening(image, sharpen_strength)
        
        # 5. Denoise
        if config.get('denoise', False):
            denoise_strength = config.get('denoise_strength', 10)
            image = cv2.fastNlMeansDenoisingColored(image, None, denoise_strength, denoise_strength, 7, 21)
        
        # 6. Apply adaptive thresholding for better text detection
        if config.get('adaptive_threshold', False):
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            thresh = cv2.adaptiveThreshold(
                gray, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY,
                config.get('threshold_block_size', 11),
                config.get('threshold_c', 2)
            )
            image = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
        
        # 7. Deskew image
        if config.get('deskew', False):
            image = self._deskew_image(image)
        
        # 8. Remove borders/margins
        if config.get('remove_borders', False):
            border_size = config.get('border_size', 10)
            image = self._remove_borders(image, border_size)
        
        return image
    
    def _resize_image(self, image: np.ndarray, max_size: Tuple[int, int]) -> np.ndarray:
        """Resize image if it exceeds maximum dimensions."""
        height, width = image.shape[:2]
        max_width, max_height = max_size
        
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        return image
    
    def _adjust_brightness_contrast(self, image: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
        """Adjust image brightness and contrast."""
        # Convert to PIL for easier manipulation
        pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # Adjust brightness
        if brightness != 1.0:
            enhancer = ImageEnhance.Brightness(pil_image)
            pil_image = enhancer.enhance(brightness)
        
        # Adjust contrast
        if contrast != 1.0:
            enhancer = ImageEnhance.Contrast(pil_image)
            pil_image = enhancer.enhance(contrast)
        
        # Convert back to OpenCV format
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    
    def _apply_sharpening(self, image: np.ndarray, strength: float) -> np.ndarray:
        """Apply sharpening filter to image."""
        kernel = np.array([[-1, -1, -1],
                          [-1, 9 * strength, -1],
                          [-1, -1, -1]]) / strength
        return cv2.filter2D(image, -1, kernel)
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        """Deskew image using Hough transform."""
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
            
            if lines is not None:
                angles = []
                for line in lines:
                    rho, theta = line[0]
                    angle = (theta * 180 / np.pi) - 90
                    angles.append(angle)
                
                # Calculate median angle
                median_angle = np.median(angles)
                
                # Rotate image
                if abs(median_angle) > 0.5:  # Only rotate if angle is significant
                    (h, w) = image.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, median_angle, 1.0)
                    image = cv2.warpAffine(image, M, (w, h), 
                                          flags=cv2.INTER_CUBIC, 
                                          borderMode=cv2.BORDER_REPLICATE)
        except Exception as e:
            self.logger.debug(f"Deskew failed: {e}")
        
        return image
    
    def _remove_borders(self, image: np.ndarray, border_size: int) -> np.ndarray:
        """Remove borders from image."""
        h, w = image.shape[:2]
        return image[border_size:h-border_size, border_size:w-border_size]
    
    def extract_text(self, image_path: str, performance_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Extract text from image using OCR.
        
        Args:
            image_path: Path to the image file
            performance_config: Performance configuration (deprecated, use preprocessing config)
            
        Returns:
            List of extracted text with bounding boxes and confidence scores
        """
        try:
            if self.ocr_engine is None:
                raise Exception("OCR engine not initialized")
            
            # Preprocess image
            image = self.preprocess_image(image_path)
            
            # Perform OCR
            self.logger.debug(f"Processing image: {image_path}")
            results = self.ocr_engine.ocr(image)
            
            # Process results
            extracted_data = []
            if results and len(results) > 0:
                result = results[0]
                
                # New PaddleOCR format
                if isinstance(result, dict) and 'rec_texts' in result:
                    rec_texts = result.get('rec_texts', [])
                    rec_scores = result.get('rec_scores', [])
                    dt_polys = result.get('dt_polys', [])
                    
                    min_length = min(len(rec_texts), len(rec_scores), len(dt_polys))
                    
                    for i in range(min_length):
                        text = rec_texts[i]
                        confidence = rec_scores[i]
                        bbox = dt_polys[i].tolist() if hasattr(dt_polys[i], 'tolist') else dt_polys[i]
                        
                        # Apply confidence threshold filter
                        min_confidence = self.config.get('ocr', {}).get('min_confidence', 0.0)
                        if confidence >= min_confidence:
                            extracted_data.append({
                                'text': text,
                                'confidence': confidence,
                                'bbox': bbox
                            })
                
                # Old PaddleOCR format
                elif isinstance(result, list):
                    min_confidence = self.config.get('ocr', {}).get('min_confidence', 0.0)
                    for line in result:
                        if line and len(line) >= 2:
                            bbox = line[0]
                            text_info = line[1]
                            
                            if text_info and len(text_info) >= 2:
                                text = text_info[0]
                                confidence = text_info[1]
                                
                                if confidence >= min_confidence:
                                    extracted_data.append({
                                        'text': text,
                                        'confidence': confidence,
                                        'bbox': bbox
                                    })
            
            # Apply post-processing filters
            extracted_data = self._post_process_results(extracted_data)
            
            self.logger.debug(f"Extracted {len(extracted_data)} text elements from {image_path}")
            return extracted_data
            
        except Exception as e:
            self.logger.error(f"Error extracting text from {image_path}: {e}")
            raise
    
    def _post_process_results(self, extracted_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process OCR results based on configuration.
        
        Args:
            extracted_data: Raw extracted data
            
        Returns:
            Filtered and processed data
        """
        post_config = self.config.get('post_processing', {})
        
        # Filter by minimum text length
        min_length = post_config.get('min_text_length', 1)
        extracted_data = [item for item in extracted_data if len(item['text'].strip()) >= min_length]
        
        # Remove special characters if configured
        if post_config.get('remove_special_chars', False):
            allowed_chars = post_config.get('allowed_chars', '')
            for item in extracted_data:
                if allowed_chars:
                    item['text'] = ''.join(c for c in item['text'] if c.isalnum() or c.isspace() or c in allowed_chars)
                else:
                    item['text'] = ''.join(c for c in item['text'] if c.isalnum() or c.isspace())
        
        # Strip whitespace
        if post_config.get('strip_whitespace', True):
            for item in extracted_data:
                item['text'] = item['text'].strip()
        
        # Convert to lowercase if configured
        if post_config.get('lowercase', False):
            for item in extracted_data:
                item['text'] = item['text'].lower()
        
        # Remove duplicates if configured
        if post_config.get('remove_duplicates', False):
            seen = set()
            unique_data = []
            for item in extracted_data:
                if item['text'] not in seen:
                    seen.add(item['text'])
                    unique_data.append(item)
            extracted_data = unique_data
        
        return extracted_data
    
    def format_extracted_text(self, extracted_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Format extracted text data for output.
        
        Args:
            extracted_data: List of extracted text elements
            
        Returns:
            Formatted text data
        """
        if not extracted_data:
            return {
                'text_lines': [],
                'full_text': '',
                'total_elements': 0,
                'avg_confidence': 0.0
            }
        
        # Sort by y-coordinate for proper reading order
        sorted_data = sorted(extracted_data, key=lambda x: x['bbox'][0][1] if isinstance(x['bbox'][0], (list, tuple)) else x['bbox'][0])
        
        text_lines = []
        confidences = []
        
        for item in sorted_data:
            text_lines.append({
                'text': item['text'],
                'confidence': round(item['confidence'], 3),
                'bbox': item['bbox']
            })
            confidences.append(item['confidence'])
        
        # Get formatting config
        format_config = self.config.get('formatting', {})
        separator = format_config.get('line_separator', ' ')
        
        # Combine all text
        full_text = separator.join([item['text'] for item in sorted_data])
        
        # Calculate statistics
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            'text_lines': text_lines,
            'full_text': full_text,
            'total_elements': len(extracted_data),
            'avg_confidence': round(avg_confidence, 3),
            'min_confidence': round(min(confidences), 3) if confidences else 0.0,
            'max_confidence': round(max(confidences), 3) if confidences else 0.0
        }