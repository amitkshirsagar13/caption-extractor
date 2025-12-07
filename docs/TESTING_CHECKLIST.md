# Performance Tracking Feature - Testing Checklist

## Pre-Testing Setup

- [ ] Ensure API server is not running
- [ ] Check `config.yml` has `performance_logging` section
- [ ] Verify `logs/performance/` directory exists or can be created

## Configuration Testing

### 1. Verify Configuration
```bash
# Check config.yml has performance_logging section
grep -A 3 "performance_logging:" config.yml
```

Expected output:
```yaml
performance_logging:
  enabled: true
  log_location: "logs/performance"
  periodicity_seconds: 600
```

- [ ] Configuration section exists
- [ ] `enabled` is set to `true`
- [ ] `log_location` is specified
- [ ] `periodicity_seconds` is set

## Server Startup Testing

### 2. Start API Server
```bash
python start_api.py
```

Check server logs for:
- [ ] "Initializing performance statistics manager"
- [ ] "Started periodic performance logging"
- [ ] No initialization errors
- [ ] Server starts successfully

### 3. Verify Endpoints Available
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test performance endpoint (should return empty stats)
curl http://localhost:8000/performance/summary
```

- [ ] Health endpoint returns 200 OK
- [ ] Performance endpoint returns 200 OK
- [ ] Initial stats show `total_requests: 0`
- [ ] `uptime_seconds` is a small positive number
- [ ] `start_time` is recent

## Functional Testing

### 4. Process Test Images

Process at least one image with each component:

```bash
# Process with OCR only
curl -X POST "http://localhost:8000/process" \
  -F "file=@test_image.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=false" \
  -F "enable_text_agent=false"

# Process with image agent
curl -X POST "http://localhost:8000/process" \
  -F "file=@test_image.jpg" \
  -F "enable_ocr=false" \
  -F "enable_image_agent=true" \
  -F "enable_text_agent=false" \
  -F "vision_model=qwen3-vl:4b"

# Process with text agent
curl -X POST "http://localhost:8000/process" \
  -F "file=@test_image.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=true" \
  -F "enable_text_agent=true" \
  -F "text_model=mistral:latest"

# Process with translation (if text is non-English)
curl -X POST "http://localhost:8000/process" \
  -F "file=@test_image.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=true" \
  -F "enable_text_agent=true" \
  -F "enable_translation=true"
```

- [ ] OCR processing completes successfully
- [ ] Image agent processing completes successfully
- [ ] Text agent processing completes successfully
- [ ] Translation processing completes (if applicable)

### 5. Verify Statistics Tracking

```bash
# Get summary statistics
curl http://localhost:8000/performance/summary
```

Expected to see:
- [ ] `total_requests` > 0
- [ ] At least one request type has data
- [ ] Model names are correct
- [ ] Request counts match number of requests made
- [ ] Average times are reasonable (> 0)

### 6. Test Request Type Endpoints

```bash
# Test OCR stats
curl http://localhost:8000/performance/ocr

# Test image stats
curl http://localhost:8000/performance/image

# Test text stats
curl http://localhost:8000/performance/text

# Test translation stats (if used)
curl http://localhost:8000/performance/translation
```

For each endpoint:
- [ ] Returns 200 OK
- [ ] Shows correct request count
- [ ] Model name is correct
- [ ] `avg_time`, `min_time`, `max_time` are present
- [ ] `request_times` array contains individual times

### 7. Test Full Statistics Endpoint

```bash
curl http://localhost:8000/performance | python -m json.tool
```

- [ ] Returns complete statistics
- [ ] All request types present
- [ ] All models tracked
- [ ] `request_times` arrays present
- [ ] JSON is well-formed

## Periodic Logging Testing

### 8. Wait for Periodic Log

Default is 10 minutes, but you can modify config for faster testing:

```yaml
performance_logging:
  periodicity_seconds: 60  # 1 minute for testing
```

After waiting (or restarting server with shorter interval):

```bash
# Check if log file was created
ls -lh logs/performance/

