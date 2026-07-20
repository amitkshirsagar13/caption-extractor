import os
import threading
import logging
from pathlib import Path
from typing import Optional

from .job_manager import get_job, update_job_status, add_processed_image, set_progress, set_current_image, set_eta
from .pipeline.step_processor.single_image_processor import SingleImageProcessor
from .pipeline_parallel_processor import process_job_folder_parallel

logger = logging.getLogger(__name__)

# Keep track of active threads to allow pausing
active_workers = {}
# Use an event to signal workers to stop or pause
stop_events = {}

def check_and_start_next_job(processor: SingleImageProcessor):
    from .job_manager import list_jobs
    jobs = list_jobs()
    running = [j for j in jobs if j.get("status") == "running"]
    if running:
        return # A job is already running, so keep the rest queued

    # Find the oldest queued job
    queued = sorted([j for j in jobs if j.get("status") == "queued"], key=lambda x: x.get("created_at", 0))
    if queued:
        next_job = queued[0]
        _start_thread(next_job["job_id"], next_job["folder_path"], processor)

def _start_thread(job_id: str, folder_path: str, processor: SingleImageProcessor):
    if job_id in active_workers:
        return # already running
    
    thread = threading.Thread(
        target=process_job_folder, 
        args=(job_id, folder_path, processor),
        daemon=True
    )
    active_workers[job_id] = thread
    thread.start()

def is_image_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}

def get_image_files(folder_path: str) -> list[str]:
    folder = Path(folder_path)
    if not folder.exists() or not folder.is_dir():
        return []
    
    images = []
    # Recursive search
    for p in folder.rglob("*"):
        if p.is_file() and is_image_file(p.name):
            images.append(str(p))
    return images

def process_job_folder(
    job_id: str,
    folder_path: str,
    image_processor: SingleImageProcessor,
    vision_model: Optional[str] = None,
    text_model: Optional[str] = None,
):
    """Process a job folder using the parallel assembly-line pipeline."""
    try:
        process_job_folder_parallel(
            job_id=job_id,
            folder_path=folder_path,
            image_processor=image_processor,
            stop_events=stop_events,
            vision_model=vision_model,
            text_model=text_model,
        )
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        update_job_status(job_id, "cancelled")
    finally:
        active_workers.pop(job_id, None)
        stop_events.pop(job_id, None)
        check_and_start_next_job(image_processor)

def start_job_worker(job_id: str, folder_path: str, processor: SingleImageProcessor):
    check_and_start_next_job(processor)

def pause_job(job_id: str):
    job_data = get_job(job_id)
    if job_data.get("status") == "queued":
        update_job_status(job_id, "paused")
    if job_id in stop_events:
        stop_events[job_id].set()

def cancel_job(job_id: str):
    update_job_status(job_id, "cancelled")
    if job_id in stop_events:
        stop_events[job_id].set()

def resume_job(job_id: str, processor: SingleImageProcessor):
    job_data = get_job(job_id)
    if job_data["status"] == "paused":
        update_job_status(job_id, "queued")
        check_and_start_next_job(processor)