"""Single image processor for API requests."""

import os
import time
import logging
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

from ...config_manager import ConfigManager
from ...ocr.ocr_processor import OCRProcessor
from ...llm.vl.image_agent import ImageAgent
from ...llm.text.text_agent import TextAgent
from ...llm.translation.translator_agent import TranslatorAgent
from ..metadata_combiner.metadata_combiner import MetadataCombiner
from .step_processor import StepProcessor
from ..pipeline_state_manager import PipelineStateManager


class SingleImageProcessor:
    """Process a single image through the configured pipeline."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize the single image processor.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.logger = logging.getLogger(__name__)
        self.metadata_combiner = MetadataCombiner()
        self.state_manager = PipelineStateManager()
        self.step_processor = StepProcessor(config_manager, self.state_manager)
        
        # Initialize processors (lazy loading)
        self._ocr_processor = None
        self._image_agent = None
        self._text_agent = None
        self._translator_agent = None
        
        self.logger.info("SingleImageProcessor initialized")

    def _get_ocr_processor(self) -> OCRProcessor:
        """Get or create OCR processor instance (lazy loading)."""
        if self._ocr_processor is None:
            self.logger.info("Initializing OCR processor")
            self.logger.debug(f"Config manager type: {type(self.config_manager)}")
            self.logger.debug(f"Config type: {type(self.config_manager.config)}")
            self._ocr_processor = OCRProcessor(self.config_manager.config)
        return self._ocr_processor

    def _get_image_agent(self) -> ImageAgent:
        """Get or create image agent instance (lazy loading)."""
        if self._image_agent is None:
            self.logger.info("Initializing Image agent")
            from ...llm.ollama_client import OllamaClient
            ollama_client = OllamaClient(self.config_manager.config)
            self._image_agent = ImageAgent(self.config_manager.config, ollama_client)
        return self._image_agent

    def _get_text_agent(self) -> TextAgent:
        """Get or create text agent instance (lazy loading)."""
        if self._text_agent is None:
            self.logger.info("Initializing Text agent")
            from ...llm.ollama_client import OllamaClient
            ollama_client = OllamaClient(self.config_manager.config)
            self._text_agent = TextAgent(self.config_manager.config, ollama_client)
        return self._text_agent

    def _get_translator_agent(self) -> TranslatorAgent:
        """Get or create translator agent instance (lazy loading)."""
        if self._translator_agent is None:
            self.logger.info("Initializing Translator agent")
            from ...llm.ollama_client import OllamaClient
            ollama_client = OllamaClient(self.config_manager.config)
            self._translator_agent = TranslatorAgent(self.config_manager.config, ollama_client)
        return self._translator_agent

    def process_image(
        self,
        image_path: str,
        enable_ocr: Optional[bool] = None,
        enable_image_agent: Optional[bool] = None,
        enable_text_agent: Optional[bool] = None,
        enable_translation: Optional[bool] = None,
        vision_model: Optional[str] = None,
        text_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a single image through the pipeline.
        
        Args:
            image_path: Path to the image file
            enable_ocr: Enable OCR processing (default: from config)
            enable_image_agent: Enable image agent (default: from config)
            enable_text_agent: Enable text agent (default: from config)
            enable_translation: Enable translation (default: from config)
            vision_model: Vision model to use (default: from config)
            text_model: Text model to use (default: from config)
            
        Returns:
            Combined metadata dictionary with processing results
        """
        start_time = time.perf_counter()
        
        # Get pipeline configuration
        pipeline_config = self.config_manager.config.get('pipeline', {})
        
        # Use provided options or fall back to config defaults
        process_ocr = enable_ocr if enable_ocr is not None else pipeline_config.get('enable_ocr', False)
        process_image_agent = enable_image_agent if enable_image_agent is not None else pipeline_config.get('enable_image_agent', True)
        process_text_agent = enable_text_agent if enable_text_agent is not None else pipeline_config.get('enable_text_agent', True)
        process_translation = enable_translation if enable_translation is not None else pipeline_config.get('enable_translation', False)
        
        self.logger.info(
            f"Processing image: {Path(image_path).name} - "
            f"OCR: {process_ocr}, Image: {process_image_agent}, "
            f"Text: {process_text_agent}, Translation: {process_translation}"
        )
        
        # Initialize pipeline state
        state = self.state_manager.create_initial_state(image_path)
        
        # Results storage
        ocr_data = None
        vl_model_data = None
        text_processing = None
        translation_result = None
        
        try:
            # Step 1: OCR Processing
            if process_ocr:
                try:
                    ocr_processor = self._get_ocr_processor()
                    success, state = self.step_processor.process_ocr_step(
                        image_path, state, ocr_processor, skip_if_completed=False
                    )
                    if success and state.get('pipeline_status', {}).get('steps', {}).get('ocr_processing', {}).get('data'):
                        ocr_data = state['pipeline_status']['steps']['ocr_processing']['data']
                        self.logger.info(f"OCR completed: {ocr_data.get('total_elements', 0)} elements")
                    else:
                        step_status = state.get('pipeline_status', {}).get('steps', {}).get('ocr_processing', {}).get('status')
                        step_error = state.get('pipeline_status', {}).get('steps', {}).get('ocr_processing', {}).get('error')
                        if step_error:
                            self.logger.warning(f"OCR processing failed: {step_error}")
                        elif step_status == 'completed':
                            self.logger.warning("OCR processing completed but returned no data (no text detected in image)")
                        else:
                            self.logger.warning(f"OCR processing failed or returned no data (status: {step_status})")
                except Exception as e:
                    self.logger.error(f"Failed to initialize or run OCR processor: {e}", exc_info=True)
                    state = self.state_manager.mark_step_failed(state, 'ocr_processing', str(e))
            
            # Step 2: Image Agent Analysis
            if process_image_agent:
                image_agent = self._get_image_agent()
                
                # Override model if specified
                if vision_model:
                    self.logger.info(f"Using vision model: {vision_model}")
                    image_agent.vision_model = vision_model
                
                resize_spec = pipeline_config.get('image_resize', {})
                success, state = self.step_processor.process_image_agent_step(
                    image_path, state, image_agent,
                    skip_if_completed=False, resize_spec=resize_spec
                )
                if success and state.get('pipeline_status', {}).get('steps', {}).get('image_agent_analysis', {}).get('data'):
                    vl_model_data = state['pipeline_status']['steps']['image_agent_analysis']['data']
                    self.logger.info("Image agent analysis completed")
                else:
                    self.logger.warning("Image agent analysis failed or returned no data")
            
            # Step 3: Text Agent Processing
            if process_text_agent:
                text_agent = self._get_text_agent()
                
                # Override model if specified
                if text_model:
                    self.logger.info(f"Using text model: {text_model}")
                    text_agent.text_model = text_model
                
                success, state = self.step_processor.process_text_agent_step(
                    image_path, state, text_agent, skip_if_completed=False
                )
                if success and state.get('pipeline_status', {}).get('steps', {}).get('text_agent_processing', {}).get('data'):
                    text_processing = state['pipeline_status']['steps']['text_agent_processing']['data']
                    self.logger.info("Text agent processing completed")
                else:
                    self.logger.warning("Text agent processing failed or returned no data")
            
            # Step 4: Translation (if needed)
            if process_translation and text_processing:
                needs_translation = text_processing.get('needTranslation', False)
                
                if needs_translation:
                    translator_agent = self._get_translator_agent()
                    success, state = self.step_processor.process_translation_step(
                        image_path, state, translator_agent, skip_if_completed=False
                    )
                    if success and state.get('pipeline_status', {}).get('steps', {}).get('translation', {}).get('data'):
                        translation_result = state['pipeline_status']['steps']['translation']['data']
                        self.logger.info("Translation completed")
                    else:
                        self.logger.warning("Translation failed or returned no data")
                else:
                    self.logger.info("Translation skipped - not needed")
            
            # Calculate total processing time
            total_time = time.perf_counter() - start_time
            
            # Combine all metadata
            metadata = self.metadata_combiner.combine_metadata(
                image_path=image_path,
                ocr_data=ocr_data,
                vl_model_data=vl_model_data,
                text_processing=text_processing,
                translation_result=translation_result,
                processing_time=total_time
            )
            
            self.logger.info(
                f"Image processing completed in {total_time:.2f}s: {Path(image_path).name}"
            )
            
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error processing image {image_path}: {e}", exc_info=True)
            # Return error metadata
            return {
                'image_file': Path(image_path).name,
                'image_path': str(image_path),
                'error': str(e),
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'processing_time': time.perf_counter() - start_time,
                'status': 'failed'
            }
