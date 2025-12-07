# Caption Extractor API

FastAPI-based REST API for extracting and analyzing text from images using OCR and AI agents.

## Features

- **Image Upload**: Upload images for processing via multipart/form-data
- **Configurable Pipeline**: Enable/disable OCR, image analysis, text processing, and translation
- **Model Selection**: Choose specific vision and text models for processing
- **Swagger UI**: Interactive API documentation at `/docs`
- **ReDoc**: Alternative API documentation at `/redoc`
- **OpenAPI Schema**: Machine-readable API spec at `/openapi.json`

## Quick Start

### 1. Start the Server

```bash
python start_api.py
```

Or with a custom config:

```bash
python start_api.py --config path/to/config.yml
```

The server will start on `http://localhost:8000` by default.

### 2. Access Swagger UI

Open your browser and navigate to:

```
http://localhost:8000/docs
```

### 3. Process an Image

#### Using Swagger UI

1. Navigate to `http://localhost:8000/docs`
2. Click on the `POST /process` endpoint
3. Click "Try it out"
4. Upload an image file
5. Configure processing options (optional)
6. Click "Execute"

#### Using curl

```bash
curl -X POST "http://localhost:8000/process" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/image.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=true" \
  -F "enable_text_agent=true" \
  -F "enable_translation=false"
```

#### Using Python

```python
import requests

url = "http://localhost:8000/process"
files = {"file": open("image.jpg", "rb")}
data = {
    "enable_ocr": True,
    "enable_image_agent": True,
    "enable_text_agent": True,
    "enable_translation": False,
    "vision_model": "qwen3-vl:235b-cloud",
    "text_model": "mistral:latest"
}

response = requests.post(url, files=files, data=data)
result = response.json()
print(result)
```

## API Endpoints

### GET /

Root endpoint with API information.

**Response:**
```json
{
  "status": "running",
  "version": "1.0.0",
  "config_loaded": true
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "config_loaded": true
}
```

### POST /process

Process an uploaded image through the caption extraction pipeline.

