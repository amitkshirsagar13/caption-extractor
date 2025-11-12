# API Documentation

## Caption Extractor API Reference

This document provides detailed information about the classes and methods available in the Caption Extractor package.

## Classes

### ConfigManager

Manages configuration loading and validation.

#### Constructor

```python
ConfigManager(config_path: str = "config.yml")
```

**Parameters:**
- `config_path`: Path to the configuration file (default: "config.yml")

#### Methods

##### `get_model_dir() -> str`
Returns the model storage directory path.

##### `get_input_folder() -> str`
Returns the input folder path for images.

##### `get_supported_formats() -> List[str]`
Returns list of supported image file formats.

##### `get_num_threads() -> int`
Returns the number of processing threads to use.

##### `get_batch_size() -> int`
Returns the batch size for processing.

##### `is_progress_enabled() -> bool`
Returns whether progress display is enabled.

##### `is_timing_enabled() -> bool`
Returns whether timing is enabled.

##### `get_ocr_config() -> Dict[str, Any]`
Returns OCR configuration dictionary.

##### `get_performance_config() -> Dict[str, Any]`
Returns performance configuration dictionary.

---

### OCRProcessor

Handles OCR operations using PaddleOCR.

#### Constructor

```python
OCRProcessor(config: Dict[str, Any])
```

**Parameters:**
- `config`: OCR configuration dictionary

#### Methods

##### `preprocess_image(image_path: str, max_size: Tuple[int, int] = None, auto_resize: bool = True) -> np.ndarray`

Preprocesses image for OCR processing.

**Parameters:**
- `image_path`: Path to the image file
- `max_size`: Maximum image size (width, height)
- `auto_resize`: Whether to auto-resize large images

**Returns:** Preprocessed image as numpy array

**Raises:**
- `FileNotFoundError`: If image file doesn't exist
- `Exception`: If image cannot be processed

##### `extract_text(image_path: str, performance_config: Dict[str, Any] = None) -> List[Dict[str, Any]]`

Extracts text from image using OCR.

**Parameters:**
- `image_path`: Path to the image file
- `performance_config`: Performance configuration

**Returns:** List of extracted text with bounding boxes and confidence scores

**Example return data:**
```python
[
    {
        'text': 'Sample text',
        'confidence': 0.95,
        'bbox': [[10, 20], [100, 20], [100, 40], [10, 40]]
    }
]
```

##### `format_extracted_text(extracted_data: List[Dict[str, Any]]) -> Dict[str, Any]`

Formats extracted text data for output.

**Parameters:**
- `extracted_data`: List of extracted text elements

**Returns:** Formatted text data

**Example return data:**
```python
{
    'text_lines': [
        {
            'text': 'Sample text',
            'confidence': 0.95,
            'bbox': [[10, 20], [100, 20], [100, 40], [10, 40]]
        }
    ],
    'full_text': 'Sample text',
    'total_elements': 1,
    'avg_confidence': 0.95
}
```

---

### ImageProcessor

Handles batch image processing with threading support.

#### Constructor

```python
ImageProcessor(config_manager, ocr_processor: OCRProcessor)
```

**Parameters:**
- `config_manager`: Configuration manager instance
- `ocr_processor`: OCR processor instance

#### Methods

##### `get_image_files(folder_path: str) -> List[str]`

Gets list of image files from folder.

**Parameters:**
- `folder_path`: Path to the folder containing images

**Returns:** List of image file paths

##### `process_single_image(image_path: str) -> Tuple[str, bool, float, Dict[str, Any]]`

Processes a single image file.

**Parameters:**
- `image_path`: Path to the image file

**Returns:** Tuple of (image_path, success, processing_time, result_data)

##### `process_images_batch(image_files: List[str]) -> Dict[str, Any]`

Processes images in batch with threading support.

**Parameters:**
- `image_files`: List of image file paths to process

**Returns:** Processing statistics and results

**Example return data:**
```python
{
    'summary': {
        'total_images': 100,
        'processed_images': 98,
        'successful_images': 96,
        'failed_images': 2,
        'success_rate': 97.96
    },
    'timing': {
        'total_processing_time': 123.45,
        'batch_time': 130.67,
        'average_time_per_image': 1.26,
        'min_time': 0.45,
        'max_time': 3.21
    },
    'errors': [
        {
            'image': '/path/to/failed_image.jpg',
            'error': 'Error message',
            'time': 0.15
        }
    ]
}
```

##### `get_processing_report() -> Dict[str, Any]`

Generates processing statistics report.

**Returns:** Processing report dictionary

## Output File Format

Each processed image generates a YAML file with the following structure:

```yaml
image_file: "example.jpg"
image_path: "/full/path/to/example.jpg"
processed_at: "2024-01-15 14:30:22"
processing_time: 0.845
text_lines:
  - text: "First line of text"
    confidence: 0.987
    bbox: [[10, 20], [100, 20], [100, 40], [10, 40]]
  - text: "Second line of text"
    confidence: 0.923
    bbox: [[10, 45], [120, 45], [120, 65], [10, 65]]
full_text: "First line of text Second line of text"
total_elements: 2
avg_confidence: 0.955
```

## Configuration Schema

### Complete Configuration Example

```yaml
# Logging Configuration
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
  file: "logs/caption_extractor.log"

# PaddleOCR Model Configuration
model:
  model_dir: "models"
  det_model_name: "ch_PP-OCRv4_det"
  rec_model_name: "ch_PP-OCRv4_rec"
  use_angle_cls: true
  lang: "en"  # Supported: en, ch, french, german, korean, japan
  use_gpu: false

# Data Configuration
data:
  input_folder: "data"
  supported_formats: [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]

# Processing Configuration
processing:
  num_threads: 4
  batch_size: 10
  show_progress: true
  enable_timing: true

# Performance Configuration
performance:
  max_image_size: [2048, 2048]
  auto_resize: true
  resize_quality: 85
```

## Error Handling

All methods include comprehensive error handling:

- **FileNotFoundError**: When image or config files are missing
- **yaml.YAMLError**: When configuration files are malformed
- **Exception**: For general processing errors (OCR failures, image corruption, etc.)

Errors are logged with full stack traces and included in processing reports.

## Thread Safety

- `ImageProcessor` is thread-safe for concurrent image processing
- Statistics updates are protected by locks
- Each thread processes images independently
- Progress reporting is synchronized across threads

## Performance Considerations

- **Thread Count**: Optimal thread count is usually equal to CPU cores
- **Memory Usage**: Large images consume more memory; use auto_resize for large datasets
- **GPU Usage**: Enable GPU support for faster processing if available
- **Batch Size**: Adjust based on available memory and processing requirements