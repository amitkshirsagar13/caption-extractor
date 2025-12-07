"""Step-by-step pipeline processor for image processing with state."""

import os
import time
import logging
from typing import Dict, Any, Tuple, Optional
from pathlib import Path

from ...pipeline_state_manager import PipelineStateManager
from ...ocr.ocr_processor import OCRProcessor
from ...llm.vl.image_agent import ImageAgent
from ...llm.text.text_agent import TextAgent


class StepProcessor:
    """Processes individual pipeline steps with state management."""

    def __init__(
        self, config_manager,
        pipeline_state_manager: PipelineStateManager
    ):
        """Initialize the step processor.

        Args:
            config_manager: Configuration manager instance
            pipeline_state_manager: Pipeline state manager instance
        """
        self.config_manager = config_manager
        self.state_manager = pipeline_state_manager
        self.logger = logging.getLogger(__name__)

    def process_ocr_step(
        self,
        image_path: str,
        state: Dict[str, Any],
        ocr_processor: OCRProcessor,
        skip_if_completed: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process OCR step.

        Args:
            image_path: Path to the image
            state: Current pipeline state
            ocr_processor: OCR processor instance
            skip_if_completed: Skip if already completed

        Returns:
            Tuple of (success, updated_state)
        """
        step_name = 'ocr_processing'

        # Debug: Log entry parameters
        self.logger.debug(f"[OCR] Entry - image_path: {image_path}")
        self.logger.debug(f"[OCR] Entry - skip_if_completed: {skip_if_completed}")
        self.logger.debug(f"[OCR] Entry - state keys: {state.keys() if state else 'None'}")
        
        # Check if should skip
        if (skip_if_completed and
                self.state_manager.is_step_completed(state, step_name)):
            self.logger.info(f"Skipping {step_name} - already completed")
            self.state_manager.mark_step_skipped(
                state, step_name, "Already completed"
            )
            return True, state

        # Mark as running
        self.logger.debug(f"[OCR] Marking step as running")
        state = self.state_manager.mark_step_running(state, step_name)
        self.logger.debug(f"[OCR] State after mark_running: {state.get('steps', {}).get(step_name, {}).get('status')}")

        try:
            start_time = time.perf_counter()
            self.logger.info(
                f"Starting {step_name} for {Path(image_path).name}"
            )

            # Debug: Check image path exists
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Image file not found: {image_path}")
            self.logger.debug(f"[OCR] Image file exists: {image_path}")

            # Debug: Get performance config
            self.logger.debug(f"[OCR] Getting performance config")
            perf_config = (
                self.config_manager.get_performance_config()
            )
            self.logger.debug(f"[OCR] Performance config: {perf_config}")
            
            # Debug: Extract text
            self.logger.debug(f"[OCR] Calling ocr_processor.extract_text")
            extracted_data = ocr_processor.extract_text(
                image_path, perf_config
            )
            self.logger.debug(f"[OCR] Extracted data type: {type(extracted_data)}")
            self.logger.debug(f"[OCR] Extracted data: {extracted_data if extracted_data else 'None or empty'}")
            
            # Debug: Format extracted text
            self.logger.debug(f"[OCR] Calling ocr_processor.format_extracted_text")
            ocr_data = ocr_processor.format_extracted_text(extracted_data)
            self.logger.debug(f"[OCR] OCR data type: {type(ocr_data)}")
            self.logger.debug(f"[OCR] OCR data keys: {ocr_data.keys() if ocr_data else 'None'}")
            self.logger.debug(f"[OCR] OCR data content: {ocr_data}")

            duration = time.perf_counter() - start_time

            # Debug: Mark as completed
            self.logger.debug(f"[OCR] Marking step as completed with data")
            state = self.state_manager.mark_step_completed(
                state, step_name, ocr_data, duration
            )
            self.logger.debug(f"[OCR] State after mark_completed: {state.get('steps', {}).get(step_name, {}).get('status')}")
            self.logger.debug(f"[OCR] State data present: {bool(state.get('steps', {}).get(step_name, {}).get('data'))}")

            elements = ocr_data.get('total_elements', 0)
            self.logger.info(
                f"{step_name} completed in {duration:.2f}s - "
                f"extracted {elements} elements"
            )

            # Debug: Final return
            self.logger.debug(f"[OCR] Returning success=True")
            return True, state

        except Exception as e:
            error_msg = f"{step_name} failed: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.logger.debug(f"[OCR] Exception type: {type(e).__name__}")
            self.logger.debug(f"[OCR] Exception details: {e}")
            state = self.state_manager.mark_step_failed(
                state, step_name, str(e)
            )
            self.logger.debug(f"[OCR] State after mark_failed: {state.get('steps', {}).get(step_name, {}).get('status')}")
            self.logger.debug(f"[OCR] Returning success=False")
            return False, state

    def process_image_agent_step(
        self,
        image_path: str,
        state: Dict[str, Any],
        image_agent: ImageAgent,
        skip_if_completed: bool = True,
        resize_spec: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process image agent analysis step.

        Args:
            image_path: Path to the image
            state: Current pipeline state
            image_agent: Image agent instance
            skip_if_completed: Skip if already completed
            resize_spec: Image resize specification

        Returns:
            Tuple of (success, updated_state)
        """
        step_name = 'image_agent_analysis'

        # Check if should skip
        if (skip_if_completed and
                self.state_manager.is_step_completed(state, step_name)):
            self.logger.info(f"Skipping {step_name} - already completed")
            self.state_manager.mark_step_skipped(
                state, step_name, "Already completed"
            )
            return True, state

        # Mark as running
        state = self.state_manager.mark_step_running(state, step_name)

        resized_temp_path = None
        try:
            start_time = time.perf_counter()
            self.logger.info(
                f"Starting {step_name} for {Path(image_path).name}"
            )

            # Resize image if needed
            if resize_spec and resize_spec.get('enabled', True):
                try:
                    resized_temp_path = self._resize_image(
                        image_path, resize_spec
                    )
                    if resized_temp_path:
                        self.logger.debug(
                            f"Resized image at: {resized_temp_path}"
                        )
                except Exception as e:
                    self.logger.warning(
                        f"Resize failed, using original: {e}"
                    )

            # Use resized or original image
            image_to_send = resized_temp_path or image_path
            vl_model_data = image_agent.analyze_image(image_to_send)

            if not vl_model_data:
                raise Exception("Image agent returned no results")

            duration = time.perf_counter() - start_time

            # Mark as completed with data
            state = self.state_manager.mark_step_completed(
                state, step_name, vl_model_data, duration
            )

            self.logger.info(
                f"{step_name} completed in {duration:.2f}s"
            )

            return True, state

        except Exception as e:
            error_msg = f"{step_name} failed: {str(e)}"
            self.logger.error(error_msg)
            state = self.state_manager.mark_step_failed(
                state, step_name, str(e)
            )
            return False, state

        finally:
            # Cleanup resized image
            if resized_temp_path and os.path.exists(resized_temp_path):
                try:
                    os.remove(resized_temp_path)
                except Exception:
                    self.logger.debug(
                        f"Failed to remove temp: {resized_temp_path}"
                    )

    def process_text_agent_step(
        self,
        image_path: str,
        state: Dict[str, Any],
        text_agent: TextAgent,
        skip_if_completed: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process text agent step.

        Args:
            image_path: Path to the image
            state: Current pipeline state
            text_agent: Text agent instance
            skip_if_completed: Skip if already completed

        Returns:
            Tuple of (success, updated_state)
        """
        step_name = 'text_agent_processing'

        # Check if should skip
        if (skip_if_completed and
                self.state_manager.is_step_completed(state, step_name)):
            self.logger.info(f"Skipping {step_name} - already completed")
            self.state_manager.mark_step_skipped(
                state, step_name, "Already completed"
            )
            return True, state

        # Mark as running
        state = self.state_manager.mark_step_running(state, step_name)

        try:
            start_time = time.perf_counter()
            self.logger.info(
                f"Starting {step_name} for {Path(image_path).name}"
            )

            # Get OCR data from previous step
            ocr_data = state['results'].get('ocr_data')
            vl_model_data = state['results'].get('vl_model_data')

            # Prepare text input
            ocr_text = ocr_data.get('full_text', '') if ocr_data else ''
            vision_text = (
                vl_model_data.get('text', '')
                if vl_model_data else ''
            )
            base_text = ocr_text or vision_text

            if not base_text:
                self.logger.info(f"No text available for {step_name}")
                state = self.state_manager.mark_step_skipped(
                    state, step_name, "No text available"
                )
                return True, state

            # Process text
            text_processing = text_agent.process_text(
                base_text, vl_model_data
            )

            if not text_processing:
                raise Exception("Text agent returned no results")

            duration = time.perf_counter() - start_time

            # Mark as completed with data
            state = self.state_manager.mark_step_completed(
                state, step_name, text_processing, duration
            )

            self.logger.info(
                f"{step_name} completed in {duration:.2f}s"
            )

            return True, state

        except Exception as e:
            error_msg = f"{step_name} failed: {str(e)}"
            self.logger.error(error_msg)
            state = self.state_manager.mark_step_failed(
                state, step_name, str(e)
            )
            return False, state

    def process_translation_step(
        self,
        image_path: str,
        state: Dict[str, Any],
        translator_agent,
        skip_if_completed: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process translation step.

        Args:
            image_path: Path to the image
            state: Current pipeline state
            translator_agent: Translator agent instance
            skip_if_completed: Skip if already completed

        Returns:
            Tuple of (success, updated_state)
        """
        step_name = 'translation'

        # Check if should skip
        if (skip_if_completed and
                self.state_manager.is_step_completed(state, step_name)):
            self.logger.info(f"Skipping {step_name} - already completed")
            self.state_manager.mark_step_skipped(
                state, step_name, "Already completed"
            )
            return True, state

        # Mark as running
        state = self.state_manager.mark_step_running(state, step_name)

        try:
            start_time = time.perf_counter()
            self.logger.info(
                f"Starting {step_name} for {Path(image_path).name}"
            )

            # Get text processing result
            text_processing = state['results'].get('text_processing')

            if not text_processing:
                state = self.state_manager.mark_step_skipped(
                    state, step_name, "No text processing data"
                )
                return True, state

            # Check if translation is needed
            need_translation = text_processing.get(
                'needTranslation', False
            )
            primary_text = (
                text_processing.get('primary_text') or
                text_processing.get('corrected_text', '')
            )

            if not need_translation or not primary_text:
                self.logger.info("Translation not needed")
                state = self.state_manager.mark_step_skipped(
                    state, step_name, "Translation not needed"
                )
                return True, state

            # Perform translation
            translation_result = (
                translator_agent.translate_to_english(primary_text)
            )

            if not translation_result:
                raise Exception("Translator returned no results")

            duration = time.perf_counter() - start_time

            # Mark as completed with data
            state = self.state_manager.mark_step_completed(
                state, step_name, translation_result, duration
            )

            self.logger.info(
                f"{step_name} completed in {duration:.2f}s"
            )

            return True, state

        except Exception as e:
            error_msg = f"{step_name} failed: {str(e)}"
            self.logger.error(error_msg)
            state = self.state_manager.mark_step_failed(
                state, step_name, str(e)
            )
            return False, state

    def process_metadata_combination_step(
        self,
        image_path: str,
        state: Dict[str, Any],
        metadata_combiner,
        skip_if_completed: bool = True
    ) -> Tuple[bool, Dict[str, Any]]:
        """Process metadata combination step.

        Args:
            image_path: Path to the image
            state: Current pipeline state
            metadata_combiner: Metadata combiner instance
            skip_if_completed: Skip if already completed

        Returns:
            Tuple of (success, updated_state)
        """
        step_name = 'metadata_combination'

        # Check if should skip - but always regenerate metadata to ensure it's current
        # This step is fast and needs to combine the latest results from all previous steps
        if False:  # Never skip metadata combination - always regenerate
            self.logger.info(f"Skipping {step_name} - already completed")
            self.state_manager.mark_step_skipped(
                state, step_name, "Already completed"
            )
            return True, state

        # Mark as running
        state = self.state_manager.mark_step_running(state, step_name)

        try:
            start_time = time.perf_counter()
            self.logger.info(
                f"Starting {step_name} for {Path(image_path).name}"
            )

            # Get results from all previous steps
            ocr_data = state['results'].get('ocr_data')
            vl_model_data = state['results'].get('vl_model_data')
            text_processing = state['results'].get('text_processing')
            translation_result = state['results'].get(
                'translation_result'
            )

            # Combine metadata
            proc_time = state['metadata']['total_processing_time']
            combined_metadata = metadata_combiner.combine_metadata(
                image_path=image_path,
                ocr_data=ocr_data,
                vl_model_data=vl_model_data,
                text_processing=text_processing,
                translation_result=translation_result,
                processing_time=proc_time
            )

            duration = time.perf_counter() - start_time

            # Mark as completed with data
            state = self.state_manager.mark_step_completed(
                state, step_name, combined_metadata, duration
            )

            self.logger.info(
                f"{step_name} completed in {duration:.2f}s"
            )

            return True, state

        except Exception as e:
            error_msg = f"{step_name} failed: {str(e)}"
            self.logger.error(error_msg)
            state = self.state_manager.mark_step_failed(
                state, step_name, str(e)
            )
            return False, state

    def _resize_image(
        self, image_path: str, spec: Dict[str, Any]
    ) -> Optional[str]:
        """Resize image according to specification.

        Args:
            image_path: Path to the image
            spec: Resize specification

        Returns:
            Path to resized image or None
        """
        import cv2
        import tempfile

        max_size = spec.get('max_size', [1024, 1024])
        keep_aspect = spec.get('keep_aspect', True)
        interp_name = spec.get('interpolation', 'area')

        try:
            img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                self.logger.warning(
                    f"Failed to read image for resizing: {image_path}"
                )
                return None

            h, w = img.shape[:2]
            max_w, max_h = int(max_size[0]), int(max_size[1])

            # If already within bounds, no resize needed
            if w <= max_w and h <= max_h:
                return None

            if keep_aspect:
                scale = min(max_w / w, max_h / h)
                new_w = max(1, int(w * scale))
                new_h = max(1, int(h * scale))
            else:
                new_w, new_h = max_w, max_h

            interp_map = {
                'area': cv2.INTER_AREA,
                'linear': cv2.INTER_LINEAR,
                'cubic': cv2.INTER_CUBIC,
            }
            interp = interp_map.get(interp_name, cv2.INTER_AREA)

            resized = cv2.resize(img, (new_w, new_h), interpolation=interp)

            # Write to temporary file
            suffix = Path(image_path).suffix
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            tmp_path = tmp.name
            tmp.close()

            # Save with quality settings
            perf_conf = self.config_manager.get_performance_config()
            quality = int(perf_conf.get('resize_quality', 85))
            if suffix.lower() in ['.jpg', '.jpeg']:
                cv2.imwrite(
                    tmp_path, resized,
                    [int(cv2.IMWRITE_JPEG_QUALITY), quality]
                )
            else:
                cv2.imwrite(tmp_path, resized)

            return tmp_path

        except Exception as e:
            self.logger.debug(f"Resize error: {e}")
            return None