**Request Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file` | File | Yes | Image file to process |
| `enable_ocr` | Boolean | No | Enable OCR processing (default: from config) |
| `enable_image_agent` | Boolean | No | Enable image analysis (default: from config) |
| `enable_text_agent` | Boolean | No | Enable text processing (default: from config) |
| `enable_translation` | Boolean | No | Enable translation (default: from config) |
| `vision_model` | String | No | Vision model name (e.g., "qwen3-vl:235b-cloud") |
| `text_model` | String | No | Text model name (e.g., "mistral:latest") |

**Response:**
```json
{
  "image_file": "image.jpg",
  "image_path": "/tmp/image.jpg",
  "processed_at": "2025-12-06 21:57:00",
  "processing_time": 12.345,
  "ocr": {
    "full_text": "Extracted text...",
    "text_lines": ["Line 1", "Line 2"],
    "total_elements": 2,
    "avg_confidence": 0.95
  },
  "image_analysis": {
    "description": "A detailed description of the image",
    "scene": "outdoor",
    "text": "Text visible in the image",
    "story": "Brief narrative about the image"
  },
  "text_processing": {
    "corrected_text": "Corrected and polished text",
    "changes": "Description of changes made",
    "confidence": "high"
  },
  "translation": {
    "translated_text": "English translation",
    "source_language": "detected language",
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

### GET /config

Get current pipeline configuration.

**Response:**
```json
{
  "pipeline": {
    "enable_ocr": false,
    "enable_image_agent": true,
    "enable_text_agent": true,
    "enable_translation": false
  },
  "models": {
    "vision_model": "qwen3-vl:235b-cloud",
    "text_model": "mistral:latest"
  },
  "ollama": {
    "host": "http://localhost:11434",
    "timeout": 120
  }
}
```

### GET /models

Get information about available models.

**Response:**
```json
{
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
```

## Configuration

The API server configuration is in `config.yml`:

```yaml
# API Configuration
api:
  port: 8000  # Port for FastAPI server
  host: "0.0.0.0"  # Host address
  reload: false  # Auto-reload on code changes (dev mode)
  workers: 1  # Number of worker processes
  log_level: "info"  # API log level
```

## Processing Options

### OCR Processing

Extract text from images using PaddleOCR.

- **Parameter**: `enable_ocr`
- **Default**: From config (typically `false`)
- **Use case**: Documents, screenshots, signage

### Image Agent

Analyze images using vision models (e.g., Qwen3-VL, LLaVA).

- **Parameter**: `enable_image_agent`
- **Default**: From config (typically `true`)
- **Use case**: Scene understanding, object detection, visual analysis

### Text Agent

Process and correct extracted text using language models.

- **Parameter**: `enable_text_agent`
- **Default**: From config (typically `true`)
- **Use case**: Text correction, completion, enhancement

### Translation

Translate non-English text to English.

- **Parameter**: `enable_translation`
- **Default**: From config (typically `false`)
- **Use case**: Multilingual content processing

## Model Selection

### Vision Models

Available vision models for image analysis:

- `qwen3-vl:235b-cloud` - High-quality vision-language model (default)
- `qwen3-vl:4b` - Smaller, faster variant
- `llava:latest` - LLaVA vision model
- `llava:13b` - Larger LLaVA variant
- `bakllava` - BakLLaVA model
- `ministral-3:latest` - Ministral vision model

### Text Models

Available text models for text processing:

- `mistral:latest` - Mistral language model (default)
- `llama3.2:latest` - Llama 3.2 model
- `gemma2:latest` - Google Gemma 2 model
- `qwen2.5:latest` - Qwen 2.5 model

**Note**: Models must be installed in Ollama before use. Install with:

```bash
ollama pull <model-name>
```

## Development

### Running in Development Mode

Enable auto-reload for development:

```yaml
# config.yml
api:
  reload: true  # Enable auto-reload
  log_level: "debug"  # Verbose logging
```

### Testing the API

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test configuration endpoint
curl http://localhost:8000/config

# Test models endpoint
curl http://localhost:8000/models
```

## Error Handling

The API returns standard HTTP status codes:

- `200 OK` - Successful request
- `400 Bad Request` - Invalid request (e.g., wrong file type)
- `500 Internal Server Error` - Processing error
- `503 Service Unavailable` - Service not initialized

**Error Response Format:**

```json
{
  "error": "Error message",
  "detail": "Detailed error information"
}
```

## Logging

The API logs all requests and processing details:

- **Location**: `logs/caption_extractor.log`
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Level**: Configured in `config.yml` (INFO by default)

## Performance Tips

1. **Use appropriate models**: Smaller models are faster but less accurate
2. **Disable unused features**: Skip OCR if not needed
3. **Batch processing**: For multiple images, consider using the batch CLI instead
4. **Resource allocation**: Adjust `workers` in config for concurrent requests

## Troubleshooting

### Server won't start

- Check if port 8000 is already in use
- Verify `config.yml` exists and is valid
- Check logs in `logs/caption_extractor.log`

### Processing fails

- Ensure Ollama is running (`ollama serve`)
- Verify required models are installed (`ollama list`)
- Check image file format (supported: jpg, jpeg, png, bmp, tiff, webp)

### Slow processing

- Use smaller/faster models
- Disable unnecessary processing steps
- Check Ollama performance (GPU availability)

## Examples

### Process with all features enabled

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=true" \
  -F "enable_text_agent=true" \
  -F "enable_translation=true"
```

### Process with specific models

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.jpg" \
  -F "vision_model=llava:13b" \
  -F "text_model=llama3.2:latest"
```

### Process with minimal features

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.jpg" \
  -F "enable_image_agent=true" \
  -F "enable_ocr=false" \
  -F "enable_text_agent=false"
```

## License

MIT License - See LICENSE file for details
