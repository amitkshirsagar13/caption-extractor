"""FastAPI service for image processing API."""

import os
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .config_manager import ConfigManager
from .pipeline.step_processor.single_image_processor import SingleImageProcessor


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
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


def initialize_services(config_path: str = "config.yml"):
    """Initialize configuration and services.
    
    Args:
        config_path: Path to configuration file
    """
    global config_manager, image_processor
    
    try:
        logger.info(f"Loading configuration from: {config_path}")
        config_manager = ConfigManager(config_path)
        
        logger.info("Initializing image processor")
        image_processor = SingleImageProcessor(config_manager)
        
        logger.info("Services initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}", exc_info=True)
        raise


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        # Look for config.yml in current directory or parent directories
        config_path = "config.yml"
        if not os.path.exists(config_path):
            # Try parent directory
            parent_config = Path(__file__).parent.parent.parent / "config.yml"
            if parent_config.exists():
                config_path = str(parent_config)
        
        initialize_services(config_path)
        logger.info("FastAPI application started successfully")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        # Don't fail startup, but services won't be available


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with API information."""
    return HealthResponse(
        status="running",
        version="1.0.0",
        config_loaded=config_manager is not None
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
        
        logger.info(f"Starting Caption Extractor API server on {host}:{port}")
        logger.info(f"Swagger UI: http://{host}:{port}/docs")
        logger.info(f"ReDoc: http://{host}:{port}/redoc")
        
        uvicorn.run(
            "caption_extractor.api_service:app",
            host=host,
            port=port,
            reload=reload,
            workers=workers,
            log_level=log_level
        )
        
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_server()
