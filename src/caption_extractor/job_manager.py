import json
import os
import threading
import time
from pathlib import Path
from typing import List, Dict, Any

# Directory to store job state files
JOBS_DIR = Path(__file__).parent.parent / ".jobs"
JOBS_DIR.mkdir(exist_ok=True)

job_locks: Dict[str, threading.Lock] = {}

def _load_job(job_id: str) -> Dict[str, Any]:
    job_file = JOBS_DIR / f"{job_id}.json"
    if not job_file.exists():
        raise FileNotFoundError(f"Job {job_id} not found")
    with job_file.open("r", encoding="utf-8") as f:
        return json.load(f)

def _save_job(job_id: str, data: Dict[str, Any]):
    job_file = JOBS_DIR / f"{job_id}.json"
    with job_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def create_job(folder_path: str) -> str:
    """Create a new job and return its ID."""
    job_id = str(int(time.time() * 1000))  # simple timestamp based id
    job_data = {
        "job_id": job_id,
        "folder_path": folder_path,
        "status": "queued",  # queued | running | paused | completed | cancelled
        "processed_images": [],
        "progress_percent": 0,
        "created_at": time.time(),
        "updated_at": time.time()
    }
    _save_job(job_id, job_data)
    job_locks[job_id] = threading.Lock()
    return job_id

def get_job(job_id: str) -> Dict[str, Any]:
    return _load_job(job_id)

def update_job_status(job_id: str, status: str):
    lock = job_locks.get(job_id)
    if not lock:
        lock = threading.Lock()
        job_locks[job_id] = lock
    with lock:
        job = _load_job(job_id)
        job["status"] = status
        job["updated_at"] = time.time()
        _save_job(job_id, job)

def add_processed_image(job_id: str, image_path: str):
    lock = job_locks.get(job_id)
    if not lock:
        lock = threading.Lock()
        job_locks[job_id] = lock
    with lock:
        job = _load_job(job_id)
        processed: List[str] = job.get("processed_images", [])
        processed.append(image_path)
        job["processed_images"] = processed
        # Update progress percent based on total images count if known
        job["updated_at"] = time.time()
        _save_job(job_id, job)

def set_progress(job_id: str, percent: float):
    lock = job_locks.get(job_id)
    if not lock:
        lock = threading.Lock()
        job_locks[job_id] = lock
    with lock:
        job = _load_job(job_id)
        job["progress_percent"] = percent
        job["updated_at"] = time.time()
        _save_job(job_id, job)

def set_current_image(job_id: str, image_path: str):
    """Update the currently-processing image path in the job state."""
    lock = job_locks.get(job_id)
    if not lock:
        lock = threading.Lock()
        job_locks[job_id] = lock
    with lock:
        job = _load_job(job_id)
        job["current_image"] = image_path
        job["updated_at"] = time.time()
        _save_job(job_id, job)

def list_jobs() -> List[Dict[str, Any]]:
    jobs = []
    for file in JOBS_DIR.glob("*.json"):
        with file.open("r", encoding="utf-8") as f:
            jobs.append(json.load(f))
    return jobs
