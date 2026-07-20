"""
Pipeline parallel processor — assembly-line image processing.

Stages run concurrently across different images:

  OCR stage    →  vision_queue
  Vision stage →  text_queue
  Text stage   →  write_queue  (includes optional translation)
  Write stage  →  YAML on disk + job progress update

While image N is in the Vision stage, image N+1 is already in OCR,
and image N-1 is already in the Text stage.  Each stage owns exactly
one thread (configurable), so the slow LLM calls never block the fast
CPU-bound OCR work.

Drop-in replacement for the sequential loop inside process_job_folder().
"""

import logging
import queue
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from .job_manager import (
    add_processed_image,
    get_job,
    set_current_image,
    set_eta,
    set_progress,
    update_job_status,
)
from .pipeline.step_processor.single_image_processor import SingleImageProcessor

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel — pushed into a queue to tell the consumer to shut down
# ---------------------------------------------------------------------------
_SENTINEL = object()


# ---------------------------------------------------------------------------
# Per-image work item that travels through the pipeline
# ---------------------------------------------------------------------------
@dataclass
class _WorkItem:
    img_path: str
    state: Dict[str, Any]           # PipelineStateManager state dict
    ocr_data: Optional[Dict] = None
    vl_data: Optional[Dict] = None
    text_data: Optional[Dict] = None
    translation_data: Optional[Dict] = None
    error: Optional[str] = None     # set on failure; item still flows to write stage


# ---------------------------------------------------------------------------
# Shared progress counter (thread-safe) — throughput-based ETA
# ---------------------------------------------------------------------------
_ETA_WINDOW = 10   # use the last N completions for the rolling rate


@dataclass
class _Progress:
    total: int
    completed: int = 0              # includes pre-existing processed images
    lock: threading.Lock = field(default_factory=threading.Lock)
    # Ring buffer of (timestamp) for the last _ETA_WINDOW write completions
    _completion_times: List[float] = field(default_factory=list)

    def record_completion(self) -> tuple[int, float]:
        """
        Record one image exiting the write stage.
        Returns (total_completed, eta_seconds).

        ETA is derived from the observed throughput at the write stage —
        the rate at which finished images emerge — rather than wall-clock
        time divided by session images.  This is correct for a pipeline
        because multiple images are in-flight simultaneously; the write
        stage throughput already reflects the true end-to-end rate.

        A sliding window of the last _ETA_WINDOW completions smooths out
        the startup transient (the first few images are slow because all
        stages start cold) without letting early slowness skew the whole
        estimate once the pipeline is running at full speed.
        """
        now = time.monotonic()
        with self.lock:
            self.completed += 1
            self._completion_times.append(now)

            # Keep only the last N timestamps
            if len(self._completion_times) > _ETA_WINDOW:
                self._completion_times = self._completion_times[-_ETA_WINDOW:]

            remaining = self.total - self.completed
            eta = 0.0

            if remaining > 0 and len(self._completion_times) >= 2:
                # Throughput = images completed over the window duration
                window_duration = self._completion_times[-1] - self._completion_times[0]
                window_images = len(self._completion_times) - 1  # intervals, not points
                if window_duration > 0:
                    rate = window_images / window_duration   # images/second
                    eta = remaining / rate

            return self.completed, eta


# ---------------------------------------------------------------------------
# Stage workers
# ---------------------------------------------------------------------------

def _ocr_worker(
    job_id: str,
    stop_event: threading.Event,
    processor: SingleImageProcessor,
    pipeline_config: Dict,
    process_ocr: bool,
    in_queue: "queue.Queue[Any]",
    out_queue: "queue.Queue[Any]",
) -> None:
    """
    Pulls raw image paths from *in_queue*, runs OCR (if enabled),
    pushes _WorkItem to *out_queue*.
    """
    ocr_proc = processor._get_ocr_processor() if process_ocr else None

    while True:
        try:
            item = in_queue.get(timeout=0.2)
        except queue.Empty:
            if stop_event.is_set():
                out_queue.put(_SENTINEL)
                return
            continue

        if item is _SENTINEL:
            out_queue.put(_SENTINEL)
            return

        img_path: str = item  # raw paths arrive here
        work = _WorkItem(
            img_path=img_path,
            state=processor.state_manager.create_initial_state(img_path),
        )

        if stop_event.is_set():
            # Still forward — write stage handles the abort check
            out_queue.put(work)
            in_queue.task_done()
            continue

        set_current_image(job_id, img_path)

        if process_ocr and ocr_proc is not None:
            try:
                t0 = time.perf_counter()
                success, work.state = processor.step_processor.process_ocr_step(
                    img_path, work.state, ocr_proc, skip_if_completed=False
                )
                elapsed = time.perf_counter() - t0

                if processor.performance_stats:
                    processor.performance_stats.track_request(
                        request_type="ocr",
                        model_name="paddleocr",
                        processing_time=elapsed,
                    )

                if success:
                    ocr_step = (
                        work.state.get("pipeline_status", {})
                        .get("steps", {})
                        .get("ocr_processing", {})
                    )
                    work.ocr_data = ocr_step.get("data")
                else:
                    logger.warning(f"[OCR] failed for {Path(img_path).name}")
            except Exception as exc:
                logger.error(f"[OCR] exception for {img_path}: {exc}", exc_info=True)
                work.error = str(exc)

        out_queue.put(work)
        in_queue.task_done()


