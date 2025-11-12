"""Caption Extractor - OCR text extraction using PaddleOCR PP-OCRv5."""

__version__ = "0.1.0"
__author__ = "Caption Extractor Team"
__description__ = "OCR text extraction from images using PaddleOCR PP-OCRv5"

from .ocr_processor import OCRProcessor
from .config_manager import ConfigManager
from .image_processor import ImageProcessor

__all__ = ["OCRProcessor", "ConfigManager", "ImageProcessor"]