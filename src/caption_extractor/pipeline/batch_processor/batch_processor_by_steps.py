"""Batch image processing organized by pipeline steps.

This processor handles batch processing where all images complete each step
before moving to the next. This optimizes local LLM usage by loading each
model once, processing all images, then unloading before loading the next.
"""

import os
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

from ...pipeline_state_manager import PipelineStateManager
from ..step_processor.step_processor import StepProcessor
from ..metadata_combiner.metadata_combiner import MetadataCombiner


class BatchProcessorBySteps:
    """Process images through each pipeline step sequentially.

    Instead of image-by-image processing (which reloads models for each
    image), this processes all images through Step 1, then all images
    through Step 2, etc. Optimal for local LLM models.
    """

    def __init__(self, config_manager, ocr_processor=None,
                 image_agent=None, text_agent=None,
                 translator_agent=None):
        """Initialize the step-based batch processor.

        Args:
            config_manager: Configuration manager instance
            ocr_processor: OCR processor instance (optional)
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

        # Get batch processing configuration
        batch_config = config_manager.config.get('batch_processing', {})
        self.num_threads = batch_config.get('num_threads_per_step', 1)
        self.show_progress = batch_config.get('show_progress', True)

        self.logger.info(
            "BatchProcessorBySteps initialized - OCR: %s, "
            "Image Agent: %s, Text Agent: %s, Translation: %s",
            self.enable_ocr, self.enable_image_agent,
            self.enable_text_agent, self.enable_translation
        )

        self.processing_stats = {
            'total_images': 0,
            'steps_completed': [],
            'step_stats': {},
            'total_time': 0.0,
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

        except Exception as err:
            self.logger.error(
                "Error scanning folder %s: %s", folder_path, err
            )
            return []

    def _process_step_for_images(self, step_name: str,
                                 image_files: List[str],
                                 step_function, *args) -> Dict[str, Any]:
        """Process a single step for all images.

        Args:
            step_name: Name of the step (for logging)
            image_files: List of image files to process
            step_function: Function to call for each image
            *args: Arguments for step function

        Returns:
            Step statistics
        """
        step_stats = {
            'name': step_name,
            'total': len(image_files),
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'total_time': 0.0,
            'processing_times': [],
            'errors': []
        }

        start_time = time.time()

        self.logger.info("=" * 60)
        self.logger.info("Processing step: %s for %s images",
                         step_name, len(image_files))
        self.logger.info("Using %s threads for parallel processing",
                         self.num_threads)
        self.logger.info("=" * 60)

        # Setup progress bar if enabled
        progress_bar = None
        if self.show_progress and TQDM_AVAILABLE:
            progress_bar = tqdm(
                total=len(image_files),
                desc="Processing " + step_name,
                unit="img"
            )

        try:
            # Process images in parallel for this step
            with ThreadPoolExecutor(
                max_workers=self.num_threads
            ) as executor:
                future_to_image = {
                    executor.submit(step_function, image_path,
                                    *args): image_path
                    for image_path in image_files
                }

                for future in as_completed(future_to_image):
                    image_path = future_to_image[future]

                    try:
                        success, state, proc_time = future.result()
                        step_stats['processing_times'].append(proc_time)

                        if success:
                            step_status = (
                                state.get('pipeline_status', {})
                                .get('steps', {})
                                .get(step_name, {})
                            )
                            if (step_status.get('status') ==
                                    'skipped'):
                                step_stats['skipped'] += 1
                                status = "SKIPPED"
                            else:
                                step_stats['successful'] += 1
                                status = "OK"
                        else:
                            step_stats['failed'] += 1
                            status = "FAILED"
                            error_msg = (
                                state.get('pipeline_status', {})
                                .get('steps', {})
                                .get(step_name, {})
                                .get('error', 'Unknown error')
                            )
                            step_stats['errors'].append({
                                'image': image_path,
                                'error': error_msg,
                                'time': proc_time
                            })

                        if progress_bar:
                            progress_bar.set_postfix({
                                'file': os.path.basename(image_path),
                                'time': f'{proc_time:.2f}s',
                                'status': status
                            })
                            progress_bar.update(1)

                    except Exception as err:
                        self.logger.error(
                            "Error processing %s: %s",
                            image_path, err
                        )
                        step_stats['failed'] += 1
                        step_stats['errors'].append({
                            'image': image_path,
                            'error': str(err),
                            'time': 0.0
                        })

                        if progress_bar:
                            progress_bar.update(1)

        finally:
            if progress_bar:
                progress_bar.close()

        step_stats['total_time'] = time.time() - start_time

        # Log step summary
        self._log_step_summary(step_stats)

        return step_stats

    def _process_ocr_for_image(self, image_path: str
                               ) -> Tuple[bool, Dict[str, Any], float]:
        """Process OCR step for single image."""
        batch_start = time.time()

        try:
            # Load or create state
            state = self.state_manager.load_state(image_path)
            if not state:
                state = self.state_manager.create_initial_state(
                    image_path
                )

            # Process OCR step
            success, state = self.step_processor.process_ocr_step(
                image_path, state, self.ocr_processor
            )

            # Save state
            self.state_manager.save_state(image_path, state)

            proc_time = time.time() - batch_start
            return success, state, proc_time

        except Exception as err:
            self.logger.error(
                "Error in OCR processing for %s: %s",
                image_path, err
            )
            proc_time = time.time() - batch_start
            state = {}
            return False, state, proc_time

    def _process_image_agent_for_image(
        self, image_path: str, resize_spec: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], float]:
        """Process image agent step for single image."""
        batch_start = time.time()

        try:
            # Load state
            state = self.state_manager.load_state(image_path)
            if not state:
                state = self.state_manager.create_initial_state(
                    image_path
                )

            # Process image agent step
            success, state = self.step_processor.process_image_agent_step(
                image_path, state, self.image_agent,
                resize_spec=resize_spec
            )

            # Save state
            self.state_manager.save_state(image_path, state)

            proc_time = time.time() - batch_start
            return success, state, proc_time

        except Exception as err:
            self.logger.error(
                "Error in image agent processing for %s: %s",
                image_path, err
            )
            proc_time = time.time() - batch_start
            state = {}
            return False, state, proc_time

    def _process_text_agent_for_image(
        self, image_path: str
    ) -> Tuple[bool, Dict[str, Any], float]:
        """Process text agent step for single image."""
        batch_start = time.time()

        try:
            # Load state
            state = self.state_manager.load_state(image_path)
            if not state:
                state = self.state_manager.create_initial_state(
                    image_path
                )

            # Process text agent step
            success, state = self.step_processor.process_text_agent_step(
                image_path, state, self.text_agent
            )

            # Save state
            self.state_manager.save_state(image_path, state)

            proc_time = time.time() - batch_start
            return success, state, proc_time

        except Exception as err:
            self.logger.error(
                "Error in text agent processing for %s: %s",
                image_path, err
            )
            proc_time = time.time() - batch_start
            state = {}
            return False, state, proc_time

    def _process_translation_for_image(
        self, image_path: str
    ) -> Tuple[bool, Dict[str, Any], float]:
        """Process translation step for single image."""
        batch_start = time.time()

        try:
            # Load state
            state = self.state_manager.load_state(image_path)
            if not state:
                state = self.state_manager.create_initial_state(
                    image_path
                )

            # Process translation step
            success, state = self.step_processor.process_translation_step(
                image_path, state, self.translator_agent
            )

            # Save state
            self.state_manager.save_state(image_path, state)

            proc_time = time.time() - batch_start
            return success, state, proc_time

        except Exception as err:
            self.logger.error(
                "Error in translation processing for %s: %s",
                image_path, err
            )
            proc_time = time.time() - batch_start
            state = {}
            return False, state, proc_time

    def _process_metadata_for_image(
        self, image_path: str
    ) -> Tuple[bool, Dict[str, Any], float]:
        """Process metadata combination step for single image."""
        batch_start = time.time()

        try:
            # Load state
            state = self.state_manager.load_state(image_path)
            if not state:
                state = self.state_manager.create_initial_state(
                    image_path
                )

            # Process metadata combination step
            success, state = (
                self.step_processor.process_metadata_combination_step(
                    image_path, state, self.metadata_combiner
                )
            )

            # Mark pipeline as completed
            state = self.state_manager.mark_pipeline_completed(state)

            # Save state
            self.state_manager.save_state(image_path, state)

            proc_time = time.time() - batch_start
            return success, state, proc_time

        except Exception as err:
            self.logger.error(
                "Error in metadata processing for %s: %s",
                image_path, err
            )
            proc_time = time.time() - batch_start
            state = {}
            return False, state, proc_time

    def process_images_batch_by_steps(
        self, image_files: List[str]
    ) -> Dict[str, Any]:
        """Process images in batch, organized by steps.

        Each step is applied to all images before moving to next step.

        Args:
            image_files: List of image file paths to process

        Returns:
            Processing statistics and results
        """
        if not image_files:
            self.logger.warning("No image files to process")
            return self.get_processing_report()

        self.processing_stats['total_images'] = len(image_files)
        self.processing_stats['steps_completed'] = []
        self.processing_stats['step_stats'] = {}
        self.processing_stats['total_time'] = 0.0
        self.processing_stats['errors'] = []

        overall_start = time.time()

        # Get resize spec once for image agent step
        resize_spec = (
            self.config_manager.get_image_resize_spec()
        )

        self.logger.info(
            "Starting batch processing by steps for %s images",
            len(image_files)
        )

        # Step 1: OCR Processing
        if self.enable_ocr and self.ocr_processor:
            self.logger.info("STEP 1: OCR PROCESSING")

            step_stats = self._process_step_for_images(
                'ocr_processing',
                image_files,
                self._process_ocr_for_image
            )
            self.processing_stats['step_stats']['ocr'] = step_stats
            self.processing_stats['steps_completed'].append('ocr')

        # Step 2: Image Agent Analysis
        if self.enable_image_agent and self.image_agent:
            self.logger.info("STEP 2: IMAGE AGENT ANALYSIS")

            step_stats = self._process_step_for_images(
                'image_agent_analysis',
                image_files,
                self._process_image_agent_for_image,
                resize_spec
            )
            self.processing_stats['step_stats']['image_agent'] = (
                step_stats
            )
            self.processing_stats['steps_completed'].append(
                'image_agent'
            )

        # Step 3: Text Agent Processing
        if self.enable_text_agent and self.text_agent:
            self.logger.info("STEP 3: TEXT AGENT PROCESSING")

            step_stats = self._process_step_for_images(
                'text_agent_processing',
                image_files,
                self._process_text_agent_for_image
            )
            self.processing_stats['step_stats']['text_agent'] = (
                step_stats
            )
            self.processing_stats['steps_completed'].append(
                'text_agent'
            )

        # Step 4: Translation
        if self.enable_translation and self.translator_agent:
            self.logger.info("STEP 4: TRANSLATION")

            step_stats = self._process_step_for_images(
                'translation',
                image_files,
                self._process_translation_for_image
            )
            self.processing_stats['step_stats']['translation'] = (
                step_stats
            )
            self.processing_stats['steps_completed'].append(
                'translation'
            )

        # Step 5: Metadata Combination
        self.logger.info("STEP 5: METADATA COMBINATION")

        step_stats = self._process_step_for_images(
            'metadata_combination',
            image_files,
            self._process_metadata_for_image
        )
        self.processing_stats['step_stats']['metadata'] = step_stats
        self.processing_stats['steps_completed'].append('metadata')

        self.processing_stats['total_time'] = (
            time.time() - overall_start
        )

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

        # Calculate aggregate statistics
        step_details = []
        for step_name, step_stat in stats['step_stats'].items():
            avg_time = (
                (sum(step_stat['processing_times']) /
                 len(step_stat['processing_times']))
                if step_stat['processing_times'] else 0.0
            )

            step_details.append({
                'step': step_name,
                'total': step_stat['total'],
                'successful': step_stat['successful'],
                'failed': step_stat['failed'],
                'skipped': step_stat['skipped'],
                'total_time': round(step_stat['total_time'], 3),
                'average_time': round(avg_time, 3)
            })

        report = {
            'summary': {
                'total_images': stats['total_images'],
                'total_steps_completed': len(stats['steps_completed']),
                'steps': stats['steps_completed']
            },
            'steps': step_details,
            'timing': {
                'total_processing_time': round(
                    stats['total_time'], 3
                )
            },
            'errors': stats['errors']
        }

        return report

    def _log_step_summary(self, step_stats: Dict[str, Any]) -> None:
        """Log summary for a single step."""
        self.logger.info("-" * 60)
        self.logger.info("Step: %s Summary", step_stats['name'])
        self.logger.info(
            "Total: %s | Successful: %s | Failed: %s | Skipped: %s",
            step_stats['total'],
            step_stats['successful'],
            step_stats['failed'],
            step_stats['skipped']
        )

        avg_time = (
            (sum(step_stats['processing_times']) /
             len(step_stats['processing_times']))
            if step_stats['processing_times'] else 0.0
        )

        self.logger.info(
            "Total time: %ss | Average time: %ss",
            round(step_stats['total_time'], 2),
            round(avg_time, 2)
        )

        if step_stats['errors']:
            self.logger.warning(
                "Errors in this step: %s",
                len(step_stats['errors'])
            )

        self.logger.info("-" * 60)

    def _log_final_report(self, report: Dict[str, Any]) -> None:
        """Log the final processing report."""
        self.logger.info("FINAL PROCESSING REPORT")
        self.logger.info("=" * 60)

        summary = report['summary']
        self.logger.info("Total images: %s", summary['total_images'])
        self.logger.info("Steps completed: %s",
                         ', '.join(summary['steps']))

        self.logger.info("-" * 60)
        self.logger.info("Step-by-Step Summary:")
        self.logger.info("-" * 60)

        for step in report['steps']:
            self.logger.info(
                "%s: %s/%s successful, %s failed, %s skipped "
                "(%.2fs, avg: %.2fs)",
                step['step'],
                step['successful'],
                step['total'],
                step['failed'],
                step['skipped'],
                step['total_time'],
                step['average_time']
            )

        self.logger.info("-" * 60)
        timing = report['timing']
        self.logger.info(
            "Total processing time: %ss",
            timing['total_processing_time']
        )

        if report['errors']:
            self.logger.info("-" * 60)
            self.logger.info("Errors (%s):", len(report['errors']))
            for error in report['errors']:
                self.logger.error(
                    "  %s: %s",
                    os.path.basename(error['image']),
                    error['error']
                )

        self.logger.info("=" * 60)