def _vision_worker(
    stop_event: threading.Event,
    processor: SingleImageProcessor,
    pipeline_config: Dict,
    process_vision: bool,
    vision_model: Optional[str],
    in_queue: "queue.Queue[Any]",
    out_queue: "queue.Queue[Any]",
) -> None:
    """
    Pulls _WorkItems from *in_queue*, runs image-agent analysis (if enabled),
    pushes enriched _WorkItem to *out_queue*.
    """
    image_agent = None
    if process_vision:
        image_agent = processor._get_image_agent()
        if vision_model:
            image_agent.vision_model = vision_model

    while True:
        try:
            work = in_queue.get(timeout=0.2)
        except queue.Empty:
            if stop_event.is_set():
                out_queue.put(_SENTINEL)
                return
            continue

        if work is _SENTINEL:
            out_queue.put(_SENTINEL)
            return

        if stop_event.is_set() or work.error:
            out_queue.put(work)
            in_queue.task_done()
            continue

        if process_vision and image_agent is not None:
            try:
                t0 = time.perf_counter()
                model_name = vision_model or image_agent.vision_model
                resize_spec = pipeline_config.get("image_resize", {})

                success, work.state = processor.step_processor.process_image_agent_step(
                    work.img_path, work.state, image_agent,
                    skip_if_completed=False,
                    resize_spec=resize_spec,
                )
                elapsed = time.perf_counter() - t0

                if processor.performance_stats:
                    processor.performance_stats.track_request(
                        request_type="image",
                        model_name=model_name,
                        processing_time=elapsed,
                    )

                if success:
                    vl_step = (
                        work.state.get("pipeline_status", {})
                        .get("steps", {})
                        .get("image_agent_analysis", {})
                    )
                    work.vl_data = vl_step.get("data")
                else:
                    logger.warning(f"[Vision] failed for {Path(work.img_path).name}")
            except Exception as exc:
                logger.error(f"[Vision] exception for {work.img_path}: {exc}", exc_info=True)
                work.error = str(exc)

        out_queue.put(work)
        in_queue.task_done()


def _text_worker(
    stop_event: threading.Event,
    processor: SingleImageProcessor,
    pipeline_config: Dict,
    process_text: bool,
    process_translation: bool,
    text_model: Optional[str],
    in_queue: "queue.Queue[Any]",
    out_queue: "queue.Queue[Any]",
) -> None:
    """
    Pulls _WorkItems, runs text-agent + optional translation, pushes to write queue.
    Text and translation are combined here because translation is cheap and
    depends directly on text output with no separate resource contention.
    """
    text_agent = None
    translator_agent = None

    if process_text:
        text_agent = processor._get_text_agent()
        if text_model:
            text_agent.text_model = text_model

    if process_translation:
        translator_agent = processor._get_translator_agent()

    while True:
        try:
            work = in_queue.get(timeout=0.2)
        except queue.Empty:
            if stop_event.is_set():
                out_queue.put(_SENTINEL)
                return
            continue

        if work is _SENTINEL:
            out_queue.put(_SENTINEL)
            return

        if stop_event.is_set() or work.error:
            out_queue.put(work)
            in_queue.task_done()
            continue

        # --- Text agent ---
        if process_text and text_agent is not None:
            try:
                t0 = time.perf_counter()
                model_name = text_model or text_agent.text_model

                success, work.state = processor.step_processor.process_text_agent_step(
                    work.img_path, work.state, text_agent, skip_if_completed=False
                )
                elapsed = time.perf_counter() - t0

                if processor.performance_stats:
                    processor.performance_stats.track_request(
                        request_type="text",
                        model_name=model_name,
                        processing_time=elapsed,
                    )

                if success:
                    text_step = (
                        work.state.get("pipeline_status", {})
                        .get("steps", {})
                        .get("text_agent_processing", {})
                    )
                    work.text_data = text_step.get("data")
                else:
                    logger.warning(f"[Text] failed for {Path(work.img_path).name}")
            except Exception as exc:
                logger.error(f"[Text] exception for {work.img_path}: {exc}", exc_info=True)
                work.error = str(exc)

        # --- Translation (only if text succeeded and needTranslation) ---
        if (
            process_translation
            and translator_agent is not None
            and work.text_data
            and work.text_data.get("needTranslation", False)
            and not work.error
        ):
            try:
                t0 = time.perf_counter()
                translator_model = getattr(translator_agent, "model", None) or text_model or "unknown"

                success, work.state = processor.step_processor.process_translation_step(
                    work.img_path, work.state, translator_agent, skip_if_completed=False
                )
                elapsed = time.perf_counter() - t0

                if processor.performance_stats:
                    processor.performance_stats.track_request(
                        request_type="translation",
                        model_name=translator_model,
                        processing_time=elapsed,
                    )

                if success:
                    trans_step = (
                        work.state.get("pipeline_status", {})
                        .get("steps", {})
                        .get("translation", {})
                    )
                    work.translation_data = trans_step.get("data")
            except Exception as exc:
                logger.error(f"[Translation] exception for {work.img_path}: {exc}", exc_info=True)
                # Non-fatal: don't set work.error, translation is optional

        out_queue.put(work)
        in_queue.task_done()


