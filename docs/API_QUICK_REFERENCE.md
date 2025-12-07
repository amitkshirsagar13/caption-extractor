# Caption Extractor API - Quick Reference

## Start Server

```bash
python start_api.py
```

Server runs on: **http://localhost:8000**

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc documentation |
| `/config` | GET | Current configuration |
| `/models` | GET | Available models |
| `/process` | POST | Process image |

## Process Image

### Minimal Request

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.jpg"
```

### Full Options

```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=true" \
  -F "enable_text_agent=true" \
  -F "enable_translation=true" \
  -F "vision_model=qwen3-vl:235b-cloud" \
  -F "text_model=mistral:latest"
```

### Python Example

```python
import requests

url = "http://localhost:8000/process"
files = {"file": open("image.jpg", "rb")}
data = {
    "enable_ocr": True,
    "enable_image_agent": True,
    "enable_text_agent": True
}

response = requests.post(url, files=files, data=data)
result = response.json()
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file` | File | Required | Image to process |
| `enable_ocr` | Boolean | Config | Enable OCR |
| `enable_image_agent` | Boolean | Config | Enable image analysis |
| `enable_text_agent` | Boolean | Config | Enable text processing |
| `enable_translation` | Boolean | Config | Enable translation |
| `vision_model` | String | Config | Vision model name |
| `text_model` | String | Config | Text model name |

## Available Models

### Vision Models
- `qwen3-vl:235b-cloud` (default)
- `qwen3-vl:4b`
- `llava:latest`
- `llava:13b`
- `bakllava`

### Text Models
- `mistral:latest` (default)
- `llama3.2:latest`
- `gemma2:latest`
- `qwen2.5:latest`

## Response Structure

```json
{
  "image_file": "filename.jpg",
  "processing_time": 12.3,
  "processed_at": "2025-12-06 21:57:00",
  "ocr": {...},
  "image_analysis": {...},
  "text_processing": {...},
  "translation": {...},
  "unified_text": "...",
  "summary": {...}
}
```

## Testing

```bash
# Test basic endpoints
python test_api.py

# Process an image
python test_api.py --image photo.jpg

# With OCR enabled
python test_api.py --image photo.jpg --enable-ocr

# Custom models
python test_api.py --image photo.jpg \
  --vision-model llava:13b \
  --text-model llama3.2:latest
```

## Configuration

Edit `config.yml`:

```yaml
api:
  port: 8000
  host: "0.0.0.0"
  reload: false
  workers: 1
  log_level: "info"
```

## Common Commands

```bash
# Check server status
curl http://localhost:8000/health

# Get current config
curl http://localhost:8000/config

# List available models
curl http://localhost:8000/models

# Process image (minimal)
curl -X POST http://localhost:8000/process \
  -F "file=@image.jpg"
```

## Error Codes

- `200` - Success
- `400` - Invalid request
- `500` - Processing error
- `503` - Service unavailable

## Logs

Location: `logs/caption_extractor.log`

## Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Full Guide: `docs/API_README.md`
- Integration Guide: `docs/FASTAPI_INTEGRATION.md`
