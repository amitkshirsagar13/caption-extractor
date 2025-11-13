# Usage Guide

## Getting Started

This guide will walk you through setting up and using the Caption Extractor to extract text from your images.

## Prerequisites

Before starting, ensure you have:
- Python 3.8 or higher
- UV package manager installed
- Images in supported formats (JPG, JPEG, PNG, BMP, TIFF, WEBP)

## Quick Start

### 1. Setup Environment

First, set up the project environment:

```bash
./start.sh --setup
```

This command will:
- Create a virtual environment
- Install all dependencies including PaddleOCR
- Create necessary directories
- Download OCR models (first run only)

### 2. Add Your Images

Copy your images to the `data` folder:

```bash
cp /path/to/your/images/* data/
```

Or configure a different input folder in `config.yml`:

```yaml
data:
  input_folder: "/path/to/your/images"
```

### 3. Run Processing

Process all images with default settings:

```bash
./start.sh
```

## Command Line Options

### Basic Commands

```bash
# Process images with default settings
./start.sh

# Show help
./start.sh --help

# Check environment without processing
./start.sh --check

# Setup environment only
./start.sh --setup
```

### Processing Options

```bash
# Enable verbose logging
./start.sh --verbose

# Use custom number of threads
./start.sh --threads 8

# Use custom configuration file
./start.sh --config custom_config.yml

# Override input folder
./start.sh --input-folder /path/to/images

# Combine multiple options
./start.sh --verbose --threads 8 --input-folder /custom/path
```

## Configuration

### Basic Configuration

Edit `config.yml` to customize processing:

```yaml
# Essential settings
processing:
  num_threads: 4          # Adjust based on your CPU
  show_progress: true     # Show progress bar
  enable_timing: true     # Track processing times

data:
  input_folder: "data"    # Your images folder

model:
  use_gpu: false         # Set to true if you have GPU
  lang: "en"             # Language: en, ch, french, german, etc.
```

### Advanced Configuration

For detailed configuration options, see the [Configuration Guide](CONFIG.md).

## Understanding Output

### Processing Output

During processing, you'll see:

```bash
Loading configuration from: config.yml
Initializing OCR processor...
Scanning for images in: data

Processing 25 images from: data
Using 4 threads

Processing images: 100%|████████| 25/25 [00:45<00:00, 1.81s/img]
```

### Results Files

For each image, a YAML file is created with extracted text:

```
data/
├── photo1.jpg
├── photo1.yml          ← Text extracted from photo1.jpg
├── document.png
└── document.yml        ← Text extracted from document.png
```

### YAML Output Example

```yaml
image_file: "receipt.jpg"
image_path: "/home/user/data/receipt.jpg"
processed_at: "2024-01-15 14:30:22"
processing_time: 1.245

text_lines:
  - text: "GROCERY STORE"
    confidence: 0.987
    bbox: [[45, 23], [156, 23], [156, 41], [45, 41]]
  - text: "Total: $25.67"
    confidence: 0.934
    bbox: [[78, 145], [134, 145], [134, 163], [78, 163]]

full_text: "GROCERY STORE Total: $25.67"
total_elements: 2
avg_confidence: 0.961
```

### Final Report

After processing, you'll see a summary:

```
=============================================================
PROCESSING COMPLETED
=============================================================
Total images: 25
Successfully processed: 24
Failed: 1
Success rate: 96.00%
Average time per image: 1.81s
Total time: 45.2s

Results saved as .yml files in the same folders as the images.
```

## Common Use Cases

### 1. Document Digitization

For scanning documents and extracting text:

```yaml
# config.yml
model:
  lang: "en"
  use_angle_cls: true    # Handle rotated documents

performance:
  max_image_size: [3000, 3000]  # Handle high-res scans
  auto_resize: false     # Keep original quality
```

### 2. Receipt/Invoice Processing

For processing receipts and invoices:

```yaml
processing:
  num_threads: 2         # Lower for detailed processing

model:
  use_angle_cls: true    # Handle mobile phone photos
  
performance:
  auto_resize: true      # Optimize mobile photos
```

### 3. Batch Photo Processing

For processing large photo collections:

```yaml
processing:
  num_threads: 8         # Maximum parallelization
  show_progress: true    # Track progress

performance:
  max_image_size: [1024, 1024]  # Resize for speed
  auto_resize: true
```