# View log file
cat logs/performance/performance_stats.yml
```

- [ ] Log directory was created
- [ ] File `performance_stats.yml` exists
- [ ] File contains valid YAML
- [ ] Statistics match current API data
- [ ] `saved_at` timestamp is present

### 9. Verify Log Content

```bash
# View log file content
cat logs/performance/performance_stats.yml
```

Check that log contains:
- [ ] `uptime_seconds`
- [ ] `start_time`
- [ ] `total_requests`
- [ ] `request_types` section
- [ ] Model statistics
- [ ] `saved_at` timestamp

## Server Shutdown Testing

### 10. Graceful Shutdown

```bash
# Stop the server (Ctrl+C or SIGTERM)
```

Check server logs for:
- [ ] "Shutting down PerformanceStatsManager"
- [ ] "Stopping periodic performance logging"
- [ ] Final statistics saved to log file
- [ ] No errors during shutdown

Verify:
- [ ] Final log file created
- [ ] Contains latest statistics
- [ ] No corruption in log files

## Example Script Testing

### 11. Run Example Script

```bash
python examples/check_performance.py
```

Expected output:
- [ ] Script connects successfully
- [ ] Displays summary statistics
- [ ] Shows detailed image stats
- [ ] Shows OCR stats
- [ ] No errors or exceptions

## Stress Testing

### 12. Multiple Concurrent Requests

```bash
# Send multiple requests concurrently
for i in {1..10}; do
  curl -X POST "http://localhost:8000/process" \
    -F "file=@test_image.jpg" \
    -F "enable_ocr=true" &
done
wait

# Check statistics
curl http://localhost:8000/performance/summary
```

- [ ] All requests complete successfully
- [ ] Request count matches number sent
- [ ] No duplicate or missing entries
- [ ] Timing data is reasonable
- [ ] No race conditions or errors

## Edge Cases

### 13. Empty Statistics

Restart server and check immediately:
```bash
curl http://localhost:8000/performance/summary
```

- [ ] Returns valid response
- [ ] `total_requests: 0`
- [ ] Empty request_types array
- [ ] No errors

### 14. Disabled Periodic Logging

Set in config:
```yaml
performance_logging:
  enabled: false
```

Restart server and verify:
- [ ] Server starts normally
- [ ] Performance endpoints still work
- [ ] No periodic log files created
- [ ] No periodic logging thread started

### 15. Invalid Request Type

```bash
curl http://localhost:8000/performance/invalid_type
```

- [ ] Returns 200 OK (not 404)
- [ ] Returns empty statistics for unknown type
- [ ] `total_requests: 0`
- [ ] `models: {}`

## Documentation Verification

### 16. Check Documentation

- [ ] `docs/PERFORMANCE_TRACKING.md` exists and is complete
- [ ] `docs/PERFORMANCE_FEATURE_SUMMARY.md` exists
- [ ] `docs/PERFORMANCE_API_REFERENCE.md` exists
- [ ] `README.md` mentions performance tracking
- [ ] All examples in docs are accurate
- [ ] Configuration examples match actual config

### 17. API Documentation

Visit http://localhost:8000/docs

- [ ] Performance endpoints appear in Swagger UI
- [ ] Endpoint descriptions are clear
- [ ] Response models are defined
- [ ] "Try it out" feature works
- [ ] Example responses are shown

## Code Quality

### 18. Code Review Checklist

- [ ] No syntax errors
- [ ] Type hints where appropriate
- [ ] Docstrings for all public methods
- [ ] Thread-safe implementation
- [ ] Proper error handling
- [ ] No memory leaks
- [ ] Clean logging messages

### 19. Performance Overhead

Process 10 images with and without performance tracking:

- [ ] Performance impact is minimal (< 1% overhead)
- [ ] No noticeable slowdown
- [ ] Memory usage is reasonable

## Final Verification

### 20. Complete Workflow Test

1. Start server
2. Process 5-10 images with various settings
3. Check all performance endpoints
4. Wait for periodic log
5. Verify log file contents
6. Run example script
7. Shutdown server gracefully
8. Verify final log

- [ ] All steps complete without errors
- [ ] Statistics are accurate
- [ ] Logs are created correctly
- [ ] System behaves as expected

## Sign-Off

Date: _______________

Tested by: _______________

All tests passed: [ ] YES [ ] NO

Notes:
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

## Issues Found

| Issue # | Description | Severity | Status |
|---------|-------------|----------|--------|
|         |             |          |        |
|         |             |          |        |
|         |             |          |        |

## Recommendations

_________________________________________________________________
_________________________________________________________________
_________________________________________________________________
