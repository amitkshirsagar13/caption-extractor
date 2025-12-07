# Quick Fix: PaddleOCR Network Error

## The Problem
```
No model hoster is available! Please check your network connection...
```

## Quick Solutions (Pick One)

### ✅ Solution 1: Download Models Now (Best)
If you have internet access right now:

```bash
# Activate your virtual environment first
source .venv/bin/activate  # Linux/Mac
# or
.venv\Scripts\activate     # Windows

# Download models
python download_models.py
```

**What this does:**
- Downloads PaddleOCR models to `~/.paddleocr/`
- Tests that everything works
- Enables offline usage forever

---

### ✅ Solution 2: Use Proxy
If you're behind a corporate firewall:

**Windows:**
```cmd
set HTTP_PROXY=http://your-proxy:port
set HTTPS_PROXY=http://your-proxy:port
python download_models.py
```

**Linux/Mac:**
```bash
export HTTP_PROXY=http://your-proxy:port
export HTTPS_PROXY=http://your-proxy:port
python download_models.py
```

---

### ✅ Solution 3: Check Existing Cache
Models might already be downloaded:

**Check cache:**
```bash
# Windows
dir %USERPROFILE%\.paddleocr

# Linux/Mac
ls -la ~/.paddleocr/
```

**If you see model files**, try running your app again - it should work!

---

### ✅ Solution 4: Download from Different Location
If you can access the internet from a different computer/network:

1. **On a computer with internet**, run:
   ```bash
   python download_models.py
   ```

2. **Copy the cache folder** to your offline machine:
   - From: `~/.paddleocr/` (or `%USERPROFILE%\.paddleocr` on Windows)
   - To: Same location on your offline machine

3. **Run your application** - it will use the cached models

---

## Verify It Works

After trying a solution:

```bash
# Test the application
python -m caption_extractor.main --config config.yml --input-folder ./data
```

Or test with the download script:
```bash
python download_models.py
```

---

## Still Not Working?

See detailed troubleshooting: [TROUBLESHOOTING_NETWORK.md](TROUBLESHOOTING_NETWORK.md)

Or check logs:
```bash
cat logs/caption_extractor.log  # Linux/Mac
type logs\caption_extractor.log # Windows
```
