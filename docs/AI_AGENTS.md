# AI Agent Integration Guide

This document explains how to use the AI agent features in Caption Extractor, which enhance OCR processing with visual LLM models using local Ollama.

## Overview

The Caption Extractor now includes three processing stages that can be enabled or disabled independently:

1. **OCR Processing** - Traditional OCR using PaddleOCR
2. **Image Agent** - Visual LLM analysis for image description, scene, text, and story
3. **Text Agent** - LLM-based text correction and completion

## Prerequisites

### Install Ollama

1. Install Ollama from [https://ollama.ai](https://ollama.ai)

2. Pull the required models:
```bash
# For image analysis (vision model)
ollama pull llava:latest

# For text processing
ollama pull llama3.2:latest
```

3. Verify Ollama is running:
```bash
ollama list
```

## Configuration

The AI agents are configured in `config.yml`:

### Pipeline Control

Enable or disable each processing component:

```yaml
pipeline:
  enable_ocr: true          # OCR text extraction using PaddleOCR
  enable_image_agent: true  # Image analysis using visual LLM
  enable_text_agent: true   # Text correction/completion using LLM
```

### Ollama Configuration

```yaml
ollama:
  # Ollama server connection
  host: "http://localhost:11434"  # Ollama API endpoint
  timeout: 120  # Request timeout in seconds
  
  # Model configuration
  models:
    # Visual model for image analysis (image agent)
    vision_model: "llava:latest"  # Suggested: llava:latest, llava:13b, bakllava
    
    # Text model for text processing (text agent)
    text_model: "llama3.2:latest"  # Suggested: llama3.2:latest, mistral:latest, gemma2:latest
```

### Image Agent Configuration

```yaml
  image_agent:
    temperature: 0.7        # Generation temperature (0.0-1.0)
    max_tokens: 1000        # Maximum tokens to generate
    system_prompt: |        # Custom system prompt
      You are an expert image analyst. Analyze the provided image and extract:
      1. Description: A detailed description of what you see
      2. Scene: The type of scene or setting
      3. Text: Any visible text in the image
      4. Story: A brief narrative or context about the image
```

### Text Agent Configuration

```yaml
  text_agent:
    temperature: 0.3        # Lower temperature for more accurate corrections
    max_tokens: 2000        # Maximum tokens to generate
    system_prompt: |        # Custom system prompt
      You are an expert text correction assistant. Your task is to:
      1. Review the OCR-extracted text and image analysis
      2. Correct any OCR errors or inconsistencies
      3. Complete incomplete words or sentences
      4. Improve readability while maintaining the original meaning
```

## Processing Pipeline

When all components are enabled, processing happens in this order:

```
Image File
    ↓
[1] OCR Processing (PaddleOCR)
    ↓
[2] Image Agent (Visual LLM Analysis)
    ↓
[3] Text Agent (Text Correction using OCR + Image Analysis)
    ↓
[4] Metadata Combination
    ↓
YAML Output File
```

## Output Format

The output YAML file now includes comprehensive metadata from all sources:

```yaml
image_file: example.jpg
image_path: /path/to/example.jpg
processed_at: '2025-11-13 00:50:00'
processing_time: 15.234

# OCR Results
ocr:
  full_text: "Original OCR extracted text..."
  text_lines:
    - text: "Line 1"
      confidence: 0.95
      bbox: [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
  total_elements: 10
  avg_confidence: 0.89

# Image Analysis from Visual LLM
image_analysis:
  description: "Detailed description of the image content..."
  scene: "indoor, document, well-lit"
  text: "Text visible in the image according to vision model..."
  story: "Brief narrative about the image context..."

# Text Processing Results
text_processing:
  corrected_text: "Corrected and completed text..."
  changes: "List of corrections made..."
  confidence: "high"

# Unified Text (Best Available Source)
unified_text:
  primary_text: "The best quality text from all sources..."
  recommended_source: "text_processing"
  alternative_texts:
    - source: "ocr"
      text: "Alternative text from OCR..."

# Summary Statistics
summary:
  has_ocr_data: true
  has_image_analysis: true
  has_text_processing: true
  text_sources_count: 3
  processing_stages: ['ocr', 'image_analysis', 'text_processing']
  has_extracted_text: true
  text_length: 150
  ocr_avg_confidence: 0.89
  text_processing_confidence: "high"
```

## Usage Examples

### Example 1: Full Pipeline (All Enabled)

```yaml
pipeline:
  enable_ocr: true
  enable_image_agent: true
  enable_text_agent: true
```

Result: Maximum accuracy with OCR, visual analysis, and LLM-corrected text.

### Example 2: OCR Only (Traditional Mode)

```yaml
pipeline:
  enable_ocr: true
  enable_image_agent: false
  enable_text_agent: false
```

Result: Fast processing with only OCR results.

### Example 3: Vision-Only Analysis

```yaml
pipeline:
  enable_ocr: false
  enable_image_agent: true
  enable_text_agent: false
```

Result: Image description, scene analysis, and text detection using only visual LLM.

### Example 4: OCR + Text Correction

```yaml
pipeline:
  enable_ocr: true
  enable_image_agent: false
  enable_text_agent: true
```

Result: OCR text corrected by LLM without full image analysis.

## Running the Application

```bash
# With default config (all agents enabled)
python -m caption_extractor.main

# With custom config
python -m caption_extractor.main --config my_config.yml

# With verbose logging to see agent details
python -m caption_extractor.main --verbose
```

## Model Recommendations

### Vision Models (Image Agent)

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `llava:latest` | ~4GB | Medium | Good | General purpose |
| `llava:13b` | ~8GB | Slow | Excellent | High accuracy needed |
| `bakllava` | ~5GB | Medium | Good | Alternative to LLaVA |

### Text Models (Text Agent)

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| `llama3.2:latest` | ~2GB | Fast | Excellent | Recommended default |
| `mistral:latest` | ~4GB | Medium | Excellent | Alternative option |
| `gemma2:latest` | ~5GB | Medium | Good | Google's model |
| `phi3:latest` | ~2GB | Fast | Good | Lightweight option |

## Performance Considerations

### Processing Time

- **OCR only**: ~1-2 seconds per image
- **OCR + Image Agent**: ~5-10 seconds per image (depends on model)
- **Full pipeline**: ~10-20 seconds per image

### Memory Usage

- OCR: ~2GB RAM
- Image Agent (llava:latest): +4GB RAM
- Text Agent (llama3.2:latest): +2GB RAM

### Recommendations

1. **For batch processing**: Enable all components for best quality
2. **For real-time processing**: Use OCR only or OCR + Text Agent
3. **For low-memory systems**: Use smaller models or disable agents
4. **For high accuracy**: Use larger vision models (llava:13b)

## Troubleshooting

### Ollama Connection Issues

```
Could not connect to Ollama. Make sure Ollama is running.
```

**Solution**: 
- Check if Ollama is running: `ollama list`
- Verify the host in config.yml matches your Ollama installation
- Default: `http://localhost:11434`

### Model Not Available

```
Vision model 'llava:latest' not available.
Pull the model using: ollama pull llava:latest
```

**Solution**:
```bash
ollama pull llava:latest
ollama pull llama3.2:latest
```

### Timeout Errors

```
Request timed out after 120s
```

**Solution**:
- Increase timeout in config.yml
- Use a smaller/faster model
- Check system resources (CPU/RAM usage)

### Agent Disabled Warnings

If you see warnings about agents being disabled, check:
1. Ollama is running
2. Required models are installed
3. Configuration flags are set to `true`

## Logging

The application logs detailed information about each processing stage:

```
INFO - Initializing Ollama client...
INFO - Successfully connected to Ollama
INFO - Initialized Image Agent with model: llava:latest
INFO - Initialized Text Agent with model: llama3.2:latest
INFO - ImageProcessor initialized - OCR: True, Image Agent: True, Text Agent: True
INFO - Running OCR on: example.jpg
INFO - OCR completed - extracted 10 text elements
INFO - Running Image Agent on: example.jpg
INFO - Successfully analyzed image with vision model
INFO - Running Text Agent on: example.jpg
INFO - Successfully processed text with LLM
INFO - Successfully processed example.jpg in 15.23s
```

Use `--verbose` flag for DEBUG level logging with more details.

## Best Practices

1. **Start with all components enabled** to evaluate quality
2. **Monitor processing time** and adjust based on your needs
3. **Use smaller models** for faster processing if accuracy is acceptable
4. **Disable agents** you don't need to save time and resources
5. **Adjust temperature** settings for different use cases:
   - Lower (0.1-0.3): More deterministic, better for corrections
   - Higher (0.7-0.9): More creative, better for descriptions
6. **Customize system prompts** for your specific domain or language

## Advanced Configuration

### Custom System Prompts

Tailor the AI behavior to your specific needs:

```yaml
ollama:
  image_agent:
    system_prompt: |
      You are analyzing medical documents. Focus on:
      - Medical terminology
      - Patient information
      - Dates and measurements
      Extract these with high precision.
  
  text_agent:
    system_prompt: |
      Correct OCR errors in medical documents.
      Preserve all medical terms, measurements, and dates exactly.
      Do not modify patient information.
```

### Multiple Model Configurations

Switch between models based on content type by modifying config.yml:

```yaml
# For documents with complex layouts
ollama:
  models:
    vision_model: "llava:13b"  # Better layout understanding
    text_model: "llama3.2:latest"

# For simple screenshots or photos
ollama:
  models:
    vision_model: "llava:latest"  # Faster
    text_model: "phi3:latest"  # Lightweight
```

## API Reference

See the source code documentation in:
- `src/caption_extractor/ollama_client.py` - Ollama API client
- `src/caption_extractor/image_agent.py` - Image analysis agent
- `src/caption_extractor/text_agent.py` - Text processing agent
- `src/caption_extractor/metadata_combiner.py` - Metadata combination logic
