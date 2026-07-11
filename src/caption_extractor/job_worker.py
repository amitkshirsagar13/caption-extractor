import os
import threading
import time
import logging
from pathlib import Path
from typing import Optional
import yaml

from .job_manager import get_job, update_job_status, add_processed_image, set_progress, set_current_image
from .pipeline.step_processor.single_image_processor import SingleImageProcessor

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
    text_model: Optional[str] = None
):
    try:
        update_job_status(job_id, "running")
        stop_events[job_id] = threading.Event()
        
        all_images = get_image_files(folder_path)
        total_images = len(all_images)
        
        if total_images == 0:
            update_job_status(job_id, "completed")
            set_progress(job_id, 100)
            return

        job_data = get_job(job_id)
        processed = set(job_data.get("processed_images", []))
        
        # Count progress
        completed_count = len(processed)
        
        for img_path in all_images:
            if stop_events[job_id].is_set():
                current_job = get_job(job_id)
                if current_job.get("status") != "cancelled":
                    update_job_status(job_id, "paused")
                return

            if img_path in processed:
                continue

            try:
                set_current_image(job_id, img_path)
                logger.info(f"Job {job_id} processing {img_path}")
                result = image_processor.process_image(
                    image_path=img_path,
                    enable_ocr=None,
                    enable_image_agent=None,
                    enable_text_agent=None,
                    enable_translation=None,
                    vision_model=vision_model,
                    text_model=text_model
                )

                # Save extraction result as YAML next to the image
                try:
                    yml_path = Path(img_path).with_suffix(".yml")
                    with open(yml_path, "w", encoding="utf-8") as f:
                        yaml.dump(result, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
                    logger.info(f"Saved extraction result to {yml_path}")
                except Exception as yml_err:
                    logger.error(f"Failed to write YAML for {img_path}: {yml_err}")

                add_processed_image(job_id, img_path)
                completed_count += 1
                
                percent = (completed_count / total_images) * 100
                set_progress(job_id, percent)
                
            except Exception as e:
                logger.error(f"Error processing {img_path} in job {job_id}: {e}")
                # We can choose to halt or continue on error. Let's continue.

        update_job_status(job_id, "completed")
        set_progress(job_id, 100)

    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}")
        update_job_status(job_id, "cancelled")
    finally:
        active_workers.pop(job_id, None)
        stop_events.pop(job_id, None)
        # Check if there is another queued job to run
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
