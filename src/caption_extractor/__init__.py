"""Caption Extractor - OCR text extraction using PaddleOCR PP-OCRv5."""

__version__ = "0.1.0"
__author__ = "Caption Extractor Team"
__description__ = "OCR text extraction from images using PaddleOCR PP-OCRv5"

from .ocr.ocr_processor import OCRProcessor
from .config_manager import ConfigManager
from .pipeline.image_processor import ImageProcessor
from .pipeline.batch_processor.batch_processor_by_steps import BatchProcessorBySteps

__all__ = [
    "OCRProcessor",
    "ConfigManager",
    "ImageProcessor",
    "BatchProcessorBySteps",
]