def _write_worker(
    job_id: str,
    stop_event: threading.Event,
    processor: SingleImageProcessor,
    progress: _Progress,
    in_queue: "queue.Queue[Any]",
    pending_list: List[str],  # Pass the ordered list of pending paths down
) -> None:
    """
    Pulls completed _WorkItems, combines metadata, writes YAML, updates job state.
    Single-threaded to avoid concurrent writes and to serialise progress tracking.
    """
    while True:
        try:
            work = in_queue.get(timeout=0.2)
        except queue.Empty:
            if stop_event.is_set():
                return
            continue

        if work is _SENTINEL:
            return

        img_path = work.img_path

        try:
            if work.error:
                logger.error(f"[Write] Skipping {img_path} due to upstream error: {work.error}")
                # Still count as completed so progress stays accurate
            else:
                # Combine metadata using the existing combiner
                total_time = (
                    work.state.get("metadata", {}).get("total_processing_time", 0.0)
                    or time.perf_counter()  # fallback; not precise here
                )
                metadata = processor.metadata_combiner.combine_metadata(
                    image_path=img_path,
                    ocr_data=work.ocr_data,
                    vl_model_data=work.vl_data,
                    text_processing=work.text_data,
                    translation_result=work.translation_data,
                    processing_time=total_time,
                )

                yml_path = Path(img_path).with_suffix(".yml")
                with open(yml_path, "w", encoding="utf-8") as fh:
                    yaml.dump(
                        metadata, fh,
                        allow_unicode=True,
                        default_flow_style=False,
                        sort_keys=False,
                    )
                logger.info(f"[Write] Saved {yml_path.name}")

            # --- Dynamically Extract Next 5 Images ---
            next5 = []
            try:
                # Find where the current image sits in the overall pending timeline
                idx = pending_list.index(img_path)
                # Slice the next 5 subsequent paths following this one
                next5 = pending_list[idx + 1 : idx + 6]
            except ValueError:
                # Fallback if image isn't found in the initial execution map
                next5 = []

            # Invoke updated version with the trailing lookahead array
            add_processed_image(job_id, img_path, next5images=next5)
            
            completed, eta = progress.record_completion()
            set_progress(job_id, (completed / progress.total) * 100)
            set_eta(job_id, int(eta) if (progress.total - completed) > 0 else 0)

        except Exception as exc:
            logger.error(f"[Write] Failed for {img_path}: {exc}", exc_info=True)

        finally:
            in_queue.task_done()


# ---------------------------------------------------------------------------
# Public entry point — replaces the sequential loop in process_job_folder()
# ---------------------------------------------------------------------------

