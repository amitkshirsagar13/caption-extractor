# FastAPI Integration - Implementation Summary

## Overview

Successfully integrated FastAPI into the Caption Extractor project to provide a REST API for image processing. The API allows users to upload images and process them through the OCR/Image/Text/Translation pipeline with configurable options.

## Changes Made

### 1. Dependencies Added (pyproject.toml)

Added the following dependencies:
- `fastapi>=0.104.0` - Web framework for building APIs
- `uvicorn[standard]>=0.24.0` - ASGI server for running FastAPI
- `python-multipart>=0.0.6` - Support for file uploads

### 2. Configuration (config.yml)

Added new API configuration section:

```yaml
# API Configuration
api:
  port: 8000  # Port for FastAPI server
  host: "0.0.0.0"  # Host address (0.0.0.0 = accessible from network)
  reload: false  # Auto-reload on code changes (dev mode)
  workers: 1  # Number of worker processes
  log_level: "info"  # API log level: debug, info, warning, error, critical
```

### 3. New Files Created

#### a. `src/caption_extractor/single_image_processor.py`

A new processor class that handles single image processing for API requests:

**Features:**
- Lazy loading of processors (OCR, Image Agent, Text Agent, Translator)
- Configurable pipeline options per request
- Support for custom model selection
- Comprehensive error handling and logging
- Returns structured metadata combining all processing results

**Key Methods:**
- `process_image()` - Main processing method with configurable options
- `_get_ocr_processor()` - Lazy load OCR processor
- `_get_image_agent()` - Lazy load Image agent
- `_get_text_agent()` - Lazy load Text agent
- `_get_translator_agent()` - Lazy load Translator agent

#### b. `src/caption_extractor/api_service.py`

The main FastAPI application with endpoints and request/response models:

**Endpoints:**

