"""
Download PaddleOCR models for offline usage.

This script helps you download PaddleOCR models so the application
can work without internet connectivity.
"""

import os
import sys
import logging
from pathlib import Path
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from config.yml."""
    config_path = Path("config.yml")
    if not config_path.exists():
        logger.warning("config.yml not found, using default cache directory")
        return {}
    
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def get_cache_directory(config: dict) -> str:
    """Get the PaddleOCR cache directory from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Absolute path to cache directory
    """
    cache_dir = config.get('ocr', {}).get('model_cache_dir')
    
    if cache_dir:
        # Convert to absolute path and expand user home directory
        cache_dir = os.path.abspath(os.path.expanduser(cache_dir))
        logger.info(f"Using configured cache directory: {cache_dir}")
    else:
        # Default to ~/.paddleocr
        cache_dir = os.path.expanduser('~/.paddleocr')
        logger.info(f"Using default cache directory: {cache_dir}")
    
    return cache_dir


def download_paddleocr_models():
    """Download PaddleOCR models to the models directory."""
    try:
        from paddleocr import PaddleOCR
        
        # Load config and get cache directory
        config = load_config()
        cache_dir = get_cache_directory(config)
        
        # Create cache directory
        Path(cache_dir).mkdir(parents=True, exist_ok=True)
        
        # Set environment variable to use our configured cache directory
        os.environ['PPOCR_HOME'] = cache_dir
        
        logger.info("Downloading PaddleOCR models...")
        logger.info("This will download models from the internet and cache them locally.")
        logger.info(f"Models will be saved to: {cache_dir}")
        
        # Initialize PaddleOCR - this will download models if not present
        # The models will be cached in PaddlePaddle's cache directory
        logger.info("\nDownloading English OCR models...")
        ocr_en = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=False,
            show_log=True
        )
        
        # Test the model
        logger.info("\nTesting English model...")
        import numpy as np
        test_image = np.ones((100, 300, 3), dtype=np.uint8) * 255
        result = ocr_en.ocr(test_image)
        logger.info("✓ English model downloaded and tested successfully!")
        
        # Display cache location
        logger.info(f"\nModels are cached in: {cache_dir}")
        logger.info("\nYou can now run the application offline.")
        logger.info("\nTo use these models, ensure your config.yml has:")
        logger.info("  ocr:")
        logger.info("    lang: 'en'")
        logger.info("    use_angle_cls: true")
        
        return True
        
    except Exception as e:
        logger.error(f"Error downloading models: {e}")
        logger.error("\nIf you're behind a firewall or proxy, you may need to:")
        logger.error("1. Configure proxy settings: export HTTP_PROXY=http://proxy:port")
        logger.error("2. Download models manually from: https://github.com/PaddlePaddle/PaddleOCR")
        return False


def check_existing_models():
    """Check if PaddleOCR models are already downloaded."""
    config = load_config()
    cache_dir = get_cache_directory(config)
    
    if os.path.exists(cache_dir):
        model_files = list(Path(cache_dir).rglob('*.pdparams'))
        if model_files:
            logger.info(f"Found {len(model_files)} cached model files in: {cache_dir}")
            return True
    
    logger.info("No cached models found.")
    return False


def main():
    """Main entry point."""
    logger.info("PaddleOCR Model Downloader")
    logger.info("=" * 50)
    
    # Check for existing models
    if check_existing_models():
        logger.info("\n✓ PaddleOCR models are already downloaded!")
        logger.info("You can run the application without internet connectivity.")
        response = input("\nDo you want to re-download models? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Download models
    success = download_paddleocr_models()
    
    if success:
        logger.info("\n" + "=" * 50)
        logger.info("✓ Setup complete! You can now use the application offline.")
    else:
        logger.error("\n" + "=" * 50)
        logger.error("✗ Setup failed. Please check the error messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