def process_job_folder_parallel(
    job_id: str,
    folder_path: str,
    image_processor: SingleImageProcessor,
    stop_events: Dict[str, threading.Event],
    vision_model: Optional[str] = None,
    text_model: Optional[str] = None,
    *,
    queue_depth: int = 4,  # max items buffered between stages
) -> None:
    """
    Process all images in *folder_path* using a 4-stage assembly-line pipeline.

    Stages run in parallel across different images:
        OCR  →  Vision  →  Text (+Translation)  →  Write

    Args:
        job_id:          Job identifier.
        folder_path:     Root folder to scan for images.
        image_processor: Initialised SingleImageProcessor.
        stop_events:     Shared dict of stop events from job_worker.
        vision_model:    Override vision model name.
        text_model:      Override text model name.
        queue_depth:     Max items buffered between stages (back-pressure).
    """
    from .job_worker import get_image_files  # avoid circular at module level

    update_job_status(job_id, "running")
    stop_event = threading.Event()
    stop_events[job_id] = stop_event

    # ------------------------------------------------------------------ #
    # Gather images, skip already-done ones
    # ------------------------------------------------------------------ #
    all_images = get_image_files(folder_path)
    total_images = len(all_images)

    if total_images == 0:
        update_job_status(job_id, "completed")
        set_progress(job_id, 100)
        return

    job_data = get_job(job_id)
    processed = set(job_data.get("processed_images", []))

    # Fast-track images whose sidecar already exists
    for img in all_images:
        if Path(img).with_suffix(".yml").exists() and img not in processed:
            add_processed_image(job_id, img)
            processed.add(img)

    pending: List[str] = [
        img for img in all_images
        if img not in processed and not Path(img).with_suffix(".yml").exists()
    ]

    if not pending:
        update_job_status(job_id, "completed")
        set_progress(job_id, 100)
        return

    # ------------------------------------------------------------------ #
    # Pipeline flags from config
    # ------------------------------------------------------------------ #
    pipeline_config = image_processor.config_manager.config.get("pipeline", {})
    process_ocr = pipeline_config.get("enable_ocr", False)
    process_vision = pipeline_config.get("enable_image_agent", True)
    process_text = pipeline_config.get("enable_text_agent", True)
    process_translation = pipeline_config.get("enable_translation", False)

    # ------------------------------------------------------------------ #
    # Build inter-stage queues
    # ------------------------------------------------------------------ #
    ocr_queue: "queue.Queue[Any]" = queue.Queue(maxsize=queue_depth)
    vision_queue: "queue.Queue[Any]" = queue.Queue(maxsize=queue_depth)
    text_queue: "queue.Queue[Any]" = queue.Queue(maxsize=queue_depth)
    write_queue: "queue.Queue[Any]" = queue.Queue(maxsize=queue_depth)

    progress = _Progress(
        total=total_images,
        completed=len(processed),
    )

    # ------------------------------------------------------------------ #
    # Start stage threads
    # ------------------------------------------------------------------ #
    threads = [
        threading.Thread(
            target=_ocr_worker,
            name=f"pipeline-ocr-{job_id}",
            args=(job_id, stop_event, image_processor, pipeline_config,
                  process_ocr, ocr_queue, vision_queue),
            daemon=True,
        ),
        threading.Thread(
            target=_vision_worker,
            name=f"pipeline-vision-{job_id}",
            args=(stop_event, image_processor, pipeline_config,
                  process_vision, vision_model, vision_queue, text_queue),
            daemon=True,
        ),
        threading.Thread(
            target=_text_worker,
            name=f"pipeline-text-{job_id}",
            args=(stop_event, image_processor, pipeline_config,
                  process_text, process_translation, text_model,
                  text_queue, write_queue),
            daemon=True,
        ),
        threading.Thread(
            target=_write_worker,
            name=f"pipeline-write-{job_id}",
            args=(job_id, stop_event, image_processor, progress, write_queue,
                  pending),
            daemon=True,
        ),
    ]

    for t in threads:
        t.start()

    # ------------------------------------------------------------------ #
    # Feed images into the pipeline
    # ------------------------------------------------------------------ #
    try:
        for img_path in pending:
            if stop_event.is_set():
                break
            # Blocks when the OCR queue is full — natural back-pressure
            ocr_queue.put(img_path)

        # Signal the chain to shut down once all items are drained
        ocr_queue.put(_SENTINEL)

    except Exception as exc:
        logger.error(f"Job {job_id} feeder error: {exc}", exc_info=True)
        stop_event.set()
        ocr_queue.put(_SENTINEL)  # ensure workers can exit

    # ------------------------------------------------------------------ #
    # Wait for all stages to finish
    # ------------------------------------------------------------------ #
    for t in threads:
        t.join()

    # ------------------------------------------------------------------ #
    # Final job status
    # ------------------------------------------------------------------ #
    current_job = get_job(job_id)
    if stop_event.is_set() and current_job.get("status") != "cancelled":
        update_job_status(job_id, "paused")
    else:
        update_job_status(job_id, "completed")
        set_progress(job_id, 100)