"""Main entry point for Caption Extractor."""

import sys
import logging
import argparse
from pathlib import Path

from .config_manager import ConfigManager
from .ocr.ocr_processor import OCRProcessor
from .pipeline.image_processor import ImageProcessor
from .llm.ollama_client import OllamaClient
from .llm.vl.image_agent import ImageAgent
from .llm.text.text_agent import TextAgent
from .llm.translation.translator_agent import TranslatorAgent
from .pipeline.batch_processor.batch_processor_by_steps import BatchProcessorBySteps


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
    parser.add_argument(
        "--batch-mode",
        type=str,
        choices=["image", "step"],
        default="step",
        help=(
            "Batch processing mode: 'image' (default) processes each image"
            " through all steps, 'step' processes all images through each"
            " step (better for local LLM models)"
        ),
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
        
        # Load configuration (this will setup logging via ConfigManager)
        config_manager = ConfigManager(args.config)
        
        # Get logger after config is loaded
        logger = logging.getLogger(__name__)
        
        # Setup logging level if verbose
        if args.verbose:
            from .logging_config import reconfigure_logging
            reconfigure_logging('DEBUG')
        
        logger.info("Starting Caption Extractor")
        logger.info(f"Configuration loaded from: {args.config}")
        
        # Override config with command line arguments
        if args.input_folder:
            config_manager.config['data']['input_folder'] = args.input_folder
            logger.info(f"Input folder overridden to: {args.input_folder}")
        
        if args.threads:
            config_manager.config['processing']['num_threads'] = args.threads
            logger.info(f"Number of threads overridden to: {args.threads}")
        
        # Get pipeline configuration
        pipeline_config = config_manager.config.get('pipeline', {})
        enable_ocr = pipeline_config.get('enable_ocr', True)
        enable_image_agent = pipeline_config.get('enable_image_agent', True)
        enable_text_agent = pipeline_config.get('enable_text_agent', True)
        
        # Initialize OCR processor
        ocr_processor = None
        if enable_ocr:
            logger.info("Initializing OCR processor...")
            ocr_config = config_manager.get_ocr_config()
            ocr_processor = OCRProcessor(ocr_config)
        else:
            logger.info("OCR processing is disabled")
        
        # Initialize Ollama client for AI agents
        ollama_client = None
        if enable_image_agent or enable_text_agent:
            logger.info("Initializing Ollama client...")
            try:
                ollama_client = OllamaClient(config_manager.config)
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama client: {e}")
                logger.warning("AI agents will be disabled")
                enable_image_agent = False
                enable_text_agent = False
        
        # Initialize Image Agent
        image_agent = None
        if enable_image_agent and ollama_client:
            logger.info("Initializing Image Agent...")
            try:
                image_agent = ImageAgent(config_manager.config, ollama_client)
            except Exception as e:
                logger.warning(f"Failed to initialize Image Agent: {e}")
                image_agent = None
        
        # Initialize Text Agent
        text_agent = None
        if enable_text_agent and ollama_client:
            logger.info("Initializing Text Agent...")
            try:
                text_agent = TextAgent(config_manager.config, ollama_client)
            except Exception as e:
                logger.warning(f"Failed to initialize Text Agent: {e}")
                text_agent = None

        # Initialize Translator Agent (optional)
        translator_agent = None
        enable_translation = pipeline_config.get('enable_translation', False)
        if enable_translation and ollama_client:
            logger.info("Initializing Translator Agent...")
            try:
                translator_agent = TranslatorAgent(
                    config_manager.config, ollama_client
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Translator Agent: {e}")
                translator_agent = None
        
        # Determine processing mode
        input_folder = config_manager.get_input_folder()
        logger.info(f"Scanning for images in: {input_folder}")

        if args.batch_mode == 'step':
            # Allow overriding threads for per-step processing
            if args.threads:
                config_manager.config.setdefault('batch_processing', {})[
                    'num_threads_per_step'
                ] = args.threads

            logger.info("Initializing step-based batch processor...")
            batch_processor = BatchProcessorBySteps(
                config_manager,
                ocr_processor,
                image_agent,
                text_agent,
                translator_agent,
            )

            image_files = batch_processor.get_image_files(input_folder)
        else:
            # Initialize image processor (image-by-image)
            logger.info("Initializing image processor...")
            image_processor = ImageProcessor(
                config_manager,
                ocr_processor,
                image_agent,
                text_agent,
                translator_agent,
            )

            image_files = image_processor.get_image_files(input_folder)
        
        if not image_files:
            logger.warning("No image files found to process")
            logger.info(f"No image files found in: {input_folder}")
            logger.info(
                f"Supported formats: {', '.join(config_manager.get_supported_formats())}"
            )
            return 1
        
        # Process images
        logger.info(f"Found {len(image_files)} image files to process")
        logger.info(f"Processing {len(image_files)} images from: {input_folder}")
        logger.info(f"Using {config_manager.get_num_threads()} threads")

        if args.batch_mode == 'step':
        if args.batch_mode == 'step':
            logger.info("Batch processing mode: STEP")
            report = batch_processor.process_images_batch_by_steps(image_files)

            # Step-mode report (summary of steps)
            logger.info("=" * 60)
            logger.info("PROCESSING COMPLETED (STEP MODE)")
            logger.info("=" * 60)
            logger.info(f"Total images: {report['summary']['total_images']}")
            logger.info(f"Steps completed: {', '.join(report['summary']['steps'])}")
            total_time_val = report['timing']['total_processing_time']
            logger.info(f"Total processing time: {total_time_val}s")

            if report.get('errors'):
                logger.warning("Errors occurred during processing:")
                for error in report['errors']:
                    name = Path(error['image']).name
                    logger.error(f"  - {name}: {error['error']}")

        else:
            logger.info("Batch processing mode: IMAGE")
            report = image_processor.process_images_batch(image_files)

            # Image-mode (original) report
            logger.info("=" * 60)
            logger.info("PROCESSING COMPLETED")
            logger.info("=" * 60)
            logger.info(f"Total images: {report['summary']['total_images']}")
            logger.info(f"Successfully processed: {report['summary']['successful_images']}")
            logger.info(f"Failed: {report['summary']['failed_images']}")
            success_rate_str = f"{report['summary']['success_rate']}%"
            logger.info(f"Success rate: {success_rate_str}")
            logger.info(f"Average time per image: {report['timing']['average_time_per_image']}s")
            logger.info(f"Total time: {report['timing']['batch_time']}s")

            if report['errors']:
                logger.warning("Errors occurred during processing:")
                for error in report['errors']:
                    name = Path(error['image']).name
                    logger.error(f"  - {name}: {error['error']}")

            logger.info("Results saved as .yml files in the same folders as the images.")
        logger.info("Caption Extractor completed successfully")
        return 0
        
        logger.info("Caption Extractor completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger = logging.getLogger(__name__)
        logger.info("Processing interrupted by user")
        return 1
        
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1__main__":
    sys.exit(main())
