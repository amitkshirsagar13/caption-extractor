# Quick Start Guide - Pipeline Processing

## 🚀 Getting Started

### Step 1: Run the Pipeline

```bash
cd /home/kira/git/devopsnextgenx/caption-extractor
python -m caption_extractor.main --config config.yml --input-folder ./images
```

**Expected Output**:
```
Loading configuration from: config.yml
Processing 10 images from: ./images
Using 4 threads

==========================================================
PROCESSING COMPLETED
==========================================================
Total images: 10
Successfully processed: 10
Failed: 0
Success rate: 100.0%
Average time per image: 23.4s
Total time: 47.2s

Results saved as .yml files in the same folders as the images.
```

### Step 2: View Processing Status

Each image now has a YAML state file:

```bash
# List all state files
ls -la images/*.yml

# View state for specific image
cat images/photo_001.yml

# View just the pipeline status
cat images/photo_001.yml | grep -A 30 "pipeline_status:"
```

### Step 3: Resume Incomplete Processing

If processing was interrupted:

```bash
# Just run the same command again
python -m caption_extractor.main --config config.yml --input-folder ./images

# System will automatically:
# ✓ Detect incomplete images
# ✓ Skip already-completed steps
# ✓ Resume from the failing step
```

## 📊 YAML State File Example

```yaml
image_path: /home/user/images/photo.jpg
image_name: photo.jpg
created_at: 2025-11-12T10:30:45.123456
updated_at: 2025-11-12T10:35:12.987654

pipeline_status:
  overall_status: completed
  current_step: null
  steps:
    ocr_processing:
      status: completed
      started_at: 2025-11-12T10:30:45.123456
      completed_at: 2025-11-12T10:31:02.456789
      duration: 17.333
      error: null
      data:
        full_text: "Lorem ipsum dolor sit amet..."
        text_lines: [...]
        total_elements: 156
        avg_confidence: 0.94
    
    image_agent_analysis:
      status: completed
      started_at: 2025-11-12T10:31:02.456789
      completed_at: 2025-11-12T10:32:15.789012
      duration: 73.332
      error: null
      data:
        description: "A photograph of..."
        scene: "outdoor"
        text: "Extracted text from image"
        story: "Detailed narrative..."
    
    text_agent_processing:
      status: completed
      started_at: 2025-11-12T10:32:15.789012
      completed_at: 2025-11-12T10:33:45.012345
      duration: 89.223
      error: null
      data:
        corrected_text: "Lorem ipsum dolor sit amet..."
        changes: "Fixed 3 OCR errors"
        confidence: "high"
    
    translation:
      status: skipped
      started_at: null
      completed_at: null
      duration: null
      error: "Skipped: Translation not needed"
      data: null
    
    metadata_combination:
      status: completed
      started_at: 2025-11-12T10:33:45.012345
      completed_at: 2025-11-12T10:33:48.345678
      duration: 3.333
      error: null
      data:
        image_file: photo.jpg
        processed_at: "2025-11-12 10:33:48"
        processing_time: 183.221

results:
  ocr_data:
    full_text: "Lorem ipsum..."
    text_lines: [...]
  image_analysis:
    description: "A photograph of..."
  text_processing:
    corrected_text: "Lorem ipsum..."
  translation_result: null
  combined_metadata:
    image_file: photo.jpg
    processing_time: 183.221

metadata:
  total_processing_time: 183.221
  failed_steps: []
  retries: 0
```

## 🔍 Monitoring Progress

### Check Individual Image Status

```bash
# Quick status check
grep "overall_status:" images/*.yml

# View all step statuses
grep -A 1 "status:" images/photo.yml

# Check processing times
grep "duration:" images/*.yml
```

### Get Batch Statistics

```bash
# Count completed images
grep -c "overall_status: completed" images/*.yml

# Count images in progress
grep -c "overall_status: running" images/*.yml

# Count failed images
grep -c "overall_status: failed" images/*.yml

# Total processing time
grep "total_processing_time:" images/*.yml | \
  awk '{sum += $2} END {print "Total: " sum " seconds"}'
```

### View Detailed Timeline

```bash
# See when each step started/completed
for step in ocr_processing image_agent_analysis text_agent_processing translation metadata_combination; do
  echo "=== $step ==="
  grep -A 2 "$step:" images/photo.yml | grep -E "started_at:|completed_at:|duration:"
done
```

## ⚙️ Configuration

### Enable/Disable Steps

Edit `config.yml`:

```yaml
pipeline:
  enable_ocr: true              # Always enabled
  enable_image_agent: true      # Disable to skip vision analysis
  enable_text_agent: true       # Disable to skip text refinement
  enable_translation: false     # Enable for translation
  
  # Optional: Configure specific parameters
  translation_language: "es"    # Spanish
  image_resize_width: 1024      # Resize for faster processing
```

