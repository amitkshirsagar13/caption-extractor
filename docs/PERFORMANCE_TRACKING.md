# Performance Statistics Tracking

## Overview

The Caption Extractor API includes comprehensive performance statistics tracking to monitor and analyze the performance of different processing components and models.

## Features

- **Request Type Tracking**: Track performance by request type (image, text, translation, ocr)
- **Model-Specific Metrics**: Individual statistics for each model used
- **Timing Analytics**: Count, average, min, max, and individual request times
- **Periodic Logging**: Automatic saving of statistics to a single YAML file (overwritten on each save)
- **REST API Endpoints**: Query performance data via HTTP endpoints
- **Thread-Safe**: Safe for concurrent request tracking

> **Note**: Performance statistics are cumulative from server start and saved to a single file (`performance_stats.yml`) that is overwritten on each periodic save. For historical tracking, implement your own backup/archival strategy.

## Configuration

Add the following to your `config.yml`:

```yaml
# Performance Logging Configuration
performance_logging:
  enabled: true  # Enable periodic performance statistics logging
  log_location: "logs/performance"  # Directory to store performance logs
  periodicity_seconds: 600  # Log interval in seconds (600 = 10 minutes)
```

### Configuration Options

- **enabled**: Enable/disable periodic performance logging (default: `false`)
- **log_location**: Directory where performance YAML files are saved (default: `"logs/performance"`)
- **periodicity_seconds**: How often to save statistics to file in seconds (default: `600` = 10 minutes)

## API Endpoints

### 1. Get All Performance Statistics

```bash
GET /performance
```

Returns comprehensive performance statistics for all request types including:
- Total uptime and request count
- Statistics per request type (image, text, translation, ocr)
- Model usage breakdown with request counts
- Timing statistics (avg, min, max) for each model
- Individual request timing arrays

**Example Response:**
```json
{
  "uptime_seconds": 3600.5,
  "start_time": "2025-12-07T10:00:00",
  "total_requests": 150,
  "request_types": {
    "image": {
      "request_type": "image",
      "total_requests": 50,
      "models": {
        "qwen3-vl:4b": {
          "model_name": "qwen3-vl:4b",
          "request_count": 30,
          "total_time": 450.5,
          "avg_time": 15.017,
          "min_time": 12.3,
          "max_time": 18.9,
          "request_times": [15.2, 14.8, 16.1, ...]
        },
        "llava:latest": {
          "model_name": "llava:latest",
          "request_count": 20,
          "total_time": 280.0,
          "avg_time": 14.0,
          "min_time": 11.5,
          "max_time": 16.8,
          "request_times": [14.2, 13.5, 15.1, ...]
        }
      }
    },
    "text": {
      "request_type": "text",
      "total_requests": 50,
      "models": {
        "mistral:latest": {
          "model_name": "mistral:latest",
          "request_count": 50,
          "total_time": 125.5,
          "avg_time": 2.51,
          "min_time": 1.8,
          "max_time": 3.5,
          "request_times": [2.5, 2.3, 2.7, ...]
        }
      }
    },
    "ocr": {
      "request_type": "ocr",
      "total_requests": 50,
      "models": {
        "paddleocr": {
          "model_name": "paddleocr",
          "request_count": 50,
          "total_time": 45.2,
          "avg_time": 0.904,
          "min_time": 0.5,
          "max_time": 1.5,
          "request_times": [0.9, 0.8, 1.1, ...]
        }
      }
    }
  }
}
```

### 2. Get Performance Summary

```bash
GET /performance/summary
```

Returns a condensed view of performance metrics without detailed timing arrays.

**Example Response:**
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
        },
        {
          "model": "llava:latest",
          "count": 20,
          "avg_time": 14.0,
          "min_time": 11.5,
          "max_time": 16.8
        }
      ]
    }
  ]
}
```

### 3. Get Performance by Request Type

```bash
GET /performance/{request_type}
```

Returns detailed performance metrics for a specific request type.

**Supported Request Types:**
- `image` - Vision model analysis
- `text` - Text processing/correction
- `translation` - Translation to English
- `ocr` - OCR text extraction

**Example:**
```bash
GET /performance/image
```

**Example Response:**
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

## Periodic Logging

When enabled in configuration, performance statistics are automatically saved to YAML files at regular intervals.

### Log File Format

Performance statistics are saved to a single file: `performance_stats.yml`

**Location:** `logs/performance/performance_stats.yml`

**Note:** The file is overwritten on each save (not time-series), always containing the latest cumulative statistics.

**Example Log File Content:**
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
        request_times:
        - 15.2
        - 14.8
        - 16.1
        # ... more times
saved_at: '2025-12-07T11:30:45'
```

## Request Types

