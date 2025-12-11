"""Enhanced OCR processing using PaddleOCR PP-OCRv5 with advanced configuration."""
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import os

logger = logging.getLogger(__name__)

class OCRProcessor:
    """Handles OCR processing using PaddleOCR with enhanced configuration."""
    
    def __init__(self, config: dict):
        """Initialize OCR processor with configuration.
        
        Args:
            config: Configuration dictionary containing OCR settings
        """
        self.logger = logger
        self.config = config
        self.ocr_config = config.get('ocr', {})
        self.preprocessing_config = config.get('preprocessing', {})
        self.post_processing_config = config.get('post_processing', {})
        
        # Initialize PaddleOCR with configuration
        self._init_paddleocr()
    
    def _init_paddleocr(self):
        """Initialize PaddleOCR with configuration settings."""
        # Disable oneDNN to prevent segmentation faults on Windows
        os.environ['PADDLE_DISABLE_ONEDNN'] = '1'
        os.environ['FLAGS_use_mkldnn'] = '0'
        
        # Enable PaddleOCR logging to see download URLs
        os.environ['PPOCR_DEBUG'] = '1'
        
        # Set custom cache directory if configured
        # IMPORTANT: Must be set BEFORE importing PaddleOCR
        cache_dir = self.ocr_config.get('model_cache_dir')
        if cache_dir:
            cache_dir = os.path.abspath(os.path.expanduser(cache_dir))
            os.environ['PPOCR_HOME'] = cache_dir
            logger.info(f"Using configured PaddleOCR cache directory: {cache_dir}")
        else:
            cache_dir = os.path.expanduser('~/.paddleocr')
            logger.info(f"Using default PaddleOCR cache directory: {cache_dir}")
        
        # Import PaddleOCR AFTER setting environment variables
        from paddleocr import PaddleOCR
        
        logger.info("Initializing PaddleOCR...")
        logger.info(f"OCR Configuration: {self.ocr_config}")
        
        # Basic settings
        lang = self.ocr_config.get('lang', 'devanagari')
        ocr_params = {
            'lang': lang,
            'use_angle_cls': self.ocr_config.get('use_angle_cls', True),
            # 'use_gpu': False,  # Force CPU to avoid GPU-related crashes
            # 'show_log': False,  # Reduce verbosity
        }
        
        # Explicitly set model directories to use the configured cache location
        # This ensures PaddleOCR uses our custom location instead of the default
        if cache_dir:
            # Create the directory structure if it doesn't exist
            os.makedirs(cache_dir, exist_ok=True)
            
            # Set explicit paths for each model type
            det_model_dir = os.path.join(cache_dir, 'whl', 'det', lang, f'{lang}_PP-OCRv5_det_infer')
            rec_model_dir = os.path.join(cache_dir, 'whl', 'rec', lang, f'{lang}_PP-OCRv5_rec_infer')
            cls_model_dir = os.path.join(cache_dir, 'whl', 'cls', 'ch_ppocr_mobile_v2.0_cls_infer')
            
            ocr_params['det_model_dir'] = det_model_dir
            ocr_params['rec_model_dir'] = rec_model_dir
            ocr_params['cls_model_dir'] = cls_model_dir
            
            logger.info(f"Detection model directory: {det_model_dir}")
            logger.info(f"Recognition model directory: {rec_model_dir}")
            logger.info(f"Classification model directory: {cls_model_dir}")
        
        # Model directory (legacy config, if specified)
        model_dir = self.ocr_config.get('model_dir')
        if model_dir:
            ocr_params['model_dir'] = model_dir
            logger.info(f"Using legacy model directory: {model_dir}")
        
        # Detection parameters
        det_config = self.ocr_config.get('detection', {})
        ocr_params.update({
            'det_db_thresh': det_config.get('det_db_thresh', 0.3),
            'det_db_box_thresh': det_config.get('det_db_box_thresh', 0.5),
            'det_db_unclip_ratio': det_config.get('det_db_unclip_ratio', 1.6),
        })
        
        # Recognition parameters - reduce batch size to prevent crashes
        rec_config = self.ocr_config.get('recognition', {})
        ocr_params.update({
            'rec_batch_num': 1,  # Use batch size of 1 to avoid memory issues
        })
        
        # Classification parameters - reduce batch size
        cls_config = self.ocr_config.get('classification', {})
        ocr_params.update({
            'cls_batch_num': 1,  # Use batch size of 1 to avoid memory issues
        })
        
        logger.info("=" * 80)
        logger.info("PaddleOCR will now attempt to download models if not cached.")
        logger.info("Model download URLs for English (en) language:")
        logger.info("-" * 80)
        logger.info("Detection Model (PP-OCRv5):")
        logger.info("  URL: https://paddleocr.bj.bcebos.com/PP-OCRv5/english/en_PP-OCRv5_det_infer.tar")
        logger.info("")
        logger.info("Recognition Model (PP-OCRv5):")
        logger.info("  URL: https://paddleocr.bj.bcebos.com/PP-OCRv5/english/en_PP-OCRv5_rec_infer.tar")
        logger.info("")
        logger.info("Angle Classification Model:")
        logger.info("  URL: https://paddleocr.bj.bcebos.com/dygraph_v2.0/ch/ch_ppocr_mobile_v2.0_cls_infer.tar")
        logger.info("")
        logger.info("Models will be downloaded to:")
        logger.info(f"  Cache directory: {cache_dir}")
        logger.info(f"  (Configure via ocr.model_cache_dir in config.yml)")
        logger.info("=" * 80)
        
        try:
            logger.info("Attempting to initialize PaddleOCR with parameters:")
            for key, value in ocr_params.items():
                logger.info(f"  {key}: {value}")
            
            self.ocr = PaddleOCR(**ocr_params)
            self.ocr_engine = self.ocr  # Alias for consistency
            logger.info("PaddleOCR initialized successfully!")
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error("PADDLEOCR INITIALIZATION FAILED")
            logger.error("=" * 80)
            logger.error(f"Error: {str(e)}")
            logger.error("")
            logger.error("TROUBLESHOOTING STEPS:")
            logger.error("1. Check if you can access these URLs in your browser:")
            logger.error("   - https://paddleocr.bj.bcebos.com/")
            logger.error("   - https://paddleocr.bj.bcebos.com/PP-OCRv5/english/en_PP-OCRv5_det_infer.tar")
            logger.error("")
            logger.error("2. If URLs are blocked, download models manually:")
            logger.error("   python download_models.py")
            logger.error("")
            logger.error("3. Check if models are already cached:")
            logger.error(f"   dir {os.path.expanduser('~')}\\.paddleocr")
            logger.error("")
            logger.error("4. If behind proxy, set environment variables:")
            logger.error("   set HTTP_PROXY=http://proxy:port")
            logger.error("   set HTTPS_PROXY=http://proxy:port")
            logger.error("=" * 80)
            raise

    
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

            # Ensure image is a contiguous uint8 numpy array suitable for Paddle
            try:
                # Comprehensive validation
                if image is None:
                    raise ValueError(f"Preprocessed image is None: {image_path}")
                
                if not isinstance(image, np.ndarray):
                    raise ValueError(f"Preprocessed image is not a numpy array: {image_path}")
                
                if image.size == 0:
                    raise ValueError(f"Preprocessed image has zero size: {image_path}")
                
                if len(image.shape) < 2:
                    raise ValueError(f"Preprocessed image has invalid shape {image.shape}: {image_path}")
                
                # Check minimum dimensions
                if image.shape[0] < 1 or image.shape[1] < 1:
                    raise ValueError(f"Preprocessed image has invalid dimensions {image.shape}: {image_path}")
                
                # Ensure 3-channel BGR format for PaddleOCR
                if len(image.shape) == 2:
                    # Grayscale - convert to BGR
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                elif len(image.shape) == 3:
                    if image.shape[2] == 1:
                        # Single channel - convert to BGR
                        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                    elif image.shape[2] == 4:
                        # RGBA - convert to BGR
                        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
                    elif image.shape[2] != 3:
                        raise ValueError(f"Preprocessed image has unsupported channel count {image.shape[2]}: {image_path}")
                
                # Force uint8 and contiguous layout
                if image.dtype != np.uint8:
                    # Normalize to 0-255 range if needed
                    if image.max() <= 1.0:
                        image = (image * 255).astype(np.uint8)
                    else:
                        image = image.astype(np.uint8)
                
                image = np.ascontiguousarray(image)
                
                # Final validation
                if image.size == 0 or image.shape[0] < 1 or image.shape[1] < 1:
                    raise ValueError(f"Final preprocessed image is invalid: {image_path}")
                    
            except Exception as conv_err:
                self.logger.error(f"Invalid image after preprocessing for {image_path}: {conv_err}")
                raise

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
        # Validate input
        if image is None or image.size == 0:
            raise ValueError("Cannot preprocess empty or None image")
        
        # 1. Resize if needed
        if config.get('auto_resize', True):
            max_size = tuple(config.get('max_image_size', [2048, 2048]))
            image = self._resize_image(image, max_size)
            
            # Validate after resize
            if image is None or image.size == 0:
                raise ValueError("Image became empty after resize")
        
        # 2. Convert to grayscale if configured
        if config.get('grayscale', False):
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)  # Convert back for PaddleOCR
            
            # Validate after grayscale conversion
            if image is None or image.size == 0:
                raise ValueError("Image became empty after grayscale conversion")
        
        # 3. Adjust brightness and contrast
        brightness = config.get('brightness', 1.0)
        contrast = config.get('contrast', 1.0)
        if brightness != 1.0 or contrast != 1.0:
            image = self._adjust_brightness_contrast(image, brightness, contrast)
            
            # Validate after brightness/contrast
            if image is None or image.size == 0:
                raise ValueError("Image became empty after brightness/contrast adjustment")
        
        # 4. Apply sharpening
        if config.get('sharpen', False):
            sharpen_strength = config.get('sharpen_strength', 1.0)
            image = self._apply_sharpening(image, sharpen_strength)
            
            # Validate after sharpen
            if image is None or image.size == 0:
                raise ValueError("Image became empty after sharpening")
        
        # 5. Denoise
        if config.get('denoise', False):
            if image is None or image.size == 0:
                self.logger.warning("Skipping denoise - image is empty")
            else:
                try:
                    denoise_strength = config.get('denoise_strength', 10)
                    result = cv2.fastNlMeansDenoisingColored(image, None, denoise_strength, denoise_strength, 7, 21)
                    
                    if result is not None and result.size > 0:
                        image = result
                    else:
                        self.logger.warning("Denoise produced empty result, keeping original")
                except Exception as e:
                    self.logger.warning(f"Denoise failed: {e}, keeping original image")
        
        # 6. Apply adaptive thresholding for better text detection
        if config.get('adaptive_threshold', False):
            # Validate image before thresholding
            if image is None or image.size == 0:
                self.logger.warning("Skipping adaptive threshold - image is empty")
            else:
                if len(image.shape) == 3 and image.shape[2] == 3:
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                elif len(image.shape) == 2:
                    gray = image
                else:
                    self.logger.warning(f"Skipping adaptive threshold - unexpected shape {image.shape}")
                    gray = None
                
                if gray is not None and gray.size > 0:
                    # Ensure block size is an odd integer >=3
                    block_size = int(config.get('threshold_block_size', 11) or 11)
                    if block_size % 2 == 0:
                        block_size = block_size - 1 if block_size > 3 else 3
                    block_size = max(3, block_size)
                    
                    try:
                        thresh = cv2.adaptiveThreshold(
                            gray, 255,
                            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                            cv2.THRESH_BINARY,
                            block_size,
                            int(config.get('threshold_c', 2))
                        )
                        
                        # Validate threshold result
                        if thresh is not None and thresh.size > 0:
                            image = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                        else:
                            self.logger.warning("Adaptive threshold produced empty result, keeping original")
                    except Exception as e:
                        self.logger.warning(f"Adaptive threshold failed: {e}, keeping original image")
        
        # 7. Deskew image
        if config.get('deskew', False):
            image = self._deskew_image(image)
            
            # Validate after deskew
            if image is None or image.size == 0:
                raise ValueError("Image became empty after deskew")
        
        # 8. Remove borders/margins
        if config.get('remove_borders', False):
            border_size = config.get('border_size', 10)
            image = self._remove_borders(image, border_size)
            
            # Validate after border removal
            if image is None or image.size == 0:
                raise ValueError("Image became empty after border removal")
        
        # Final validation before returning
        if image is None or image.size == 0:
            raise ValueError("Preprocessing resulted in empty image")
        
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
        try:
            # Validate input
            if image is None or image.size == 0:
                self.logger.warning("Cannot adjust brightness/contrast on empty image")
                return image
            
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
            result = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            # Validate result
            if result is None or result.size == 0:
                self.logger.warning("Brightness/contrast adjustment produced empty image, returning original")
                return image
            
            return result
        except Exception as e:
            self.logger.warning(f"Failed to adjust brightness/contrast: {e}, returning original image")
            return image
    
    def _apply_sharpening(self, image: np.ndarray, strength: float) -> np.ndarray:
        """Apply sharpening filter to image."""
        try:
            if image is None or image.size == 0:
                self.logger.warning("Cannot sharpen empty image")
                return image
            
            kernel = np.array([[-1, -1, -1],
                              [-1, 9 * strength, -1],
                              [-1, -1, -1]]) / strength
            result = cv2.filter2D(image, -1, kernel)
            
            if result is None or result.size == 0:
                self.logger.warning("Sharpening produced empty image, returning original")
                return image
            
            return result
        except Exception as e:
            self.logger.warning(f"Sharpening failed: {e}, returning original image")
            return image
    
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
        if h <= 0 or w <= 0:
            self.logger.debug("Image has non-positive dimensions, skipping border removal")
            return image

        # Clamp border_size so we don't create an empty image
        border = int(max(0, border_size))
        max_border_h = max(0, (h // 2) - 1)
        max_border_w = max(0, (w // 2) - 1)
        border = min(border, max_border_h, max_border_w)

        if border <= 0:
            return image

        new_h = h - 2 * border
        new_w = w - 2 * border
        if new_h <= 0 or new_w <= 0:
            self.logger.warning("Requested border removal would result in empty image; skipping")
            return image

        return image[border:h-border, border:w-border]
    
    def extract_text(self, image_path: str, performance_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Extract text from image using OCR.
        
        Args:
            image_path: Path to the image file
            performance_config: Performance configuration (deprecated, use preprocessing config)
            
        Returns:
            List of extracted text with bounding boxes and confidence scores
        """
        import time
        self._ocr_start_time = time.perf_counter()
        
        try:
            if self.ocr_engine is None:
                raise Exception("OCR engine not initialized")
            
            # Check if file exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            
            self.logger.debug(f"Processing image: {image_path}")
            
            # Load and preprocess image as numpy array
            # Using numpy array is more reliable than passing path to avoid PaddleOCR segfaults
            image = cv2.imread(image_path)
            if image is None:
                # Try with PIL as fallback
                pil_image = Image.open(image_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            if image is None:
                raise Exception(f"Cannot load image: {image_path}")
            
            self.logger.debug(f"Loaded image {image_path}: shape={image.shape}, dtype={image.dtype}")
            
            # Apply minimal preprocessing to ensure compatibility
            # Resize if too large
            preproc_config = self.config.get('preprocessing', {})
            if preproc_config.get('auto_resize', True):
                max_size = tuple(preproc_config.get('max_image_size', [2048, 2048]))
                image = self._resize_image(image, max_size)
            
            # Validate image before passing to PaddleOCR
            if image is None or image.size == 0:
                raise ValueError(f"Image is empty after loading: {image_path}")

            # Ensure proper dtype and memory layout
            if image.dtype != np.uint8:
                self.logger.debug("Converting image dtype to uint8 for OCR")
                image = image.astype(np.uint8)
            image = np.ascontiguousarray(image)
            
            # Ensure 3-channel BGR format
            if len(image.shape) == 2:
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            elif len(image.shape) == 3 and image.shape[2] == 4:
                image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
            
            # Final validation
            if len(image.shape) != 3 or image.shape[2] != 3:
                raise ValueError(f"Image must be 3-channel BGR format. Got shape: {image.shape} for {image_path}")
            
            if image.shape[0] < 1 or image.shape[1] < 1:
                raise ValueError(f"Image has invalid dimensions: {image.shape} for {image_path}")
            
            self.logger.info(f"Passing to PaddleOCR: shape={image.shape}, dtype={image.dtype}, contiguous={image.flags['C_CONTIGUOUS']}")

            try:
                results = self.ocr_engine.ocr(image)
            except Exception as ocr_err:
                error_msg = str(ocr_err)
                
                # Check for PaddlePaddle internal errors (vector, trace_order, dependency, etc.)
                if any(keyword in error_msg.lower() for keyword in ['vector<bool>', 'trace_order', 'dependency_count', 'preconditionnotmet']):
                    self.logger.error("=" * 80)
                    self.logger.error("CRITICAL: PaddlePaddle Internal Error Detected")
                    self.logger.error("=" * 80)
                    self.logger.error(f"Error: {error_msg}")
                    self.logger.error("")
                    self.logger.error("This error indicates a PaddlePaddle bug or incompatibility.")
                    self.logger.error("")
                    self.logger.error("RECOMMENDED FIXES:")
                    self.logger.error("1. Reinstall PaddlePaddle and PaddleOCR:")
                    self.logger.error("   pip uninstall paddlepaddle paddleocr -y")
                    self.logger.error("   pip install paddlepaddle")
                    self.logger.error("   pip install paddleocr")
                    self.logger.error("")
                    self.logger.error("2. Clear PaddleOCR model cache:")
                    self.logger.error(f"   rmdir /s /q {os.path.expanduser('~')}\\.paddleocr")
                    self.logger.error("")
                    self.logger.error("3. If using Python 3.13, downgrade to Python 3.11:")
                    self.logger.error("   PaddlePaddle may not fully support Python 3.13 yet")
                    self.logger.error("")
                    self.logger.error("4. Try processing one image at a time (disable batch processing)")
                    self.logger.error("")
                    self.logger.error("5. Alternative: Disable OCR in config.yml:")
                    self.logger.error("   pipeline:")
                    self.logger.error("     enable_ocr: false")
                    self.logger.error("")
                    self.logger.error("See PADDLEOCR_FIX.md for detailed instructions")
                    self.logger.error("=" * 80)
                    raise RuntimeError(f"PaddlePaddle internal error - reinstallation required: {error_msg}")
                
                # Generic error handling
                hint = (
                    "PaddleOCR raised an error while processing the image. "
                    "Common causes: empty/zero-sized image, wrong dtype, device/config mismatch, "
                    "or corrupted PaddlePaddle installation."
                )
                self.logger.error(f"OCR engine error for {image_path}: {ocr_err} -- {hint}")
                raise
            
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
            Formatted text data with model info and processing time
        """
        import time
        
        # Calculate OCR processing time
        processing_time = 0.0
        if hasattr(self, '_ocr_start_time'):
            processing_time = round(time.perf_counter() - self._ocr_start_time, 3)
        
        if not extracted_data:
            return {
                'text_lines': [],
                'full_text': '',
                'total_elements': 0,
                'avg_confidence': 0.0,
                'model': 'PaddleOCR',
                'processing_time': processing_time
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
            # 'text_lines': text_lines,
            'full_text': full_text,
            'total_elements': len(extracted_data),
            'avg_confidence': round(avg_confidence, 3),
            'min_confidence': round(min(confidences), 3) if confidences else 0.0,
            'max_confidence': round(max(confidences), 3) if confidences else 0.0,
            'model': 'PaddleOCR',
            'processing_time': processing_time
        }