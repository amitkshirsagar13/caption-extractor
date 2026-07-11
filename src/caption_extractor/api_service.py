"""FastAPI service for image processing API."""

import os
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Request, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from .config_manager import ConfigManager
from .pipeline.step_processor.single_image_processor import SingleImageProcessor
from .performance import PerformanceStatsManager
from .job_manager import list_jobs, create_job, get_job
from .job_worker import start_job_worker, pause_job, resume_job, cancel_job, is_image_file


# Get logger - logging will be configured by ConfigManager
logger = logging.getLogger(__name__)


# Request/Response Models
class ProcessingOptions(BaseModel):
    """Processing pipeline options."""
    enable_ocr: Optional[bool] = Field(
        None, 
        description="Enable OCR text extraction (default: from config)"
    )
    enable_image_agent: Optional[bool] = Field(
        None,
        description="Enable image analysis using vision model (default: from config)"
    )
    enable_text_agent: Optional[bool] = Field(
        None,
        description="Enable text processing/correction (default: from config)"
    )
    enable_translation: Optional[bool] = Field(
        None,
        description="Enable translation to English (default: from config)"
    )
    vision_model: Optional[str] = Field(
        None,
        description="Vision model name (e.g., 'gemma3:latest', 'llava:latest')"
    )
    text_model: Optional[str] = Field(
        None,
        description="Text model name (e.g., 'mistral:latest', 'llama3.2:latest')"
    )


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="API version")
    config_loaded: bool = Field(..., description="Configuration status")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")

class JobCreateRequest(BaseModel):
    folder_path: str