### 1. **image** - Vision Model Analysis
- Tracks performance of vision models (qwen3-vl, llava, ministral, etc.)
- Measures time for image understanding and analysis
- Automatically tracks the model used for each request

### 2. **text** - Text Processing
- Tracks performance of text models (mistral, llama, gemma, etc.)
- Measures time for text correction and completion
- Useful for comparing text model performance

### 3. **translation** - Translation to English
- Tracks translation model performance
- Measures time for language translation
- Usually uses the same model as text processing

### 4. **ocr** - OCR Text Extraction
- Tracks PaddleOCR performance
- Measures time for text detection and recognition
- Model name is always "paddleocr"

## Usage Examples

### Query All Statistics
```bash
curl http://localhost:8000/performance
```

### Query Specific Request Type
```bash
# Get image processing stats
curl http://localhost:8000/performance/image

# Get OCR stats
curl http://localhost:8000/performance/ocr

# Get text processing stats
curl http://localhost:8000/performance/text

# Get translation stats
curl http://localhost:8000/performance/translation
```

### Get Summary View
```bash
curl http://localhost:8000/performance/summary
```

## Performance Metrics Explained

### Per-Model Metrics

- **request_count**: Total number of requests processed by this model
- **total_time**: Cumulative processing time for all requests (seconds)
- **avg_time**: Average processing time per request (seconds)
- **min_time**: Fastest request processing time (seconds)
- **max_time**: Slowest request processing time (seconds)
- **request_times**: Array of individual request times (seconds)

### Aggregate Metrics

- **total_requests**: Total requests across all request types
- **uptime_seconds**: Time since the API server started
- **start_time**: ISO timestamp when the server started
- **models_used**: Number of different models used for a request type

## Use Cases

### 1. Model Performance Comparison
Compare different vision models to choose the best one:
```bash
# See which vision model performs best
curl http://localhost:8000/performance/image
```

### 2. System Performance Monitoring
Monitor overall system health and throughput:
```bash
# Check summary statistics
curl http://localhost:8000/performance/summary
```

### 3. Current Statistics Analysis
View current performance statistics:
```bash
# Check the performance log file
cat logs/performance/performance_stats.yml
```

### 4. Capacity Planning
Use request counts and timing data to plan infrastructure:
- Identify peak load periods
- Calculate average throughput (requests/second)
- Estimate resource requirements for scaling

### 5. Model Selection
Use timing data to make informed decisions about model selection:
- Compare avg_time across different models
- Balance accuracy vs. speed based on requirements
- Identify models with consistent performance (low variance)

## Data Retention

- Statistics are cumulative from server start
- Data is not reset unless the server restarts
- Periodic saves overwrite the single `performance_stats.yml` file
- For historical data retention, implement your own backup/archival process

## Thread Safety

The performance tracking system is thread-safe and can handle:
- Concurrent API requests
- Parallel processing pipelines
- Multiple workers (if configured)

## Troubleshooting

### No Statistics Available
If you get an error "Performance tracking not initialized":
1. Check that `performance_stats` is initialized in `api_service.py`
2. Verify configuration is loaded correctly
3. Check server logs for initialization errors

### Missing Request Types
If a request type shows 0 requests:
1. Ensure the pipeline step is enabled in config
2. Verify requests are actually being processed
3. Check that the model is being called

### Log Files Not Created
If periodic logs aren't being saved:
1. Verify `enabled: true` in `performance_logging` config
2. Check that the `log_location` directory is writable
3. Review server logs for permission errors
4. Ensure the periodicity interval has elapsed

## Architecture

### Components

1. **PerformanceStatsManager** (`src/caption_extractor/performance/performance_stats.py`)
   - Core statistics tracking and storage
   - Thread-safe request tracking
   - Periodic logging worker thread
   - Statistics calculation and aggregation

2. **SingleImageProcessor** (`src/caption_extractor/pipeline/step_processor/single_image_processor.py`)
   - Integrates performance tracking into processing pipeline
   - Times each processing step
   - Records model names and processing times

3. **API Endpoints** (`src/caption_extractor/api_service.py`)
   - Exposes performance data via REST API
   - Handles query routing by request type
   - Manages lifecycle (startup/shutdown)

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

## Future Enhancements

Potential improvements to the performance tracking system:

- [ ] Add percentile metrics (p50, p95, p99)
- [ ] Support for custom time windows (last hour, last day, etc.)
- [ ] Real-time WebSocket updates for monitoring dashboards
- [ ] Export to Prometheus/Grafana formats
- [ ] Automatic anomaly detection
- [ ] Performance regression alerts
- [ ] Database persistence for long-term storage
- [ ] Configurable log retention policies

## License

Same as the main Caption Extractor project.