### Reprocess All Images

To force reprocessing (even if completed):

```bash
# Option 1: Delete YAML files
rm images/*.yml

# Option 2: Use --force flag (if implemented)
python -m caption_extractor.main --config config.yml \
  --input-folder ./images --force

# Then run normally
python -m caption_extractor.main --config config.yml \
  --input-folder ./images
```

## 🐛 Troubleshooting

### Image Processing Failed at OCR Step

```yaml
# In image.yml:
ocr_processing:
  status: failed
  error: "Could not load image or unsupported format"
```

**Solution**:
1. Check image file integrity
2. Convert to supported format (JPG, PNG)
3. Delete YAML file and retry

```bash
file images/photo.jpg
rm images/photo.yml
python -m caption_extractor.main --config config.yml \
  --input-folder ./images
```

### Image Stuck in "running" Status

```yaml
# In image.yml:
pipeline_status:
  overall_status: running
  current_step: text_agent_processing
```

**Solution**: Process was interrupted. Safe to resume:

```bash
# Just run again - system will recover
python -m caption_extractor.main --config config.yml \
  --input-folder ./images
```

### Memory Issues with Large Batch

**Solution**: Reduce thread count

```bash
python -m caption_extractor.main --config config.yml \
  --input-folder ./images --threads 2
```

Or edit `config.yml`:
```yaml
processing:
  num_threads: 2  # Reduced from 4
```

### Partial Translation Failures

```yaml
translation:
  status: failed
  error: "Translation service timeout"
```

**Solution**: Retry just translation

```bash
# Option 1: Re-run (will skip OCR/Image/Text, retry translation)
python -m caption_extractor.main --config config.yml \
  --input-folder ./images

# Option 2: Disable translation, keep other results
# Edit config.yml:
pipeline:
  enable_translation: false
```

## 📈 Performance Optimization

### For First-Time Processing (Fast)

```yaml
# config.yml
pipeline:
  enable_ocr: true
  enable_image_agent: true
  enable_text_agent: true
  enable_translation: false    # Skip translation initially
  
processing:
  num_threads: 8              # More threads for IO-bound tasks
```

### For Quality (Slower but Better)

```yaml
pipeline:
  enable_ocr: true
  enable_image_agent: true
  enable_text_agent: true
  enable_translation: true    # Include translation
  
  # Resize for better vision analysis
  image_resize_width: 2048
```

### For Resume (Existing Batches)

```bash
# Just re-run - it automatically resumes
# Already-completed steps are skipped
# Only incomplete/failed images processed

python -m caption_extractor.main --config config.yml \
  --input-folder ./images

# Very fast - only processes new/failed images
```

## 📚 Advanced Usage

### Process Specific Folder Only

```bash
python -m caption_extractor.main --config config.yml \
  --input-folder /path/to/specific/folder
```

### Enable Verbose Logging

```bash
python -m caption_extractor.main --config config.yml \
  --input-folder ./images --verbose
```

**Output** includes detailed step-by-step logging:
```
DEBUG: Loading state for image...
DEBUG: OCR step starting
DEBUG: OCR completed in 17.3s
DEBUG: Saving state...
```

### Custom Thread Count

```bash
python -m caption_extractor.main --config config.yml \
  --input-folder ./images --threads 4
```

## 🎯 Key Concepts

### Step Status Values
- `pending` - Not yet processed
- `running` - Currently processing
- `completed` - Successfully finished
- `failed` - Error occurred (see `error` field)
- `skipped` - Disabled or not needed

### Overall Status Values
- `pending` - Not started
- `running` - In progress
- `completed` - All steps done
- `failed` - One or more steps failed

### Duration Tracking
- All timings in seconds (floating point)
- Includes only execution time (not YAML I/O)
- Useful for performance analysis

## 🔐 Best Practices

1. **Always keep YAML files**: Contains complete state history
2. **Back up YAML files**: Before batch re-runs
3. **Check for failed steps**: Before assuming success
4. **Use verbose logging**: For debugging issues
5. **Monitor disk space**: YAML files accumulate (~50KB each)
6. **Archive old results**: Move completed images and YAMLs

## 📝 Common Commands Reference

```bash
# Process images
python -m caption_extractor.main --config config.yml \
  --input-folder ./images

# Resume incomplete
python -m caption_extractor.main --config config.yml \
  --input-folder ./images

# Verbose output
python -m caption_extractor.main --config config.yml \
  --input-folder ./images --verbose

# Custom threads
python -m caption_extractor.main --config config.yml \
  --input-folder ./images --threads 2

# Check status
grep "overall_status:" images/*.yml

# View processing times
grep "duration:" images/*.yml
```

---

**Need Help?** Check the full documentation in `docs/PIPELINE_ARCHITECTURE.md` or review `BEFORE_AFTER_COMPARISON.md` for architecture details.