## Optimization Tips

### Performance Optimization

1. **CPU Usage**: Set `num_threads` to your CPU core count
2. **Memory Usage**: Enable `auto_resize` for large images
3. **GPU Acceleration**: Set `use_gpu: true` if available
4. **Batch Size**: Increase for better throughput with many small images

### Accuracy Optimization

1. **Language Setting**: Set correct language in `model.lang`
2. **Image Quality**: Use high-resolution, clear images
3. **Angle Classification**: Enable `use_angle_cls` for rotated images
4. **Preprocessing**: Ensure good contrast and lighting

## Troubleshooting

### Common Issues

#### No Images Found
```
No image files found in: data
```
**Solutions:**
- Check if images are in the correct folder
- Verify image formats are supported
- Check file permissions

#### OCR Model Download Failed
```
Error initializing PaddleOCR: Model download failed
```
**Solutions:**
- Check internet connection
- Verify disk space in models folder
- Try running again (downloads can be interrupted)

#### Memory Issues
```
Process killed: Out of memory
```
**Solutions:**
- Reduce `num_threads`
- Enable `auto_resize` in performance config
- Set smaller `max_image_size`

#### GPU Not Detected
```
GPU not available, falling back to CPU
```
**Solutions:**
- Install GPU version of PaddlePaddle
- Check CUDA installation
- Verify GPU compatibility

### Performance Issues

#### Slow Processing
**Optimizations:**
- Increase `num_threads` (up to CPU cores)
- Enable GPU processing
- Reduce image size with `auto_resize`
- Use smaller `max_image_size`

#### High Memory Usage
**Solutions:**
- Reduce `num_threads`
- Enable `auto_resize`
- Process images in smaller batches
- Use lower `resize_quality`

## Advanced Usage

### Custom Scripts

You can also use the Caption Extractor in your own Python scripts:

```python
from caption_extractor import ConfigManager, OCRProcessor, ImageProcessor

# Load configuration
config_manager = ConfigManager('config.yml')

# Initialize processors
ocr_processor = OCRProcessor(config_manager.get_ocr_config())
image_processor = ImageProcessor(config_manager, ocr_processor)

# Process single image
result = image_processor.process_single_image('path/to/image.jpg')
print(f"Processing result: {result}")

# Process batch
image_files = image_processor.get_image_files('data')
report = image_processor.process_images_batch(image_files)
print(f"Batch report: {report}")
```

### Step-based batch processing (LLM / agent friendly)

If you run local LLMs or agent models and want to avoid loading/unloading
models per image, use the step-based batch processor. In this mode the
pipeline will:

1. Load the model(s) needed for Step 1 (e.g., OCR or image agent),
2. Process all images through Step 1,
3. Unload Step 1 model(s), then load model(s) for Step 2,
4. Process all images through Step 2, and so on.

This reduces repeated model initialization and is recommended for
large datasets when using local LLMs.

How to run:

```bash
# Step-based mode (preferred for local LLMs / agents)
PYTHONPATH=src python -m caption_extractor.main --batch-mode step

# Optionally override per-step threads
PYTHONPATH=src python -m caption_extractor.main --batch-mode step --threads 2
```

Configuration (example `config.yml` snippet):

```yaml
batch_processing:
  mode: "step"                # 'image' or 'step'
  num_threads_per_step: 2      # Threads used while processing each step
  show_progress: true          # Show per-step progress bars (requires tqdm)
```

Notes:
- Use `--batch-mode image` to run the original behavior (process each image
  through all steps before moving to the next image).
- The step-based mode still uses the same state files/YAML output; any
  completed steps will be skipped on subsequent runs.


### Integration with Other Tools

The YAML output format makes it easy to integrate with other tools:

```bash
# Extract all text to a single file
find data -name "*.yml" -exec yq -r .full_text {} \; > all_text.txt

# Find images with specific text
grep -l "invoice" data/*.yml

# Get processing statistics
yq -r .processing_time data/*.yml | awk '{sum+=$1; count++} END {print "Average:", sum/count}'
```

## Next Steps

- Review the [Configuration Guide](CONFIG.md) for detailed settings
- Check the [API Documentation](API.md) for programmatic usage
- See the [Examples](EXAMPLES.md) for specific use cases