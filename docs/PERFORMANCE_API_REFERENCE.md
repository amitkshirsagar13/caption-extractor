# Performance API Quick Reference

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/performance` | GET | Get all performance statistics with detailed timing arrays |
| `/performance/summary` | GET | Get condensed summary without timing arrays |
| `/performance/{type}` | GET | Get statistics for specific request type |

## Request Types

| Type | Description | Models Tracked |
|------|-------------|----------------|
| `image` | Vision model analysis | qwen3-vl, llava, ministral, etc. |
| `text` | Text processing/correction | mistral, llama, gemma, etc. |
| `translation` | Translation to English | Same as text models |
| `ocr` | OCR text extraction | paddleocr |

## Quick Commands

```bash
# Get all statistics
curl http://localhost:8000/performance

# Get summary
curl http://localhost:8000/performance/summary

# Get image processing stats
curl http://localhost:8000/performance/image

# Get OCR stats
curl http://localhost:8000/performance/ocr

# Get text processing stats
curl http://localhost:8000/performance/text

# Get translation stats
curl http://localhost:8000/performance/translation
```

## Python Examples

```python
import requests

# Get summary
response = requests.get('http://localhost:8000/performance/summary')
data = response.json()
print(f"Total Requests: {data['total_requests']}")
print(f"Uptime: {data['uptime_seconds']}s")

# Get image stats
response = requests.get('http://localhost:8000/performance/image')
data = response.json()
for model, stats in data['models'].items():
    print(f"{model}: {stats['avg_time']:.2f}s avg")
```

## Response Structure

### Summary Response
```json
{
  "uptime_seconds": 3600.5,
  "start_time": "2025-12-07T10:00:00",
  "total_requests": 150,
  "request_types": [
    {
      "request_type": "image",
      "total_requests": 50,
      "models_used": 2,
      "model_breakdown": [
        {
          "model": "qwen3-vl:4b",
          "count": 30,
          "avg_time": 15.017,
          "min_time": 12.3,
          "max_time": 18.9
        }
      ]
    }
  ]
}
```

### Detailed Response (per type)
```json
{
  "request_type": "image",
  "total_requests": 50,
  "uptime_seconds": 3600.5,
  "models": {
    "qwen3-vl:4b": {
      "model_name": "qwen3-vl:4b",
      "request_count": 30,
      "total_time": 450.5,
      "avg_time": 15.017,
      "min_time": 12.3,
      "max_time": 18.9,
      "request_times": [15.2, 14.8, 16.1, ...]
    }
  }
}
```

## Configuration

```yaml
performance_logging:
  enabled: true
  log_location: "logs/performance"
  periodicity_seconds: 600  # 10 minutes
```

## Log Files

- **Location**: `logs/performance/performance_stats.yml`
- **Format**: Single YAML file (overwritten on each save)
- **Content**: Latest cumulative statistics since server start

## Metrics Explained

| Metric | Description |
|--------|-------------|
| `request_count` | Total number of requests for this model |
| `total_time` | Cumulative processing time (seconds) |
| `avg_time` | Average time per request (seconds) |
| `min_time` | Fastest request time (seconds) |
| `max_time` | Slowest request time (seconds) |
| `request_times` | Array of individual request times |

## Common Use Cases

### Compare Models
```bash
# See which vision model is faster
curl http://localhost:8000/performance/image | jq '.models | to_entries[] | {model: .key, avg_time: .value.avg_time}'
```

### Check System Load
```bash
# Get total requests and uptime
curl http://localhost:8000/performance/summary | jq '{total_requests, uptime_seconds}'
```

### Find Bottlenecks
```bash
# Get average time for each request type
curl http://localhost:8000/performance/summary | jq '.request_types[] | {type: .request_type, models: .model_breakdown[] | .avg_time}'
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Performance tracking not initialized" | Restart API server, check logs for initialization errors |
| No data for request type | Enable the pipeline step in config.yml |
| Log files not created | Check `performance_logging.enabled: true` in config |
| Old data persists | Statistics reset on server restart |

## Related Documentation

- Full Guide: `docs/PERFORMANCE_TRACKING.md`
- Implementation: `docs/PERFORMANCE_FEATURE_SUMMARY.md`
- Example Script: `examples/check_performance.py`
- API Docs: http://localhost:8000/docs
