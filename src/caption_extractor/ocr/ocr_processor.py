"""Enhanced OCR processing using PaddleOCR PP-OCRv5 with advanced configuration."""
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import os
import gc

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
        
        # Configuration parameters driven by existing oct_processor.py structure
        self.enabled = config.get("enabled", True)
        self.use_gpu = self.ocr_config.get("use_gpu", True)
        self.storage_folder = self.ocr_config.get("model_cache_dir", "./.paddleocr")
        self.lang = self.ocr_config.get("lang", "en")
        self.use_angle_cls = self.ocr_config.get("use_angle_cls", True)
        self.device = "gpu:0" if self.use_gpu else "cpu"

        # Two engines: one for Latin/English, one for Devanagari
        self.ocr_engine_en = None   # PP-OCRv5 server — English + Latin
        self.ocr_engine_hi = None   # devanagari_PP-OCRv5_mobile_rec

        if self.enabled:
            # Reusing environment variable mapping logic
            os.environ['PADDLE_DISABLE_ONEDNN'] = '1'
            os.environ['FLAGS_use_mkldnn'] = '0'
            os.environ['FLAGS_enable_pir_api'] = '0'
            self.storage_folder = os.path.abspath(os.path.expanduser(self.storage_folder))
            os.environ["PADDLE_HOME"] = self.storage_folder
            os.environ['PADDLEX_HOME'] = self.storage_folder
            os.environ['PPOCR_HOME'] = self.storage_folder
            
            self._init_paddleocr()
    
    def _patch_importlib(self):
        """Remap paddlepaddle → paddlepaddle-gpu for importlib lookups."""
        import importlib.metadata
        orig_ver  = importlib.metadata.version
        orig_dist = importlib.metadata.distribution

        def patched_version(name):
            return orig_ver("paddlepaddle-gpu") if name == "paddlepaddle" else orig_ver(name)

        def patched_distribution(name):
            return orig_dist("paddlepaddle-gpu") if name == "paddlepaddle" else orig_dist(name)

        importlib.metadata.version      = patched_version
        importlib.metadata.distribution = patched_distribution

        try:
            import paddlex.utils.deps
            if hasattr(paddlex.utils.deps, "is_inst_package"):
                _orig = paddlex.utils.deps.is_inst_package
                paddlex.utils.deps.is_inst_package = (
                    lambda n, *a, **kw: True if n == "paddlepaddle" else _orig(n, *a, **kw)
                )
        except Exception:
            pass


    def _init_paddleocr(self):
        """Initialize PaddleOCR with configuration settings using dual-pass layout."""
        try:
            os.environ["PADDLE_INFERENCE_ENGINE"] = "paddle"
            # Force this environment variable to double-insure the engine layout
            os.environ["PADDLE_PDX_ENABLE_MKLDNN_BYDEFAULT"] = "0"
            
            self._patch_importlib()

            import paddle
            gpu_compiled = paddle.device.is_compiled_with_cuda()
            gpu_places   = paddle.get_device() if hasattr(paddle, "get_device") else "N/A"

            from paddleocr import PaddleOCR

            # Add enable_mkldnn=False here to bypass the underlying PIR conversion bug
            shared_kwargs = dict(
                use_doc_orientation_classify = False,
                use_doc_unwarping           = False,
                use_textline_orientation    = self.use_angle_cls,
                device                      = self.device,
                enable_mkldnn               = False,  # <-- Crucial Fix
            )

            # ── Engine 1: English / Latin (default PP-OCRv5 server) ──────────
            logger.info("Loading English OCR engine (PP-OCRv5 server)...")
            self.ocr_engine_en = PaddleOCR(lang="en", **shared_kwargs)

            # ── Engine 2: Devanagari (Hindi/Sanskrit/Marathi) ────────────────
            logger.info("Loading Devanagari OCR engine (devanagari_PP-OCRv5_mobile_rec)...")
            self.ocr_engine_hi = PaddleOCR(
                lang="devanagari",
                text_recognition_model_name="devanagari_PP-OCRv5_mobile_rec",
                **shared_kwargs,
            )

            if gpu_compiled and "gpu" in str(gpu_places).lower():
                logger.info(f"[SUCCESS] Both OCR engines active on GPU ({gpu_places})")
            else:
                logger.warning(
                    f"[FALLBACK] OCR engines on CPU "
                    f"(CUDA Compiled={gpu_compiled}, Device={gpu_places})"
                )

        except Exception as e:
            logger.error(f"Failed to initialise PaddleOCR engines: {e}", exc_info=True)
            self.enabled = False
            raise e

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
            
            preproc_config = preprocessing_config or self.config.get('preprocessing', {})
            
            image = cv2.imread(image_path)
            if image is None:
                pil_image = Image.open(image_path)
                image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
            
            if image is None:
                raise Exception(f"Cannot load image: {image_path}")
            
            original_shape = image.shape

            image = self._apply_preprocessing_steps(image, preproc_config)

            try:
                if image is None:
                    raise ValueError(f"Preprocessed image is None: {image_path}")
                if not isinstance(image, np.ndarray):
                    raise ValueError(f"Preprocessed image is not a numpy array: {image_path}")
                if image.size == 0:
                    raise ValueError(f"Preprocessed image has zero size: {image_path}")
                if len(image.shape) < 2:
                    raise ValueError(f"Preprocessed image has invalid shape {image.shape}: {image_path}")
                if image.shape[0] < 1 or image.shape[1] < 1:
                    raise ValueError(f"Preprocessed image has invalid dimensions {image.shape}: {image_path}")
                
                if len(image.shape) == 2:
                    image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                elif len(image.shape) == 3:
                    if image.shape[2] == 1:
                        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
                    elif image.shape[2] == 4:
                        image = cv2.cvtColor(image, cv2.COLOR_RGBA2BGR)
                    elif image.shape[2] != 3:
                        raise ValueError(f"Preprocessed image has unsupported channel count {image.shape[2]}: {image_path}")
                
                if image.dtype != np.uint8:
                    if image.max() <= 1.0:
                        image = (image * 255).astype(np.uint8)
                    else:
                        image = image.astype(np.uint8)
                
                image = np.ascontiguousarray(image)
                
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
        """Apply preprocessing steps to enhance OCR accuracy."""
        if image is None or image.size == 0:
            raise ValueError("Cannot preprocess empty or None image")
        
        if config.get('auto_resize', True):
            max_size = tuple(config.get('max_image_size', [2048, 2048]))
            image = self._resize_image(image, max_size)
            if image is None or image.size == 0:
                raise ValueError("Image became empty after resize")
        
        if config.get('grayscale', False):
            if len(image.shape) == 3 and image.shape[2] == 3:
                image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            if image is None or image.size == 0:
                raise ValueError("Image became empty after grayscale conversion")
        
        brightness = config.get('brightness', 1.0)
        contrast = config.get('contrast', 1.0)
        if brightness != 1.0 or contrast != 1.0:
            image = self._adjust_brightness_contrast(image, brightness, contrast)
            if image is None or image.size == 0:
                raise ValueError("Image became empty after brightness/contrast adjustment")
        
        if config.get('sharpen', False):
            sharpen_strength = config.get('sharpen_strength', 1.0)
            image = self._apply_sharpening(image, sharpen_strength)
            if image is None or image.size == 0:
                raise ValueError("Image became empty after sharpening")
        
        if config.get('denoise', False):
            if image is not None and image.size > 0:
                try:
                    denoise_strength = config.get('denoise_strength', 10)
                    result = cv2.fastNlMeansDenoisingColored(image, None, denoise_strength, denoise_strength, 7, 21)
                    if result is not None and result.size > 0:
                        image = result
                except Exception as e:
                    self.logger.warning(f"Denoise failed: {e}, keeping original image")
        
        if config.get('adaptive_threshold', False):
            if image is not None and image.size > 0:
                if len(image.shape) == 3 and image.shape[2] == 3:
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                elif len(image.shape) == 2:
                    gray = image
                else:
                    gray = None
                
                if gray is not None and gray.size > 0:
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
                        if thresh is not None and thresh.size > 0:
                            image = cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR)
                    except Exception as e:
                        self.logger.warning(f"Adaptive threshold failed: {e}, keeping original image")
        
        if config.get('deskew', False):
            image = self._deskew_image(image)
            if image is None or image.size == 0:
                raise ValueError("Image became empty after deskew")
        
        if config.get('remove_borders', False):
            border_size = config.get('border_size', 10)
            image = self._remove_borders(image, border_size)
            if image is None or image.size == 0:
                raise ValueError("Image became empty after border removal")
        
        return image
    
    def _resize_image(self, image: np.ndarray, max_size: Tuple[int, int]) -> np.ndarray:
        height, width = image.shape[:2]
        max_width, max_height = max_size
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            image = cv2.resize(image, (int(width * scale), int(height * scale)), interpolation=cv2.INTER_LANCZOS4)
        return image
    
    def _adjust_brightness_contrast(self, image: np.ndarray, brightness: float, contrast: float) -> np.ndarray:
        try:
            pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
            if brightness != 1.0:
                pil_image = ImageEnhance.Brightness(pil_image).enhance(brightness)
            if contrast != 1.0:
                pil_image = ImageEnhance.Contrast(pil_image).enhance(contrast)
            return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        except Exception as e:
            self.logger.warning(f"Failed to adjust brightness/contrast: {e}, returning original image")
            return image
    
    def _apply_sharpening(self, image: np.ndarray, strength: float) -> np.ndarray:
        try:
            kernel = np.array([[-1, -1, -1], [-1, 9 * strength, -1], [-1, -1, -1]]) / strength
            return cv2.filter2D(image, -1, kernel)
        except Exception as e:
            self.logger.warning(f"Sharpening failed: {e}, returning original image")
            return image
    
    def _deskew_image(self, image: np.ndarray) -> np.ndarray:
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)
            if lines is not None:
                angles = [(line[0][1] * 180 / np.pi) - 90 for line in lines]
                median_angle = np.median(angles)
                if abs(median_angle) > 0.5:
                    (h, w) = image.shape[:2]
                    M = cv2.getRotationMatrix2D((w // 2, h // 2), median_angle, 1.0)
                    image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        except Exception as e:
            self.logger.debug(f"Deskew failed: {e}")
        return image
    
    def _remove_borders(self, image: np.ndarray, border_size: int) -> np.ndarray:
        h, w = image.shape[:2]
        border = min(int(max(0, border_size)), max(0, (h // 2) - 1), max(0, (w // 2) - 1))
        if border <= 0:
            return image
        return image[border:h-border, border:w-border]

    def _run_engine(self, engine, image: np.ndarray) -> List[Dict]:
        """Run a single engine predictive pass and capture uniform formats."""
        lines = []
        try:
            # We explicitly pass the preprocessed numpy frame to avoid path parsing anomalies
            results = list(engine.predict(image))
            for page_result in results:
                if page_result is None:
                    continue

                rec_texts  = getattr(page_result, "rec_texts",  None)
                rec_scores = getattr(page_result, "rec_scores", None)
                rec_polys  = getattr(page_result, "rec_polys",  None)

                if rec_texts is None:
                    try:
                        rec_texts  = page_result["rec_texts"]
                        rec_scores = page_result.get("rec_scores", [])
                        rec_polys  = page_result.get("rec_polys",  [])
                    except (KeyError, TypeError):
                        pass

                if not rec_texts:
                    continue

                for i, text_str in enumerate(rec_texts):
                    confidence = float(rec_scores[i]) if rec_scores is not None and i < len(rec_scores) else 1.0
                    poly_raw   = rec_polys[i] if rec_polys is not None and i < len(rec_polys) else []
                    poly       = poly_raw.tolist() if hasattr(poly_raw, "tolist") else poly_raw

                    lines.append({
                        "text":       str(text_str).strip(),
                        "confidence": round(confidence, 4),
                        "bbox":        poly,  # Mapped to bbox key for internal downstream filters
                    })
        except Exception as e:
            logger.error(f"Engine predict() failed: {e}", exc_info=True)
        return lines

    def _merge_passes(self, en_lines: List[Dict], hi_lines: List[Dict]) -> List[Dict]:
        """Merge English and Devanagari passes using bounding-box centroid checks."""
        import math

        def centroid(box):
            if not box or not isinstance(box, list):
                return (0, 0)
            # Flatten or coordinate map check
            xs = [p[0] for p in box if isinstance(p, (list, tuple)) and len(p) >= 2]
            ys = [p[1] for p in box if isinstance(p, (list, tuple)) and len(p) >= 2]
            if not xs or not ys:
                return (0, 0)
            return (sum(xs) / len(xs), sum(ys) / len(ys))

        def dist(a, b):
            return math.hypot(a[0] - b[0], a[1] - b[1])

        for ln in en_lines:
            ln["_c"] = centroid(ln["bbox"])
        for ln in hi_lines:
            ln["_c"] = centroid(ln["bbox"])

        merged = list(hi_lines)

        for en_ln in en_lines:
            overlap = any(dist(en_ln["_c"], hi_ln["_c"]) < 20 for hi_ln in hi_lines)
            if not overlap:
                merged.append(en_ln)

        merged.sort(key=lambda ln: ln["_c"][1])

        for ln in merged:
            ln.pop("_c", None)

        return merged

    def extract_text(self, image_path: str, performance_config: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Extract text from image using dual-pass OCR.
        
        Args:
            image_path: Path to the image file
            performance_config: Performance configuration (deprecated, use preprocessing config)
            
        Returns:
            List of extracted text strings with bounding boxes and confidence scores
        """
        import time
        self._ocr_start_time = time.perf_counter()
        
        if not self.enabled or (not self.ocr_engine_en and not self.ocr_engine_hi):
            return []

        try:
            # Process & clean image structure using pristine preprocess_image logic
            image = self.preprocess_image(image_path)
            
            logger.info(f"Running dual-pass engine configuration on: {image_path}")
            en_lines = self._run_engine(self.ocr_engine_en, image) if self.ocr_engine_en else []
            hi_lines = self._run_engine(self.ocr_engine_hi, image) if self.ocr_engine_hi else []

            # Merge dual engines gracefully
            extracted_data = self._merge_passes(en_lines, hi_lines)
            
            # Reapply structural filters & confidence controls from legacy engine layout
            min_confidence = self.ocr_config.get('min_confidence', 0.0)
            extracted_data = [item for item in extracted_data if item['confidence'] >= min_confidence]
            
            # Apply post-processing filters
            extracted_data = self._post_process_results(extracted_data)
            
            self.logger.debug(f"Extracted {len(extracted_data)} text elements from {image_path}")
            return extracted_data
            
        except Exception as e:
            self.logger.error(f"Error extracting text from {image_path}: {e}")
            raise
    
    def _post_process_results(self, extracted_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Post-process OCR results based on configuration."""
        post_config = self.config.get('post_processing', {})
        min_length = post_config.get('min_text_length', 1)
        extracted_data = [item for item in extracted_data if len(item['text'].strip()) >= min_length]
        
        if post_config.get('remove_special_chars', False):
            allowed_chars = post_config.get('allowed_chars', '')
            for item in extracted_data:
                if allowed_chars:
                    item['text'] = ''.join(c for c in item['text'] if c.isalnum() or c.isspace() or c in allowed_chars)
                else:
                    item['text'] = ''.join(c for c in item['text'] if c.isalnum() or c.isspace())
        
        if post_config.get('strip_whitespace', True):
            for item in extracted_data:
                item['text'] = item['text'].strip()
        
        if post_config.get('lowercase', False):
            for item in extracted_data:
                item['text'] = item['text'].lower()
        
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
        """Format extracted text data for output match alignment."""
        import time
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
        
        # text_lines = []
        # confidences = []
        
        # for item in sorted_data:
        #     text_lines.append({
        #         'text': item['text'],
        #         'confidence': round(item['confidence'], 3),
        #         'bbox': item['bbox']
        #     })
        #     confidences.append(item['confidence'])
        
        format_config = self.config.get('formatting', {})
        separator = format_config.get('line_separator', ' ')
        full_text = separator.join([item['text'] for item in sorted_data])
        # avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            # 'text_lines': text_lines,
            'full_text': full_text,
            'total_elements': len(extracted_data),
            # 'avg_confidence': round(avg_confidence, 3),
            # 'min_confidence': round(min(confidences), 3) if confidences else 0.0,
            # 'max_confidence': round(max(confidences), 3) if confidences else 0.0,
            'model': 'PaddleOCR-v5-DualPass',
            'processing_time': processing_time
        }

    def release(self):
        """Destroy both OCR engines and clear GPU VRAM cache allocation blocks safely."""
        for attr, label in [("ocr_engine_en", "English"), ("ocr_engine_hi", "Devanagari")]:
            engine = getattr(self, attr, None)
            if engine is not None:
                try:
                    predictor = getattr(engine, "_pipeline", None) or getattr(engine, "predictor", None)
                    if predictor is not None and hasattr(predictor, "destroy"):
                        predictor.destroy()
                except Exception as ex:
                    logger.warning(f"Could not call destroy() on {label} engine: {ex}")
                setattr(self, attr, None)
                logger.info(f"{label} OCR engine released.")

        gc.collect()
        try:
            import paddle
            if paddle.device.is_compiled_with_cuda():
                paddle.device.cuda.empty_cache()
                logger.info("Paddle CUDA memory cache cleared.")
        except Exception as ex:
            logger.warning(f"paddle.device.cuda.empty_cache() failed: {ex}")

        self.enabled = False
        logger.info("PaddleOCR fully offloaded from memory.")