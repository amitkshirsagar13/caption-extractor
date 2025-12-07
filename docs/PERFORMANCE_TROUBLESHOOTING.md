# Performance Tracking - Troubleshooting Guide

## Empty Request Types

### Issue
When checking `logs/performance/performance_stats.yml`, you see:
```yaml
request_types: {}
total_requests: 0
```

### Cause
This is normal when:
1. The server just started and no requests have been processed yet
2. The periodic logging saved stats before any images were processed
3. All pipeline steps are disabled in the configuration

### Solution

**Process some images first:**

```bash
# Process an image with OCR
curl -X POST "http://localhost:8000/process" \
  -F "file=@your_image.jpg" \
  -F "enable_ocr=true"

# Then check stats
curl http://localhost:8000/performance/summary
```

You should now see:
```json
{
  "total_requests": 1,
  "request_types": [
    {
      "request_type": "ocr",
      "total_requests": 1,
      "model_breakdown": [...]
    }
  ]
}
```

### Verify Tracking is Working

Run the unit test:
```bash
python tests/test_performance_tracking.py
```

This will:
- Create a test performance manager
- Track sample requests
- Verify statistics are being collected
- Save to a test file

Expected output:
```
✓ ALL TESTS PASSED
```

## Common Issues

### 1. Performance Stats Not Tracking

**Check:**
- Is `performance_stats` properly initialized in `api_service.py`?
- Is it passed to `SingleImageProcessor`?
- Are requests actually completing successfully?

**Debug:**
```bash
# Check server logs for initialization
grep "performance" logs/caption_extractor.log

# Check if tracking is being called
# Look for log messages like "OCR completed: ... in X.XXs"
```

### 2. Log File Not Created

**Check:**
```yaml
# In config.yml
performance_logging:
  enabled: true  # Must be true
  log_location: "logs/performance"  # Directory must be writable
  periodicity_seconds: 600  # Wait this long after server start
```

**Solutions:**
- Ensure `enabled: true`
- Check directory permissions
- Wait for first periodic save (default 10 minutes)
- Or manually trigger save by restarting server

### 3. Specific Request Type Missing

**If you don't see a request type (e.g., 'image'):**

Check that the pipeline step is enabled:
```yaml
# In config.yml
pipeline:
  enable_ocr: true          # Required for 'ocr' stats
  enable_image_agent: true  # Required for 'image' stats
  enable_text_agent: true   # Required for 'text' stats
  enable_translation: true  # Required for 'translation' stats
```

And that you're explicitly enabling it in the API request:
```bash
curl -X POST "http://localhost:8000/process" \
  -F "file=@image.jpg" \
  -F "enable_image_agent=true" \
  -F "vision_model=qwen3-vl:4b"
```

### 4. Stats Reset on Server Restart

**Expected Behavior:**
- Stats are cumulative from server start
- They reset when server restarts
- Periodic log is overwritten (not appended)

**For Persistent History:**
Implement a backup script:
```bash
#!/bin/bash
# backup_performance.sh
cp logs/performance/performance_stats.yml \
   "logs/performance/backup_$(date +%Y%m%d_%H%M%S).yml"
```

Run before server restart or via cron.

## Verification Checklist

- [ ] Server started successfully
- [ ] Performance manager initialized (check logs)
- [ ] At least one request processed
- [ ] Pipeline step(s) enabled in config
- [ ] Request completed without errors
- [ ] Check `/performance/summary` endpoint
- [ ] Verify stats are non-zero
- [ ] Check log file exists (after wait period)

## Quick Test Commands

```bash
# 1. Check current stats via API
curl http://localhost:8000/performance/summary | jq

# 2. Process test image
curl -X POST "http://localhost:8000/process" \
  -F "file=@test.jpg" \
  -F "enable_ocr=true" \
  -F "enable_image_agent=true"

# 3. Check stats again
curl http://localhost:8000/performance/summary | jq

# 4. View log file
cat logs/performance/performance_stats.yml

# 5. Run unit test
python tests/test_performance_tracking.py
```

## Expected Behavior After Processing

After processing one image with all components enabled:

```yaml
# logs/performance/performance_stats.yml
uptime_seconds: 45.23
start_time: '2025-12-07T16:00:00'
total_requests: 4  # ocr + image + text + translation (if needed)
request_types:
  ocr:
    request_type: ocr
    total_requests: 1
    models:
      paddleocr:
        model_name: paddleocr
        request_count: 1
        avg_time: 0.85
        # ... more stats
  image:
    request_type: image
    total_requests: 1
    models:
      qwen3-vl:4b:
        model_name: qwen3-vl:4b
        request_count: 1
        avg_time: 15.2
        # ... more stats
  text:
    request_type: text
    total_requests: 1
    models:
      mistral:latest:
        model_name: mistral:latest
        request_count: 1
        avg_time: 2.3
        # ... more stats
saved_at: '2025-12-07T16:10:00'
```

## Getting Help

If issues persist:
1. Check `logs/caption_extractor.log` for errors
2. Run the unit test: `python tests/test_performance_tracking.py`
3. Enable DEBUG logging in `config.yml`
4. Verify API endpoints work: `http://localhost:8000/docs`
5. Check that requests are actually completing successfully