# Initialize FastAPI app
app = FastAPI(
    title="Caption Extractor API",
    description="Extract and analyze text from images using OCR and AI agents",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Global state
config_manager: Optional[ConfigManager] = None
image_processor: Optional[SingleImageProcessor] = None
performance_stats: Optional[PerformanceStatsManager] = None

# Templates configuration
def get_project_root():
    return Path(__file__).parent

templates = Jinja2Templates(directory=str(get_project_root() / "templates"))


def initialize_services(config_path: str = "config.yml"):
    """Initialize configuration and services.
    
    Args:
        config_path: Path to configuration file
    """
    global config_manager, image_processor, performance_stats
    
    try:
        logger.info(f"Loading configuration from: {config_path}")
        config_manager = ConfigManager(config_path)
        
        logger.info("Initializing performance statistics manager")
        performance_stats = PerformanceStatsManager(config_manager.config)
        
        logger.info("Initializing image processor")
        image_processor = SingleImageProcessor(config_manager, performance_stats)
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Mount static files
        static_path = get_project_root() / "static"
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

        # Look for config.yml in current directory or parent directories
        config_path = "config.yml"
        if not os.path.exists(config_path):
            # Try parent directory
            parent_config = Path(__file__).parent.parent.parent / "config.yml"
            if parent_config.exists():
                config_path = str(parent_config)
        
        initialize_services(config_path)
        
        # Start periodic performance logging if enabled
        if performance_stats:
            performance_stats.start_periodic_logging()
        
        logger.info("FastAPI application started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        # Don't fail startup, but services won't be available


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down FastAPI application")
    
    if performance_stats:
        performance_stats.shutdown()


@app.get("/", response_class=HTMLResponse)  # ← correct response class
async def root(request: Request):
    return templates.TemplateResponse(
        request=request,           # ← new Starlette API (>=0.36)
        name="index.html",
        context={
            "status": "running",
            "version": "1.0.0",
            "config_loaded": config_manager is not None
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if config_manager is not None else "degraded",
        version="1.0.0",
        config_loaded=config_manager is not None
    )


@app.post("/process", response_model=Dict[str, Any])
async def process_image(
    file: UploadFile = File(..., description="Image file to process"),
    enable_ocr: Optional[bool] = Form(None, description="Enable OCR processing"),
    enable_image_agent: Optional[bool] = Form(None, description="Enable image analysis"),
    enable_text_agent: Optional[bool] = Form(None, description="Enable text processing"),
    enable_translation: Optional[bool] = Form(None, description="Enable translation"),
    vision_model: Optional[str] = Form(None, description="Vision model name"),
    text_model: Optional[str] = Form(None, description="Text model name")
):
    """Process an uploaded image through the caption extraction pipeline.
    
    Upload an image and optionally configure which processing steps to run.
    By default, uses configuration from config.yml.
    
    Args:
        file: Image file to process
        enable_ocr: Enable OCR text extraction
        enable_image_agent: Enable AI vision model analysis
        enable_text_agent: Enable text correction/completion
        enable_translation: Enable translation to English
        vision_model: Override default vision model
        text_model: Override default text model
        
    Returns:
        JSON response with extracted metadata including OCR results,
        image analysis, text processing, and translations
    """
    if config_manager is None or image_processor is None:
        raise HTTPException(
            status_code=503,
            detail="Service not initialized. Configuration may be missing."
        )
    
    # Validate file type
    if not file.content_type or not file.content_type.startswith('image/'):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Please upload an image file."
        )
    
    temp_file_path = None
    
    try:
        # Create temporary file to store uploaded image
        suffix = Path(file.filename).suffix if file.filename else '.jpg'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file_path = temp_file.name
            
            # Write uploaded file to disk
            content = await file.read()
            temp_file.write(content)
            
            logger.info(
                f"Processing uploaded image: {file.filename} "
                f"({len(content)} bytes) -> {temp_file_path}"
            )

            if vision_model == "string": 
                vision_model = "gemma3:latest"
            if text_model == "string":
                text_model = "mistral:latest"
        
        # Process the image
        result = image_processor.process_image(
            image_path=temp_file_path,
            enable_ocr=enable_ocr,
            enable_image_agent=enable_image_agent,
            enable_text_agent=enable_text_agent,
            enable_translation=enable_translation,
            vision_model=vision_model,
            text_model=text_model
        )
        
        # Update image filename in result
        if result:
            result['image_file'] = file.filename
            result['original_filename'] = file.filename
        
        logger.info(f"Successfully processed: {file.filename}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing image: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process image: {str(e)}"
        )
        
    finally:
        # Cleanup temporary file
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.remove(temp_file_path)
                logger.debug(f"Removed temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {temp_file_path}: {e}")


@app.get("/debug")
async def debug_info():
    """Get debug information about the service state."""
    import sys
    import paddle
    
    info = {
        "python_version": sys.version,
        "config_loaded": config_manager is not None,
        "processor_initialized": image_processor is not None,
    }
    
    if config_manager:
        info["ocr_config"] = config_manager.config.get('ocr', {})
        info["pipeline_config"] = config_manager.config.get('pipeline', {})
        info["ollama_host"] = config_manager.config.get('ollama', {}).get('host')
        
    try:
        info["paddle_version"] = paddle.__version__
    except:
        info["paddle_version"] = "not available"
        
    return info


@app.get("/config")
async def get_config():
    """Get current pipeline configuration.
    
    Returns the current configuration including enabled pipeline steps
    and model settings.
    """
    if config_manager is None:
        raise HTTPException(
            status_code=503,
            detail="Configuration not loaded"
        )
    
    pipeline_config = config_manager.config.get('pipeline', {})
    ollama_config = config_manager.config.get('ollama', {})
    models = ollama_config.get('models', {})
    
    return {
        "pipeline": {
            "enable_ocr": pipeline_config.get('enable_ocr', False),
            "enable_image_agent": pipeline_config.get('enable_image_agent', True),
            "enable_text_agent": pipeline_config.get('enable_text_agent', True),
            "enable_translation": pipeline_config.get('enable_translation', False)
        },
        "models": {
            "vision_model": models.get('vision_model', 'gemma3'),
            "text_model": models.get('text_model', 'mistral:latest')
        },
        "ollama": {
            "host": ollama_config.get('host', 'http://localhost:11434'),
            "timeout": ollama_config.get('timeout', 120)
        }
    }


@app.get("/models")
async def get_available_models():
    """Get information about available models.
    
    Returns suggested models for vision and text processing.
    """
    return {
        "vision_models": [
            "qwen3-vl:235b-cloud",
            "qwen3-vl:4b",
            "llava:latest",
            "llava:13b",
            "bakllava",
            "ministral-3:latest"
        ],
        "text_models": [
            "mistral:latest",
            "llama3.2:latest",
            "gemma2:latest",
            "qwen2.5:latest"
        ],
        "note": "Models must be installed in Ollama. Run 'ollama pull <model>' to install."
    }


@app.get("/performance")
async def get_performance_stats():
    """Get comprehensive performance statistics for all request types.
    
    Returns detailed performance metrics including:
    - Total uptime and request count
    - Statistics per request type (image, text, translation, ocr)
    - Model usage breakdown with request counts
    - Timing statistics (avg, min, max) for each model
    - Individual request timing arrays
    """
    if performance_stats is None:
        raise HTTPException(
            status_code=503,
            detail="Performance tracking not initialized"
        )
    
    return performance_stats.get_stats()


@app.get("/performance/summary")
async def get_performance_summary():
    """Get a summary of performance statistics.
    
    Returns a condensed view of performance metrics without detailed timing arrays.
    """
    if performance_stats is None:
        raise HTTPException(
            status_code=503,
            detail="Performance tracking not initialized"
        )
    
    return performance_stats.get_summary()


@app.get("/performance/{request_type}")
async def get_performance_by_type(request_type: str):
    """Get performance statistics for a specific request type.
    
    Args:
        request_type: Type of request (e.g., 'image', 'text', 'translation', 'ocr')
        
    Returns detailed performance metrics for the specified request type including:
    - Total requests for this type
    - All models used for this request type
    - Per-model statistics (count, avg/min/max time)
    - Individual request timing arrays
    """
    if performance_stats is None:
        raise HTTPException(
            status_code=503,
            detail="Performance tracking not initialized"
        )
    
    return performance_stats.get_stats(request_type=request_type)


@app.post("/performance/save")
async def save_performance_stats():
    """Manually trigger saving performance statistics to file.
    
    This endpoint allows you to save the current statistics immediately
    instead of waiting for the periodic save interval.
    """
    if performance_stats is None:
        raise HTTPException(
            status_code=503,
            detail="Performance tracking not initialized"
        )
    
    try:
        performance_stats.save_stats_to_file()
        return {
            "status": "success",
            "message": "Performance statistics saved successfully",
            "file_location": f"{performance_stats.log_location}/performance_stats.yml"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save performance statistics: {str(e)}"
        )


@app.get("/folders")
async def list_folders(path: str = Query(..., description="Path to list folders from")):
    """List folders and return the first image as thumbnail."""
    try:
        base_dir = Path(path)
        if not base_dir.exists() or not base_dir.is_dir():
            return {"folders": []}
            
        result = []
        for d in base_dir.iterdir():
            if d.is_dir():
                # Find first image
                first_img = None
                image_count = 0
                try:
                    for p in d.iterdir():
                        if p.is_file() and is_image_file(str(p)):
                            if first_img is None:
                                first_img = str(p)
                            image_count += 1
                except PermissionError:
                    pass
                
                if first_img is None:
                    try:
                        for p in d.rglob('*'):
                            if p.is_file() and is_image_file(str(p)):
                                first_img = str(p)
                                break
                    except Exception:
                        pass
                
                result.append({
                    "name": d.name,
                    "path": str(d),
                    "first_image": first_img,
                    "image_count": image_count
                })
        return {"folders": result}
    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        return {"folders": []}


@app.get("/folders/images")
async def get_folder_images(path: str = Query(..., description="Path to folder")):
    """Get all images and their caption statuses in a folder."""
    try:
        folder = Path(path)
        if not folder.exists() or not folder.is_dir():
            return {"images": []}
            
        images = []
        for p in folder.iterdir():
            if p.is_file() and is_image_file(str(p)):
                yml_path = p.with_suffix(".yml")
                has_caption = yml_path.exists()

                images.append({
                    "name": p.name,
                    "path": str(p),
                    "has_caption": has_caption,
                    "yml_path": str(yml_path) if has_caption else None
                })
        return {"images": images}
    except Exception as e:
        logger.error(f"Error listing images in folder: {e}")
        return {"images": []}


@app.get("/image")
async def get_image(path: str = Query(..., description="Path to image file")):
    """Serve an image file."""
    try:
        image_path = Path(path)
        if not image_path.exists() or not image_path.is_file():
            raise HTTPException(status_code=404, detail="Image not found")
        return FileResponse(str(image_path))
    except Exception as e:
        logger.error(f"Error serving image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/image/yml")
async def get_image_yml(path: str = Query(..., description="Path to image file")):
    """Return raw YAML text for an image (loads the .yml file next to it)."""
    from fastapi.responses import PlainTextResponse
    try:
        image_path = Path(path)
        yml_path = image_path.with_suffix(".yml")
        if not yml_path.exists():
            raise HTTPException(status_code=404, detail="YML data not found for this image")
        with open(yml_path, "r", encoding="utf-8") as f:
            raw_yaml = f.read()
        return PlainTextResponse(content=raw_yaml, media_type="text/plain; charset=utf-8")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving yml for image: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs")
async def get_all_jobs():
    """List all extraction jobs."""
    try:
        return {"jobs": list_jobs()}
    except Exception as e:
        return {"jobs": [], "error": str(e)}

@app.post("/jobs")
async def create_new_job(req: JobCreateRequest):
    """Create a new background job to process a folder recursively."""
    if image_processor is None:
        raise HTTPException(status_code=503, detail="Image processor not initialized")
    
    try:
        job_id = create_job(req.folder_path)
        start_job_worker(job_id, req.folder_path, image_processor)
        return {"job_id": job_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get status of a specific job."""
    try:
        return get_job(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found")

@app.post("/jobs/{job_id}/pause")
async def pause_existing_job(job_id: str):
    try:
        pause_job(job_id)
        return {"status": "pause_requested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/{job_id}/resume")
async def resume_existing_job(job_id: str):
    if image_processor is None:
        raise HTTPException(status_code=503, detail="Image processor not initialized")
    try:
        resume_job(job_id, image_processor)
        return {"status": "resume_requested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/jobs/{job_id}/cancel")
async def cancel_existing_job(job_id: str):
    try:
        cancel_job(job_id)
        return {"status": "cancel_requested"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


def run_server(config_path: str = "config.yml"):
    """Run the FastAPI server.
    
    Args:
        config_path: Path to configuration file
    """
    import uvicorn
    
    # Load config to get port
    try:
        cfg_mgr = ConfigManager(config_path)
        api_config = cfg_mgr.config.get('api', {})
        host = api_config.get('host', '0.0.0.0')
        port = api_config.get('port', 8000)
        reload = api_config.get('reload', False)
        workers = api_config.get('workers', 1)
        log_level = api_config.get('log_level', 'info')
        
        # Reload monitoring configuration
        reload_dirs = api_config.get('reload_dirs', None)
        reload_excludes = api_config.get('reload_excludes', None)
        
        logger.info(f"Starting Caption Extractor API server on {host}:{port}")
        logger.info(f"Swagger UI: http://{host}:{port}/docs")
        logger.info(f"ReDoc: http://{host}:{port}/redoc")
        
        # Build uvicorn.run arguments
        run_args = {
            "app": "caption_extractor.api_service:app",
            "host": host,
            "port": port,
            "reload": reload,
            "workers": workers,
            "log_level": log_level
        }
        
        # Add reload configuration if reload is enabled
        if reload:
            if reload_dirs:
                run_args["reload_dirs"] = reload_dirs
                logger.info(f"Monitoring directories for changes: {reload_dirs}")
            if reload_excludes:
                run_args["reload_excludes"] = reload_excludes
                logger.info(f"Excluding from reload monitoring: {reload_excludes}")
        
        uvicorn.run(**run_args)
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_server()
