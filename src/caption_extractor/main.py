"""Main entry point for Caption Extractor."""

import sys
import logging
import argparse
from pathlib import Path

from .config_manager import ConfigManager
from .ocr_processor import OCRProcessor
from .image_processor import ImageProcessor


def setup_argument_parser() -> argparse.ArgumentParser:
    """Setup command line argument parser.
    
    Returns:
        Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="Extract text from images using PaddleOCR PP-OCRv5",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config.yml",
        help="Path to configuration file (default: config.yml)"
    )
    
    parser.add_argument(
        "--input-folder",
        type=str,
        help="Override input folder from config"
    )
    
    parser.add_argument(
        "--threads",
        type=int,
        help="Override number of threads from config"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="caption-extractor 0.1.0"
    )
    
    return parser


def main() -> int:
    """Main function to run the caption extractor.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse command line arguments
        parser = setup_argument_parser()
        args = parser.parse_args()
        
        # Load configuration
        print(f"Loading configuration from: {args.config}")
        config_manager = ConfigManager(args.config)
        
        # Setup logging level if verbose
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        logger = logging.getLogger(__name__)
        logger.info("Starting Caption Extractor")
        logger.info(f"Configuration loaded from: {args.config}")
        
        # Override config with command line arguments
        if args.input_folder:
            config_manager.config['data']['input_folder'] = args.input_folder
            logger.info(f"Input folder overridden to: {args.input_folder}")
        
        if args.threads:
            config_manager.config['processing']['num_threads'] = args.threads
            logger.info(f"Number of threads overridden to: {args.threads}")
        
        # Initialize OCR processor
        logger.info("Initializing OCR processor...")
        ocr_config = config_manager.get_ocr_config()
        ocr_processor = OCRProcessor(ocr_config)
        
        # Initialize image processor
        logger.info("Initializing image processor...")
        image_processor = ImageProcessor(config_manager, ocr_processor)
        
        # Get image files from input folder
        input_folder = config_manager.get_input_folder()
        logger.info(f"Scanning for images in: {input_folder}")
        image_files = image_processor.get_image_files(input_folder)
        
        if not image_files:
            logger.warning("No image files found to process")
            print(f"No image files found in: {input_folder}")
            print(f"Supported formats: {config_manager.get_supported_formats()}")
            return 1
        
        # Process images
        logger.info(f"Found {len(image_files)} image files to process")
        print(f"\nProcessing {len(image_files)} images from: {input_folder}")
        print(f"Using {config_manager.get_num_threads()} threads")
        
        report = image_processor.process_images_batch(image_files)
        
        # Display summary
        print("\n" + "="*60)
        print("PROCESSING COMPLETED")
        print("="*60)
        print(f"Total images: {report['summary']['total_images']}")
        print(f"Successfully processed: {report['summary']['successful_images']}")
        print(f"Failed: {report['summary']['failed_images']}")
        print(f"Success rate: {report['summary']['success_rate']}%")
        print(f"Average time per image: {report['timing']['average_time_per_image']}s")
        print(f"Total time: {report['timing']['batch_time']}s")
        
        if report['errors']:
            print(f"\nErrors occurred during processing:")
            for error in report['errors']:
                print(f"  - {Path(error['image']).name}: {error['error']}")
        
        print(f"\nResults saved as .yml files in the same folders as the images.")
        
        logger.info("Caption Extractor completed successfully")
        return 0
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user")
        logger = logging.getLogger(__name__)
        logger.info("Processing interrupted by user")
        return 1
        
    except Exception as e:
        print(f"Error: {e}")
        logger = logging.getLogger(__name__)
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())