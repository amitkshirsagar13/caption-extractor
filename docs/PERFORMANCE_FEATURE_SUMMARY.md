# Performance Statistics Feature - Implementation Summary

## Overview

Added comprehensive performance statistics tracking to the Caption Extractor API to monitor and analyze processing performance across different request types and models.

## Files Created

### 1. Performance Module
- **`src/caption_extractor/performance/__init__.py`**
  - Package initialization for performance tracking module

- **`src/caption_extractor/performance/performance_stats.py`**
  - `PerformanceStatsManager` class - Core statistics tracking
  - `ModelStats` dataclass - Per-model statistics
  - `RequestTypeStats` dataclass - Per-request-type statistics
  - Thread-safe request tracking
  - Periodic YAML logging functionality
  - Statistics calculation and aggregation

### 2. Documentation
- **`docs/PERFORMANCE_TRACKING.md`**
  - Comprehensive documentation
  - Configuration guide
  - API endpoint reference with examples
  - Use cases and troubleshooting
  - Architecture overview

### 3. Examples
- **`examples/check_performance.py`**
  - Demonstration script for querying performance statistics
  - Shows how to use all performance endpoints
  - Pretty-printed output for easy visualization

## Files Modified

### 1. Configuration
- **`config.yml`**
  - Added `performance_logging` section with:
    - `enabled`: Enable/disable periodic logging
    - `log_location`: Directory for performance logs
    - `periodicity_seconds`: Logging interval (default: 600s = 10min)

### 2. API Service
- **`src/caption_extractor/api_service.py`**
  - Added `performance_stats` global variable
  - Modified `initialize_services()` to create PerformanceStatsManager
  - Added `startup_event()` to start periodic logging
  - Added `shutdown_event()` to cleanup on shutdown
  - New endpoints:
    - `GET /performance` - All statistics
    - `GET /performance/summary` - Condensed summary
    - `GET /performance/{request_type}` - Type-specific stats

### 3. Image Processor
- **`src/caption_extractor/pipeline/step_processor/single_image_processor.py`**
  - Added `performance_stats` parameter to `__init__()`
  - Added timing tracking for each processing step:
    - OCR processing (request_type: 'ocr', model: 'paddleocr')
    - Image agent (request_type: 'image', model: vision_model)
    - Text agent (request_type: 'text', model: text_model)
    - Translation (request_type: 'translation', model: translator_model)
  - Track individual step times with `time.perf_counter()`
  - Log timing information in step completion messages

## Features Implemented

### 1. Request Type Tracking
- **image**: Vision model analysis (qwen3-vl, llava, etc.)
- **text**: Text processing/correction (mistral, llama, etc.)
- **translation**: Translation to English
- **ocr**: OCR text extraction (PaddleOCR)

### 2. Per-Model Metrics
For each model in each request type:
- `request_count`: Number of requests
- `total_time`: Cumulative processing time
- `avg_time`: Average time per request
- `min_time`: Fastest request
- `max_time`: Slowest request
- `request_times`: Array of individual times

### 3. API Endpoints

#### GET /performance
Returns complete statistics for all request types including detailed timing arrays.

#### GET /performance/summary
Returns condensed view without detailed timing arrays.

#### GET /performance/{request_type}
Returns detailed statistics for a specific request type:
- `/performance/image`
- `/performance/text`
- `/performance/translation`
- `/performance/ocr`

### 4. Periodic Logging
- Configurable periodic saving to YAML files
- Files saved as: `performance_stats_YYYYMMDD_HHMMSS.yml`
- Default location: `logs/performance/`
- Default interval: 600 seconds (10 minutes)
- Runs in background thread
- Automatic cleanup on shutdown

### 5. Thread Safety
- Thread-safe request tracking using `threading.Lock()`
- Safe for concurrent API requests
- Safe for parallel processing

## Configuration Example

```yaml
# Performance Logging Configuration
performance_logging:
  enabled: true  # Enable periodic performance statistics logging
  log_location: "logs/performance"  # Directory to store performance logs
  periodicity_seconds: 600  # Log interval in seconds (600 = 10 minutes)
```

## Usage Examples

### Query All Statistics
```bash
curl http://localhost:8000/performance
```

### Query Specific Request Type
```bash
curl http://localhost:8000/performance/image
curl http://localhost:8000/performance/ocr
curl http://localhost:8000/performance/text
curl http://localhost:8000/performance/translation
```

### Get Summary
```bash
curl http://localhost:8000/performance/summary
```

### Using Python Script
```bash
python examples/check_performance.py
```

## Example Output

### Summary Endpoint
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

### Periodic Log File (`logs/performance/performance_stats.yml`)
```yaml
uptime_seconds: 3600.5
start_time: '2025-12-07T10:00:00'
total_requests: 150
request_types:
  image:
    request_type: image
    total_requests: 50
    models:
      qwen3-vl:4b:
        model_name: qwen3-vl:4b
        request_count: 30
        total_time: 450.5
        avg_time: 15.017
        min_time: 12.3
        max_time: 18.9
        request_times: [15.2, 14.8, 16.1, ...]
saved_at: '2025-12-07T11:30:45'
```

**Note:** This file is overwritten on each periodic save with the latest cumulative statistics.

## Architecture

### Data Flow
```
Request → SingleImageProcessor → Track Timing → PerformanceStatsManager
                                                          ↓
                                                  Store in Memory
                                                          ↓
                              ┌─────────────────────────┴─────────────────────┐
                              ↓                                                 ↓
                    API Endpoints (/performance)                    Periodic Logger
                              ↓                                                 ↓
                    Return JSON Response                       Save to YAML File
```

### Components
1. **PerformanceStatsManager**: Core statistics tracking and storage
2. **SingleImageProcessor**: Integrates timing into processing pipeline
3. **API Endpoints**: Expose data via REST API
4. **Periodic Logger**: Background thread for automatic saving

## Use Cases

1. **Model Performance Comparison**: Compare different vision/text models
2. **System Monitoring**: Track overall health and throughput
3. **Historical Analysis**: Analyze performance over time via logs
4. **Capacity Planning**: Use data for infrastructure scaling decisions
5. **Model Selection**: Make informed choices based on speed vs. accuracy

## Testing

To test the feature:

1. Start the API server:
   ```bash
   python start_api.py
   ```

2. Process some images via API

3. Check statistics:
   ```bash
   python examples/check_performance.py
   # or
   curl http://localhost:8000/performance/summary
   ```

4. Check periodic logs:
   ```bash
   ls logs/performance/
   cat logs/performance/performance_stats_*.yml
   ```

## Benefits

1. **Visibility**: See exactly how long each processing step takes
2. **Model Comparison**: Easily compare performance of different models
3. **Optimization**: Identify bottlenecks in the pipeline
4. **Monitoring**: Track system performance over time
5. **Troubleshooting**: Diagnose performance issues
6. **Data-Driven Decisions**: Choose models based on actual performance data

## Future Enhancements

Potential improvements:
- Add percentile metrics (p50, p95, p99)
- Support for custom time windows
- Real-time WebSocket updates
- Prometheus/Grafana export
- Automatic anomaly detection
- Performance regression alerts
- Database persistence
- Log retention policies

## Notes

- Statistics are cumulative from server start
- Data is lost on server restart (unless logged to files)
- Periodic logs accumulate - implement rotation as needed
- Thread-safe for concurrent requests
- Minimal performance overhead
