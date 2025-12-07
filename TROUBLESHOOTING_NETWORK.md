# PaddleOCR Network Issues - Troubleshooting Guide

## Problem
Error: "No model hoster is available! Please check your network connection..."

This occurs when PaddleOCR cannot reach its model hosting services to download required models.

## Solutions

### Option 1: Download Models While Connected (Recommended)

If you have temporary internet access:

```bash
# Run the model download script
python download_models.py
```

This will:
- Download all required PaddleOCR models
- Cache them locally in `~/.paddleocr/`
- Test that models work correctly
- Allow offline usage afterward

### Option 2: Use VPN or Proxy

If you're behind a corporate firewall:

```bash
# Set proxy environment variables (Windows)
set HTTP_PROXY=http://proxy.company.com:8080
set HTTPS_PROXY=http://proxy.company.com:8080

# Set proxy environment variables (Linux/Mac)
export HTTP_PROXY=http://proxy.company.com:8080
export HTTPS_PROXY=http://proxy.company.com:8080

# Then run the download script
python download_models.py
```

### Option 3: Manual Model Download

If automated download doesn't work:

1. **Download models manually** from GitHub:
   - Visit: https://github.com/PaddlePaddle/PaddleOCR/blob/main/doc/doc_en/models_list_en.md
   - Download English OCR models:
     - Detection model: `en_PP-OCRv4_det`
     - Recognition model: `en_PP-OCRv4_rec`
     - Classification model: `ch_ppocr_mobile_v2.0_cls`

2. **Extract and organize**:
   ```
   models/
   ├── det/
   │   └── en_PP-OCRv4_det/
   ├── rec/
   │   └── en_PP-OCRv4_rec/
   └── cls/
       └── ch_ppocr_mobile_v2.0_cls/
   ```

3. **Update `config.yml`**:
   ```yaml
   ocr:
     model_dir: "models"  # Point to local models
     lang: "en"
     use_angle_cls: true
     det_model_dir: "models/det/en_PP-OCRv4_det"
     rec_model_dir: "models/rec/en_PP-OCRv4_rec"
     cls_model_dir: "models/cls/ch_ppocr_mobile_v2.0_cls"
   ```

### Option 4: Use Different Model Sources (China-based users)

If you're in China, PaddleOCR provides alternative model sources:

```bash
# Use AIStudio mirror
export PPOCR_MODEL_URL=https://aistudio.baidu.com

# Or use BOS (Baidu Object Storage)
export PPOCR_MODEL_URL=https://paddle-model-ecology.bj.bcebos.com
```

### Option 5: Disable Model Download and Use Pre-installed Models

If you have previously run PaddleOCR successfully, models might already be cached:

1. **Check cache location**:
   ```bash
   # Windows
   dir %USERPROFILE%\.paddleocr
   
   # Linux/Mac
   ls ~/.paddleocr/
   ```

2. **If models exist**, your `config.yml` should work without changes since PaddleOCR will use cached models.

## Verification

After downloading models, verify they work:

```bash
# Test the application
python -m caption_extractor.main --config config.yml --input-folder ./images

# Or run the test in download_models.py
python download_models.py
```

## Network Diagnostics

Test connectivity to PaddleOCR model hosts:

```bash
# Test HuggingFace
curl -I https://huggingface.co

# Test ModelScope
curl -I https://modelscope.cn

# Test AIStudio
curl -I https://aistudio.baidu.com

# Test BOS
curl -I https://paddle-model-ecology.bj.bcebos.com
```

If all fail, you're likely behind a firewall and need to use Option 1 (download from a different network) or Option 3 (manual download).

## Common Issues

### Issue: "SSL Certificate Verification Failed"

```bash
# Disable SSL verification (temporary workaround)
export CURL_CA_BUNDLE=""
python download_models.py
```

### Issue: "Connection Timeout"

```bash
# Increase timeout
export PADDLEOCR_DOWNLOAD_TIMEOUT=300
python download_models.py
```

### Issue: Models download but application still fails

Check that your virtual environment has the correct packages:

```bash
# Reinstall PaddleOCR
pip install --upgrade paddleocr paddlepaddle
```

## Support

If none of these solutions work, please:
1. Check the logs in `logs/caption_extractor.log`
2. Run with debug logging: Edit `config.yml` and set `logging.level: DEBUG`
3. Create an issue with the error details

## Related Files

- `download_models.py` - Automated model download script
- `config.yml` - Application configuration
- `src/caption_extractor/ocr_processor.py` - OCR initialization code
