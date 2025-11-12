# Caption Extractor

OCR text extraction from images using PaddleOCR PP-OCRv5 with multi-threaded batch processing.

## Features

- **High-accuracy OCR**: Uses PaddleOCR PP-OCRv5 for text detection and recognition
- **Multi-threaded processing**: Configurable concurrent processing for improved performance
- **Batch processing**: Process entire folders of images automatically
- **Progress tracking**: Real-time progress display with timing information
- **Flexible configuration**: YAML-based configuration for all settings
- **Comprehensive logging**: Detailed logging with configurable levels
- **Performance reporting**: Detailed statistics after processing completion
- **Multiple image formats**: Support for JPG, JPEG, PNG, BMP, TIFF, WEBP
- **YAML output**: Extracted text saved as structured YAML files

## Installation

### Prerequisites

- Python 3.8 or higher
- UV package manager ([Installation guide](https://docs.astral.sh/uv/getting-started/installation/))

### Quick Setup

1. Clone or download the project
2. Run the setup script:

```bash
./start.sh --setup
```

This will:
- Create a virtual environment
- Install all required dependencies
- Create necessary directories

## Usage

### Basic Usage

```bash
# Process all images in the data folder
./start.sh

# Process with verbose logging
./start.sh --verbose

# Use custom number of threads
./start.sh --threads 8

# Use custom configuration file
./start.sh --config my_config.yml

# Use custom input folder
./start.sh --input-folder /path/to/images
```

### Setup and Check Commands

```bash
# Setup environment only
./start.sh --setup

# Check environment and data without processing
./start.sh --check

# Show help
./start.sh --help
```

### Direct Python Usage

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the application
python -m caption_extractor.main --help
```

## Configuration

Edit `config.yml` to customize processing settings:

### Key Configuration Options

```yaml
# Processing Configuration
processing:
  num_threads: 4          # Number of concurrent threads
  batch_size: 10         # Batch size for processing
  show_progress: true    # Show progress bar
  enable_timing: true    # Enable timing for each image

# Data Configuration  
data:
  input_folder: "data"   # Input folder containing images
  supported_formats: [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]

# Model Configuration
model:
  model_dir: "models"    # Model storage location
  use_angle_cls: true    # Use angle classification
  lang: "en"            # Language support
  use_gpu: false        # Use GPU if available

# Logging Configuration
logging:
  level: INFO           # DEBUG, INFO, WARNING, ERROR, CRITICAL
  file: "logs/caption_extractor.log"
```

## Project Structure

```
caption-extractor/
├── src/caption_extractor/     # Python source code
│   ├── __init__.py           # Package initialization
│   ├── main.py              # Main entry point
│   ├── config_manager.py    # Configuration management
│   ├── ocr_processor.py     # OCR processing logic
│   └── image_processor.py   # Image and batch processing
├── data/                    # Input images directory
├── docs/                    # Documentation
├── tests/                   # Test scripts
├── logs/                    # Log files
├── models/                  # PaddleOCR models (auto-downloaded)
├── config.yml              # Configuration file
├── start.sh                # Startup script
├── pyproject.toml          # Project configuration
└── README.md               # This file
```

## Output Format

For each processed image, a YAML file is created in the same directory with extracted text:

```yaml
image_file: "example.jpg"
image_path: "/path/to/example.jpg"
processed_at: "2024-01-15 14:30:22"
processing_time: 0.845
text_lines:
  - text: "Sample extracted text"
    confidence: 0.987
    bbox: [[10, 20], [100, 20], [100, 40], [10, 40]]
full_text: "Sample extracted text"
total_elements: 1
avg_confidence: 0.987
```

## Processing Report

After completion, you'll see a detailed report:

```
=============================================================
PROCESSING COMPLETED
=============================================================
Total images: 150
Successfully processed: 148
Failed: 2
Success rate: 98.67%
Average time per image: 1.23s
Total time: 185.5s
```

## Dependencies

- **PaddleOCR**: OCR engine for text extraction
- **PaddlePaddle**: Deep learning framework
- **PyYAML**: YAML file handling
- **Pillow**: Image processing
- **OpenCV**: Computer vision operations
- **tqdm**: Progress bar display

## Troubleshooting

### Common Issues

1. **No images found**: Ensure image files are in the correct format and location
2. **GPU not detected**: Install PaddlePaddle GPU version if needed
3. **Memory issues**: Reduce `num_threads` or enable `auto_resize` in config
4. **Model download fails**: Check internet connection and model directory permissions

### Performance Tips

1. **Use GPU**: Set `use_gpu: true` if GPU is available
2. **Optimize threads**: Set `num_threads` to number of CPU cores
3. **Enable auto-resize**: For large images, enable `auto_resize` in performance config
4. **Batch size**: Adjust `batch_size` based on available memory

## Development

### Adding Tests

Create test files in the `tests/` directory:

```python
# tests/test_ocr_processor.py
import unittest
from caption_extractor.ocr_processor import OCRProcessor

class TestOCRProcessor(unittest.TestCase):
    def test_initialization(self):
        # Your test code here
        pass
```

### Running Tests

```bash
source .venv/bin/activate
python -m pytest tests/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

1. Check the troubleshooting section
2. Review the configuration options
3. Check the log files in `logs/`
4. Create an issue in the project repository