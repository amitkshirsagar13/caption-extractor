"""Image processing with pipeline state management."""

import os
import time
import yaml
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from tqdm import tqdm

from ..ocr.ocr_processor import OCRProcessor
from ..llm.vl.image_agent import ImageAgent
from ..llm.text.text_agent import TextAgent
from .metadata_combiner.metadata_combiner import MetadataCombiner
from ..pipeline_state_manager import PipelineStateManager
from .step_processor.step_processor import StepProcessor


class ImageProcessor:
    """Handles batch image processing with pipeline state."""

    def __init__(
        self,
        config_manager,
        ocr_processor: OCRProcessor,
        image_agent: ImageAgent = None,
        text_agent: TextAgent = None,
        translator_agent=None
    ):
        """Initialize the image processor.

        Args:
            config_manager: Configuration manager instance
            ocr_processor: OCR processor instance
            image_agent: Image agent instance (optional)
            text_agent: Text agent instance (optional)
            translator_agent: Translator agent (optional)
        """
        self.config_manager = config_manager
        self.ocr_processor = ocr_processor
        self.image_agent = image_agent
        self.text_agent = text_agent
        self.translator_agent = translator_agent
        self.metadata_combiner = MetadataCombiner()
        self.logger = logging.getLogger(__name__)
        self.stats_lock = Lock()

        # Initialize pipeline state manager
        self.state_manager = PipelineStateManager()
        self.step_processor = StepProcessor(
            config_manager, self.state_manager
        )

        # Get pipeline configuration
        pipeline_config = config_manager.config.get('pipeline', {})
        self.enable_ocr = pipeline_config.get('enable_ocr', True)
        self.enable_image_agent = (
            pipeline_config.get('enable_image_agent', True)
        )
        self.enable_text_agent = (
            pipeline_config.get('enable_text_agent', True)
        )
        self.enable_translation = (
            pipeline_config.get('enable_translation', False)
        )

        self.logger.info(
            "ImageProcessor initialized - OCR: %s, "
            "Image Agent: %s, Text Agent: %s",
            self.enable_ocr, self.enable_image_agent,
            self.enable_text_agent
        )
        self.processing_stats = {
            'total_images': 0,
            'processed_images': 0,
            'failed_images': 0,
            'total_time': 0.0,
            'processing_times': [],
            'errors': []
        }

    def get_image_files(self, folder_path: str) -> List[str]:
        """Get list of image files from folder.

        Args:
            folder_path: Path to the folder containing images

        Returns:
            List of image file paths
        """
        if not os.path.exists(folder_path):
            self.logger.error(
                "Input folder does not exist: %s", folder_path
            )
            return []

        supported_formats = (
            self.config_manager.get_supported_formats()
        )
        image_files = []

        try:
            for file_path in Path(folder_path).rglob('*'):
                if (file_path.is_file() and
                        file_path.suffix.lower() in supported_formats):
                    image_files.append(str(file_path))

            self.logger.info(
                "Found %s image files in %s",
                len(image_files), folder_path
            )
            return sorted(image_files)

        except Exception as e:
            self.logger.error(
                "Error scanning folder %s: %s", folder_path, e
            )
            return []

    def process_single_image(
        self, image_path: str
    ) -> Tuple[str, bool, float, Dict[str, Any]]:
        """Process single image using pipeline state management.

        Args:
            image_path: Path to the image file

        Returns:
            Tuple of (image_path, success, processing_time, result_data)
        """
        batch_start = time.time()

        try:
            # Load or create state
            state = self.state_manager.load_state(image_path)
            if not state:
                state = self.state_manager.create_initial_state(
                    image_path
                )
                self.logger.info(
                    "Created new state for %s",
                    Path(image_path).name
                )
            else:
                self.logger.info(
                    "Loaded state for %s",
                    Path(image_path).name
                )

            # Get resize spec
            resize_spec = (
                self.config_manager.get_image_resize_spec()
            )

            # Process each pipeline step
            success = True

            # Step 1: OCR
            if self.enable_ocr and self.ocr_processor:
                step_success, state = (
                    self.step_processor.process_ocr_step(
                        image_path, state, self.ocr_processor
                    )
                )
                self.state_manager.save_state(image_path, state)
                if not step_success:
                    self.logger.warning(
                        "OCR step failed for %s",
                        Path(image_path).name
                    )
                success = success and step_success

            # Step 2: Image Agent
            if self.enable_image_agent and self.image_agent:
                step_success, state = (
                    self.step_processor.process_image_agent_step(
                        image_path, state, self.image_agent,
                        resize_spec=resize_spec
                    )
                )
                self.state_manager.save_state(image_path, state)
                if not step_success:
                    self.logger.warning(
                        "Image agent step failed for %s",
                        Path(image_path).name
                    )
                success = success and step_success

            # Step 3: Text Agent
            if self.enable_text_agent and self.text_agent:
                step_success, state = (
                    self.step_processor.process_text_agent_step(
                        image_path, state, self.text_agent
                    )
                )
                self.state_manager.save_state(image_path, state)
                if not step_success:
                    self.logger.warning(
                        "Text agent step failed for %s",
                        Path(image_path).name
                    )
                success = success and step_success

            # Step 4: Translation
            if self.enable_translation and self.translator_agent:
                step_success, state = (
                    self.step_processor.process_translation_step(
                        image_path, state, self.translator_agent
                    )
                )
                self.state_manager.save_state(image_path, state)
                success = success and step_success

            # Step 5: Metadata Combination
            step_success, state = (
                self.step_processor.process_metadata_combination_step(
                    image_path, state, self.metadata_combiner
                )
            )
            # Do not allow metadata step to overwrite previous failures
            success = success and step_success
            self.state_manager.save_state(image_path, state)

            # Mark pipeline as completed
            state = self.state_manager.mark_pipeline_completed(state)
            self.state_manager.save_state(image_path, state)

            # Get combined result
            combined_metadata = state['results'].get(
                'combined_metadata'
            )
            if not combined_metadata:
                combined_metadata = (
                    self.metadata_combiner.create_minimal_metadata(
                        image_path, "No combined metadata"
                    )
                )

            # Backwards compatibility: expose top-level full_text if present in OCR block
            try:
                if ('full_text' not in combined_metadata and
                        combined_metadata.get('ocr', {}).get('full_text')):
                    combined_metadata['full_text'] = (
                        combined_metadata['ocr']['full_text']
                    )
            except Exception:
                # Ignore if combined_metadata structure is unexpected
                pass

            # If any step failed, add an 'error' key with failed step messages
            if not success:
                try:
                    step_info = state.get('pipeline_status', {}).get('steps', {})
                    errors = []
                    for step_name, info in step_info.items():
                        if info.get('status') == 'failed':
                            err = info.get('error') or f"{step_name} failed"
                            errors.append(f"{step_name}: {err}")

                    combined_metadata['error'] = ' | '.join(errors) if errors else 'One or more steps failed'
                except Exception:
                    combined_metadata['error'] = 'One or more steps failed'

            proc_time = time.time() - batch_start

            self.logger.info(
                "Successfully processed %s in %.2fs",
                Path(image_path).name, proc_time
            )
            return image_path, success, proc_time, combined_metadata

        except Exception as e:
            proc_time = time.time() - batch_start
            self.logger.error(
                "Error processing %s: %s", image_path, e,
                exc_info=True
            )

            # Create minimal metadata for failed processing
            result_data = (
                self.metadata_combiner.create_minimal_metadata(
                    image_path, str(e)
                )
            )

            return image_path, False, proc_time, result_data

    def _save_result_to_yaml(
        self, image_path: str, result_data: Dict[str, Any]
    ) -> None:
        """Save processing result to YAML file.

        Args:
            image_path: Path to the processed image
            result_data: Processing result data
        """
        try:
            # Create output file path
            image_file = Path(image_path)
            output_path = (
                image_file.parent / f"{image_file.stem}.yml"
            )

            # Save to YAML file
            with open(output_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    result_data, f, default_flow_style=False,
                    allow_unicode=True, indent=2
                )

            self.logger.debug("Saved result to: %s", output_path)

        except Exception as e:
            self.logger.error(
                "Error saving result for %s: %s", image_path, e
            )
            raise

    def _update_stats(
        self, image_path: str, success: bool,
        processing_time: float,
        error: str = None
    ) -> None:
        """Update processing statistics.

        Args:
            image_path: Path to the processed image
            success: Whether processing was successful
            processing_time: Time taken to process the image
            error: Error message if processing failed
        """
        with self.stats_lock:
            self.processing_stats['processed_images'] += 1
            self.processing_stats['total_time'] += processing_time
            self.processing_stats['processing_times'].append(
                processing_time
            )

            if success:
                self.logger.debug(
                    "Successfully processed %s in %.3fs",
                    os.path.basename(image_path), processing_time
                )
            else:
                self.processing_stats['failed_images'] += 1
                if error:
                    self.processing_stats['errors'].append({
                        'image': image_path,
                        'error': error,
                        'time': processing_time
                    })

    def process_images_batch(
        self, image_files: List[str]
    ) -> Dict[str, Any]:
        """Process images in batch with threading support.

        Args:
            image_files: List of image file paths to process

        Returns:
            Processing statistics and results
        """
        if not image_files:
            self.logger.warning("No image files to process")
            return self.get_processing_report()

        # Initialize stats
        self.processing_stats['total_images'] = len(image_files)
        self.processing_stats['processed_images'] = 0
        self.processing_stats['failed_images'] = 0
        self.processing_stats['total_time'] = 0.0
        self.processing_stats['processing_times'] = []
        self.processing_stats['errors'] = []

        num_threads = self.config_manager.get_num_threads()
        show_progress = self.config_manager.is_progress_enabled()

        self.logger.info(
            "Starting batch processing of %s images "
            "using %s threads",
            len(image_files), num_threads
        )

        start_time = time.time()

        # Setup progress bar if enabled
        progress_bar = None
        if show_progress:
            progress_bar = tqdm(
                total=len(image_files),
                desc="Processing images",
                unit="img"
            )

        try:
            # Process images concurrently
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                # Submit all tasks
                future_to_image = {
                    executor.submit(
                        self.process_single_image, image_path
                    ): image_path
                    for image_path in image_files
                }

                # Process completed tasks
                for future in as_completed(future_to_image):
                    image_path = future_to_image[future]

                    try:
                        (img_path, success, proc_time,
                         result_data) = future.result()

                        # Update progress bar
                        if progress_bar:
                            progress_bar.set_postfix({
                                'current': os.path.basename(img_path),
                                'time': f'{proc_time:.2f}s'
                            })
                            progress_bar.update(1)

                        # Update statistics
                        error_msg = (
                            result_data.get('error')
                            if not success else None
                        )
                        self._update_stats(
                            img_path, success, proc_time, error_msg
                        )

                    except Exception as e:
                        self.logger.error(
                            "Unexpected error processing %s: %s",
                            image_path, e
                        )
                        self._update_stats(
                            image_path, False, 0.0, str(e)
                        )

                        if progress_bar:
                            progress_bar.update(1)

        finally:
            if progress_bar:
                progress_bar.close()

        total_batch_time = time.time() - start_time
        self.processing_stats['batch_time'] = total_batch_time

        # Generate and log final report
        report = self.get_processing_report()
        self._log_final_report(report)

        return report

    def get_processing_report(self) -> Dict[str, Any]:
        """Generate processing statistics report.

        Returns:
            Processing report dictionary
        """
        stats = self.processing_stats

        # Calculate averages
        avg_time = (
            (sum(stats['processing_times']) /
             len(stats['processing_times']))
            if stats['processing_times'] else 0.0
        )

        success_rate = (
            ((stats['processed_images'] - stats['failed_images']) /
             max(stats['processed_images'], 1)) * 100
        )

        report = {
            'summary': {
                'total_images': stats['total_images'],
                'processed_images': stats['processed_images'],
                'successful_images': (
                    stats['processed_images'] - stats['failed_images']
                ),
                'failed_images': stats['failed_images'],
                'success_rate': round(success_rate, 2)
            },
            'timing': {
                'total_processing_time': round(
                    stats['total_time'], 3
                ),
                'batch_time': round(
                    stats.get('batch_time', 0.0), 3
                ),
                'average_time_per_image': round(avg_time, 3),
                'min_time': (
                    round(min(stats['processing_times']), 3)
                    if stats['processing_times'] else 0.0
                ),
                'max_time': (
                    round(max(stats['processing_times']), 3)
                    if stats['processing_times'] else 0.0
                )
            },
            'errors': stats['errors']
        }

        return report

    def _log_final_report(self, report: Dict[str, Any]) -> None:
        """Log the final processing report.

        Args:
            report: Processing report dictionary
        """
        summary = report['summary']
        timing = report['timing']

        self.logger.info("=" * 60)
        self.logger.info("PROCESSING REPORT")
        self.logger.info("=" * 60)
        self.logger.info("Total images: %s", summary['total_images'])
        self.logger.info(
            "Successfully processed: %s",
            summary['successful_images']
        )
        self.logger.info("Failed: %s", summary['failed_images'])
        self.logger.info(
            "Success rate: %s%%", summary['success_rate']
        )
        self.logger.info("-" * 40)
        self.logger.info(
            "Total processing time: %ss",
            timing['total_processing_time']
        )
        self.logger.info(
            "Total batch time: %ss", timing['batch_time']
        )
        self.logger.info(
            "Average time per image: %ss",
            timing['average_time_per_image']
        )
        self.logger.info(
            "Min/Max time: %ss / %ss",
            timing['min_time'], timing['max_time']
        )

        if report['errors']:
            self.logger.info("-" * 40)
            self.logger.info("Errors (%s):", len(report['errors']))
            for error in report['errors']:
                self.logger.error(
                    "  %s: %s",
                    os.path.basename(error['image']),
                    error['error']
                )

        self.logger.info("=" * 60)
