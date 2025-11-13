# Caption Extractor

Advanced image processing pipeline with OCR text extraction, AI-powered image analysis, and intelligent text refinement using PaddleOCR PP-OCRv5 and Ollama agents.

## 🎯 Key Features

- **Pipeline-Based Processing**: Step-by-step processing with YAML state management
- **No Context Switching**: Each image processes through all steps sequentially
- **Resume Capability**: Automatically resume incomplete processing from the failing step
- **State Persistence**: Complete YAML audit trail of all processing steps
- **Multi-Step Intelligence**:
  - **OCR Extraction**: High-accuracy text detection with PaddleOCR PP-OCRv5
  - **Vision Analysis**: AI-powered image understanding via Image Agent
  - **Text Refinement**: Intelligent text correction via Text Agent
  - **Optional Translation**: Translate extracted content to other languages
  - **Metadata Combination**: Unified output combining all sources
- **Multi-threaded Processing**: Configurable concurrent processing for batch jobs
- **Error Resilience**: Per-step error handling with automatic retry capability
- **Comprehensive Logging**: Detailed logging at each pipeline step
- **Multiple Image Formats**: Support for JPG, JPEG, PNG, BMP, TIFF, WEBP
- **Performance Metrics**: Detailed timing and success statistics per image and step

## 🚀 Getting Started

### Quick Start

```bash
# Run pipeline processing
python -m caption_extractor.main --config config.yml --input-folder ./images

# Resume incomplete processing (automatic)
python -m caption_extractor.main --config config.yml --input-folder ./images
```

### With Setup Script

```bash
# Setup environment
./start.sh --setup

# Run processing
./start.sh
```

## Configuration

Edit `config.yml` to customize processing settings:

### Pipeline Configuration

```yaml
pipeline:
  enable_ocr: true              # Enable/disable OCR step
  enable_image_agent: true      # Enable/disable vision analysis
  enable_text_agent: true       # Enable/disable text refinement
  enable_translation: false     # Enable/disable translation (optional)
```

### Key Processing Options

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

## 📖 Documentation

### Complete Guides

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in 5 minutes
- **[docs/PIPELINE_ARCHITECTURE.md](docs/PIPELINE_ARCHITECTURE.md)** - Detailed pipeline architecture and state management
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - Complete implementation details
- **[BEFORE_AFTER_COMPARISON.md](BEFORE_AFTER_COMPARISON.md)** - Architecture evolution and improvements
- **[docs/API.md](docs/API.md)** - Python API reference
- **[docs/USAGE.md](docs/USAGE.md)** - Detailed usage guide
- **[docs/AI_AGENTS.md](docs/AI_AGENTS.md)** - AI agent configuration and usage

## Output Format

For each processed image, a YAML file is created in the same directory with complete pipeline state:

```yaml
image_path: "example.jpg"
image_name: "example.jpg"
created_at: "2025-11-12T10:30:45.123456"
updated_at: "2025-11-12T10:35:12.987654"

pipeline_status:
  overall_status: completed      # pending/running/completed/failed
  current_step: null
  steps:
    ocr_processing:
      status: completed
      duration: 17.3
      data: {ocr extraction results}
    image_agent_analysis:
      status: completed
      duration: 73.3
      data: {vision analysis results}
    text_agent_processing:
      status: completed
      duration: 89.2
      data: {text refinement results}
    translation:
      status: skipped
      error: "Translation not needed"
    metadata_combination:
      status: completed
      duration: 3.3
      data: {combined results}

results:
  ocr_data: {ocr results}
  image_analysis: {vision analysis}
  text_processing: {text refinement}
  translation_result: null
  combined_metadata: {final metadata}

metadata:
  total_processing_time: 183.2
  failed_steps: []
  retries: 0
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