# PaddleOCR Installation Fix Guide

## Problem

You're experiencing PaddlePaddle internal errors like:

```
invalid vector<bool> subscript
(PreconditionNotMet) trace_order size should be equal to dependency_count_
```

These errors indicate **PaddlePaddle internal bugs or incompatibilities** with your system/Python version.

## Root Causes

1. **Python 3.13 incompatibility** - PaddlePaddle doesn't fully support Python 3.13 yet
2. **Corrupted installation** - Mixing incompatible versions of paddlepaddle/paddleocr
3. **Model cache issues** - Corrupted or incompatible cached models
4. **Windows-specific bugs** - Some PaddlePaddle versions have Windows-specific issues

## Solution

### Option 1: Reinstall with Compatible Versions (Recommended)

```bash
# 1. Uninstall current versions
pip uninstall paddlepaddle paddleocr -y

# 2. Install latest stable versions
# For CPU-only (recommended for stability):
pip install paddlepaddle
pip install paddleocr

# OR if specific versions are available for your platform:
# pip install paddlepaddle==2.6.1
# pip install paddleocr==2.7.3

# 3. Clear model cache
# Windows:
rmdir /s /q %USERPROFILE%\.paddleocr

# Linux/Mac:
rm -rf ~/.paddleocr

# 4. Test the installation
python -c "from paddleocr import PaddleOCR; ocr = PaddleOCR(use_angle_cls=True, lang='en', use_gpu=False); print('OK')"
```

### Option 2: Use Python 3.11 Instead of 3.13

PaddlePaddle may not fully support Python 3.13 yet. If you're using Python 3.13:

```bash
# Install Python 3.11 and create a new virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# OR
.venv\Scripts\activate  # Windows

# Then follow Option 1 steps above
```

### Option 3: Disable OCR (Temporary Workaround)

If you need to continue without OCR, edit `config.yml`:

```yaml
pipeline:
  enable_ocr: false  # Disable OCR processing
  enable_image_agent: true
  enable_text_agent: true
  enable_translation: true
```

## Verification

After applying the fix, run:

```bash
./start.sh
```

You should see:
- No segmentation faults
- No "trace_order" errors
- OCR processing completing successfully

## Additional Troubleshooting

### If reinstallation doesn't work:

1. **Check Python version compatibility:**
   ```bash
   python --version
   # Should be 3.8, 3.9, 3.10, or 3.11
   ```

2. **Verify numpy version:**
   ```bash
   pip show numpy
   # Should be < 2.0.0
   ```

3. **Install CPU-only version explicitly:**
   ```bash
   pip uninstall paddlepaddle -y
   pip install paddlepaddle
   # NOT paddlepaddle-gpu
   ```

4. **Check for conflicting packages:**
   ```bash
   pip list | grep paddle
   # Should only show paddlepaddle and paddleocr
   ```

## Common Issues

### Issue: "invalid vector<bool> subscript"
**Cause:** PaddlePaddle internal bug, often triggered by specific image properties or batch processing
**Solution:** 
1. Follow Option 1 (reinstall with compatible versions)
2. Process images one at a time instead of batches
3. Use Python 3.11 instead of 3.13

### Issue: "oneDNN" appearing in logs
**Solution:** Already handled - we disable oneDNN via environment variables in the code.

### Issue: Segmentation fault
**Solution:** Follow Option 1 or Option 2 above.

### Issue: Models not downloading
**Solution:** Check internet connection or manually download models:
```bash
python download_models.py
```

## Contact

If issues persist, please:
1. Share your Python version: `python --version`
2. Share your package versions: `pip freeze | grep paddle`
3. Share the full error message
