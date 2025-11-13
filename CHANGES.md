# Changes - AI Agent Integration

## Summary

Added comprehensive AI agent processing capabilities to the Caption Extractor, integrating visual LLM models via local Ollama to enhance OCR processing with image analysis and text correction.

## New Features

### 1. AI Agent Processing Pipeline
- **Image Agent**: Uses visual LLM models (e.g., LLaVA) to analyze images and extract:
  - Detailed image description
  - Scene type and setting
  - Visible text
  - Contextual story/narrative

- **Text Agent**: Uses text LLM models (e.g., Llama 3.2) to:
  - Correct OCR errors
  - Complete incomplete words/sentences
  - Improve text readability
  - Provide confidence ratings

### 2. Flexible Pipeline Configuration
- Enable/disable each component independently:
  - `enable_ocr`: Traditional OCR processing
  - `enable_image_agent`: Visual LLM analysis
  - `enable_text_agent`: Text correction with LLM
- All three enabled by default for maximum accuracy

### 3. Local Ollama Integration
- Connects to local Ollama instance (no cloud dependencies)
- Configurable host, timeout, and models
- Automatic model availability checking
- Graceful fallback if Ollama is unavailable

### 4. Enhanced Metadata Output
- Comprehensive YAML output including:
  - OCR results with confidence scores
  - Image analysis (description, scene, text, story)
  - Text processing results with change tracking
  - Unified text section with best available source
  - Summary statistics across all processing stages

### 5. Proper Logging
- Detailed logging at each processing stage
- Progress tracking for each agent
- Error handling with informative messages
- Verbose mode for debugging

## New Files

1. **src/caption_extractor/ollama_client.py**
   - Client for connecting to local Ollama API
   - Methods for text and image-based generation
   - Model availability checking

2. **src/caption_extractor/image_agent.py**
   - Image analysis using visual LLM models
   - Structured response parsing
   - Configurable temperature and token limits

3. **src/caption_extractor/text_agent.py**
   - Text correction and completion
   - Context-aware processing using image analysis
   - Multiple processing modes (simple correction, enhancement, combination)

4. **src/caption_extractor/metadata_combiner.py**
   - Combines data from all sources
   - Creates unified text from best available source
   - Generates comprehensive summary statistics

5. **docs/AI_AGENTS.md**
   - Complete guide for AI agent features
   - Configuration examples
   - Model recommendations
   - Troubleshooting guide

6. **CHANGES.md**
   - This file documenting all changes

## Modified Files

1. **config.yml**
   - Added `pipeline` section for component control
   - Added `ollama` section with full configuration:
     - Connection settings
     - Model configuration
     - Image agent settings
     - Text agent settings with system prompts

2. **src/caption_extractor/main.py**
   - Initialize Ollama client
   - Initialize Image Agent and Text Agent
   - Pass agents to ImageProcessor
   - Graceful fallback if agents unavailable

3. **src/caption_extractor/image_processor.py**
   - Accept image_agent and text_agent parameters
   - Read pipeline configuration flags
   - Process images through 3-stage pipeline:
     1. OCR Processing
     2. Image Agent Analysis
     3. Text Agent Correction
   - Combine metadata from all sources
   - Enhanced error handling for each stage

4. **pyproject.toml**
   - Added `requests>=2.31.0` dependency

## Configuration

### Basic Configuration

```yaml
# Enable/disable processing components
pipeline:
  enable_ocr: true          # OCR text extraction
  enable_image_agent: true  # Image analysis with visual LLM
  enable_text_agent: true   # Text correction with LLM

# Ollama connection and models
ollama:
  host: "http://localhost:11434"
  timeout: 120
  models:
    vision_model: "llava:latest"
    text_model: "llama3.2:latest"
```

### Advanced Configuration

See `docs/AI_AGENTS.md` for:
- Custom system prompts
- Temperature adjustments
- Token limits
- Model alternatives

## Usage

### Prerequisites

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull llava:latest
ollama pull llama3.2:latest
```

### Running

```bash
# Install dependencies
pip install -e .

# Run with default config (all agents enabled)
python -m caption_extractor.main

# Run with custom config
python -m caption_extractor.main --config my_config.yml

# Run with verbose logging
python -m caption_extractor.main --verbose
```

## Output Example

Output YAML now includes:

```yaml
image_file: example.jpg
processed_at: '2025-11-13 00:50:00'
processing_time: 15.234

ocr:
  full_text: "OCR extracted text..."
  total_elements: 10
  avg_confidence: 0.89

image_analysis:
  description: "Detailed image description..."
  scene: "indoor, document"
  text: "Text visible in image..."
  story: "Context and narrative..."

text_processing:
  corrected_text: "Corrected and polished text..."
  changes: "List of corrections..."
  confidence: "high"

unified_text:
  primary_text: "Best quality text..."
  recommended_source: "text_processing"

summary:
  processing_stages: ['ocr', 'image_analysis', 'text_processing']
  has_extracted_text: true
  text_length: 150
```

## Performance

### Processing Time
- OCR only: ~1-2 seconds/image
- OCR + Image Agent: ~5-10 seconds/image
- Full pipeline: ~10-20 seconds/image

### Memory Requirements
- OCR: ~2GB RAM
- + Image Agent: +4GB RAM (llava:latest)
- + Text Agent: +2GB RAM (llama3.2:latest)

## Benefits

1. **Higher Accuracy**: LLM-corrected text reduces OCR errors
2. **Rich Metadata**: Multiple perspectives on image content
3. **Flexibility**: Enable only what you need
4. **Privacy**: Runs completely locally with Ollama
5. **Extensibility**: Easy to add new agents or models
6. **Backward Compatible**: Disable agents to use as before

## Migration Guide

### For Existing Users

No changes required! The system defaults to all components enabled. To use as before:

```yaml
pipeline:
  enable_ocr: true
  enable_image_agent: false
  enable_text_agent: false
```

### To Enable AI Agents

1. Install Ollama
2. Pull models: `ollama pull llava:latest` and `ollama pull llama3.2:latest`
3. Update config to enable agents (or use defaults)
4. Run as normal

## Known Limitations

1. Requires Ollama installation for AI agents
2. Processing time increases with agents enabled
3. Higher memory usage with visual models
4. First run downloads models (~4-6GB)

## Future Enhancements

Potential additions:
- Streaming responses for faster feedback
- Multi-language model support
- Custom model fine-tuning integration
- Batch optimization for multiple images
- GPU acceleration configuration

## Testing

All modules have been tested for:
- ✓ Import without errors
- ✓ Configuration loading
- ✓ Graceful degradation
- ✓ Error handling
- ✓ Metadata combination

## Documentation

See `docs/AI_AGENTS.md` for comprehensive documentation including:
- Detailed configuration guide
- Model recommendations
- Usage examples
- Troubleshooting
- Best practices

## Support

For issues or questions:
1. Check `docs/AI_AGENTS.md` troubleshooting section
2. Verify Ollama is running: `ollama list`
3. Check logs with `--verbose` flag
4. Review configuration in `config.yml`