1. **GET /** - Root endpoint with API info
2. **GET /health** - Health check
3. **POST /process** - Process uploaded image
4. **GET /config** - Get current configuration
5. **GET /models** - List available models

**Features:**
- Automatic OpenAPI/Swagger documentation
- File upload support with validation
- Configurable processing options via form parameters
- Comprehensive error handling
- Logging integration
- Temporary file management

**Request Parameters for /process:**
- `file` (required) - Image file to upload
- `enable_ocr` (optional) - Enable/disable OCR
- `enable_image_agent` (optional) - Enable/disable image analysis
- `enable_text_agent` (optional) - Enable/disable text processing
- `enable_translation` (optional) - Enable/disable translation
- `vision_model` (optional) - Override vision model
- `text_model` (optional) - Override text model

#### c. `src/caption_extractor/run_api.py`

CLI entry point for running the API server:
- Command-line argument parsing
- Configuration file specification
- Server initialization

#### d. `start_api.py` (root directory)

Simple startup script for easy server launch:
- Automatically adds src to Python path
- Provides clear startup information
- Supports custom config file

#### e. `test_api.py` (root directory)

Comprehensive test suite for the API:

**Test Functions:**
- `test_health_check()` - Test health endpoint
- `test_get_config()` - Test configuration retrieval
- `test_get_models()` - Test models listing
- `test_process_image()` - Test image processing with options

**Features:**
- Command-line interface for testing
- Saves processing results to JSON files
- Detailed output of results
- Test summary reporting

#### f. `docs/API_README.md`

Complete API documentation including:
- Quick start guide
- Endpoint descriptions
- Request/response examples
- Configuration options
- Processing options explanation
- Model selection guide
- Development tips
- Troubleshooting guide
- Usage examples with curl and Python

## API Features

### 1. Swagger UI (Interactive Documentation)

Accessible at: `http://localhost:8000/docs`

Features:
- Interactive API testing
- Request/response schemas
- Try-it-out functionality
- File upload interface
- Automatic validation

### 2. ReDoc (Alternative Documentation)

Accessible at: `http://localhost:8000/redoc`

Features:
- Clean, readable documentation
- Searchable interface
- Code samples
- Detailed schemas

### 3. OpenAPI Schema

Accessible at: `http://localhost:8000/openapi.json`

Features:
- Machine-readable API specification
- Client code generation support
- Integration with API tools

## Usage Examples

### Starting the Server

```bash
# Default configuration
python start_api.py

# Custom configuration
python start_api.py --config my_config.yml
```

### Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Get configuration
curl http://localhost:8000/config

# Process an image
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=true"
```

### Testing with Python

```python
import requests

# Process an image
url = "http://localhost:8000/process"
files = {"file": open("image.jpg", "rb")}
data = {
    "enable_ocr": True,
    "enable_image_agent": True,
    "vision_model": "qwen3-vl:235b-cloud"
}

response = requests.post(url, files=files, data=data)
result = response.json()
print(result)
```

### Using Test Script

```bash
# Basic tests (health, config, models)
python test_api.py

# Process an image
python test_api.py --image path/to/image.jpg

# Process with OCR and translation
python test_api.py --image image.jpg --enable-ocr --enable-translation

# Use custom models
python test_api.py --image image.jpg \
  --vision-model llava:13b \
  --text-model llama3.2:latest
```

## Response Format

The API returns comprehensive metadata:

```json
{
  "image_file": "image.jpg",
  "image_path": "/tmp/tempfile.jpg",
  "processed_at": "2025-12-06 21:57:00",
  "processing_time": 12.345,
  "ocr": {
    "full_text": "Extracted text from image",
    "text_lines": ["Line 1", "Line 2"],
    "total_elements": 2,
    "avg_confidence": 0.95
  },
  "image_analysis": {
    "description": "Detailed image description",
    "scene": "outdoor",
    "text": "Text visible in image",
    "story": "Brief narrative"
  },
  "text_processing": {
    "corrected_text": "Corrected and polished text",
    "changes": "Changes made",
    "confidence": "high"
  },
  "translation": {
    "translated_text": "English translation",
    "source_language": "detected",
    "target_language": "English"
  },
  "unified_text": "Combined text from all sources",
  "summary": {
    "total_text_length": 1234,
    "has_ocr_data": true,
    "has_image_analysis": true,
    "has_text_processing": true
  }
}
```

## Logging

All API requests and processing are logged:

- **Location**: `logs/caption_extractor.log`
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Level**: Configurable in `config.yml`

Example log entries:
```
2025-12-06 21:57:08,208 - caption_extractor.api_service - INFO - Loading configuration from: config.yml
2025-12-06 21:57:08,215 - caption_extractor.single_image_processor - INFO - SingleImageProcessor initialized
2025-12-06 21:57:08,215 - caption_extractor.api_service - INFO - FastAPI application started successfully
```

## Architecture

### Request Flow

1. Client uploads image via POST /process
2. FastAPI receives and validates the file
3. Image saved to temporary file
4. SingleImageProcessor.process_image() called with options
5. Pipeline steps executed based on configuration:
   - OCR processing (if enabled)
   - Image agent analysis (if enabled)
   - Text agent processing (if enabled)
   - Translation (if enabled and needed)
6. MetadataCombiner combines all results
7. Response returned to client
8. Temporary file cleaned up

### Component Interactions

```
FastAPI (api_service.py)
    ↓
SingleImageProcessor (single_image_processor.py)
    ↓
StepProcessor (step_processor.py)
    ↓
Individual Processors:
    - OCRProcessor
    - ImageAgent
    - TextAgent
    - TranslatorAgent
    ↓
MetadataCombiner (metadata_combiner.py)
    ↓
JSON Response
```

## Configuration Options

### Pipeline Options (per request)

- **enable_ocr**: Extract text using PaddleOCR
- **enable_image_agent**: Analyze image with vision model
- **enable_text_agent**: Process/correct text with language model
- **enable_translation**: Translate to English if needed

### Model Selection (per request)

- **vision_model**: Choose specific vision model
  - qwen3-vl:235b-cloud (default, high quality)
  - llava:latest (good balance)
  - qwen3-vl:4b (faster, smaller)
  
- **text_model**: Choose specific text model
  - mistral:latest (default)
  - llama3.2:latest
  - gemma2:latest

## Error Handling

The API provides comprehensive error handling:

- **400 Bad Request**: Invalid file type or parameters
- **500 Internal Server Error**: Processing failure
- **503 Service Unavailable**: Service not initialized

Error response format:
```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## Benefits

1. **Easy Integration**: Standard REST API can be integrated with any application
2. **Interactive Documentation**: Swagger UI allows easy testing and exploration
3. **Flexible Processing**: Configure pipeline per request
4. **Model Selection**: Choose models based on speed/quality requirements
5. **Comprehensive Logging**: Full audit trail of all operations
6. **Error Handling**: Clear error messages and status codes
7. **File Upload**: Standard multipart/form-data support
8. **Scalability**: Can run multiple workers for concurrent requests

## Future Enhancements

Possible improvements:
1. Batch processing endpoint for multiple images
2. WebSocket support for streaming results
3. Authentication/authorization
4. Rate limiting
5. Result caching
6. Async processing with job queue
7. Database integration for result storage
8. Image preprocessing options
9. Custom prompt templates
10. Performance metrics endpoint

## Testing

To verify the installation:

1. Start the server: `python start_api.py`
2. Open browser: `http://localhost:8000/docs`
3. Test health endpoint: `http://localhost:8000/health`
4. Upload an image via Swagger UI
5. Run test suite: `python test_api.py --image sample.jpg`

## Dependencies

Required packages:
- `fastapi>=0.104.0` - Web framework
- `uvicorn[standard]>=0.24.0` - ASGI server
- `python-multipart>=0.0.6` - File upload support
- `pydantic` - Data validation (included with FastAPI)
- `requests` - For test script only

## Conclusion

The FastAPI integration provides a production-ready REST API for the Caption Extractor with:
- Complete documentation (Swagger/ReDoc)
- Flexible configuration options
- Comprehensive error handling
- Detailed logging
- Easy testing and integration

The API can be used standalone or integrated into larger applications, providing a robust interface for image processing tasks.
