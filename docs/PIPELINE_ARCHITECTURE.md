# Pipeline-Based Image Processing Architecture

## Overview

The caption-extractor now uses a **pipeline-based processing model** with **YAML state management**. This architecture enables:

- ✅ **No Context Switching**: Each image processes through all steps sequentially  
- ✅ **State Persistence**: YAML files track completion status for each step
- ✅ **Resume Capability**: Failed images can be reprocessed from the failing step
- ✅ **Incremental Processing**: Steps are skipped if already completed
- ✅ **Step-Level Error Handling**: Failures in one step don't block subsequent steps

## Architecture Components

### 1. PipelineStateManager (`pipeline_state_manager.py`)

Manages YAML state files for each image with complete pipeline tracking.

**Key Methods:**
- `create_initial_state()`: Creates initial state for an image
- `load_state()`: Loads state from YAML file
- `save_state()`: Persists state to YAML file
- `mark_step_running()`: Marks a step as in-progress
- `mark_step_completed()`: Marks step complete with output data
- `mark_step_failed()`: Marks step failed with error message
- `mark_step_skipped()`: Marks step skipped (disabled or already done)
- `is_step_completed()`: Checks if step already completed
- `should_skip_step()`: Determines if step should be skipped

### 2. StepProcessor (`step_processor.py`)

Processes individual pipeline steps with state management integration.

**Pipeline Steps (In Order):**
1. `process_ocr_step()` - OCR text extraction
2. `process_image_agent_step()` - Image analysis/vision
3. `process_text_agent_step()` - Text processing/correction
4. `process_translation_step()` - Translation (optional)
5. `process_metadata_combination_step()` - Final metadata combination

### 3. ImageProcessor (`image_processor.py`)

Orchestrates the pipeline execution using state management and step processors.

**Flow:**
```
process_single_image():
  ├─ Load or create state YAML
  ├─ For each step in pipeline:
  │  ├─ Check if should skip (already completed)
  │  ├─ Execute step processor
  │  ├─ Mark step status (running/completed/failed)
  │  └─ Save state to YAML
  ├─ Mark pipeline completed
  └─ Return combined metadata
```

## State YAML Structure

Each image gets a `.yml` file in the same directory with this structure:

```yaml
image_path: /path/to/image.jpg
image_name: image.jpg
created_at: 2025-11-12T10:30:45.123456
updated_at: 2025-11-12T10:35:12.987654

pipeline_status:
  overall_status: completed  # pending/running/completed/failed
  current_step: null
  steps:
    ocr_processing:
      status: completed  # pending/running/completed/failed/skipped
      started_at: 2025-11-12T10:30:45.123456
      completed_at: 2025-11-12T10:31:02.456789
      duration: 17.333
      error: null
      data: {...ocr_data...}
    
    image_agent_analysis:
      status: completed
      started_at: 2025-11-12T10:31:02.456789
      completed_at: 2025-11-12T10:32:15.789012
      duration: 73.332
      error: null
      data: {...image_analysis...}
    
    text_agent_processing:
      status: completed
      started_at: 2025-11-12T10:32:15.789012
      completed_at: 2025-11-12T10:33:45.012345
      duration: 89.223
      error: null
      data: {...text_processing...}
    
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
      data: {...combined_metadata...}

results:
  ocr_data: {...}
  image_analysis: {...}
  text_processing: {...}
  translation_result: null
  combined_metadata: {...}
  processing_time: null

metadata:
  total_processing_time: 183.221
  failed_steps: []
  retries: 0
```

## Usage Example

### Basic Usage (No Changes Required)

The pipeline runs automatically during normal processing:

```bash
python -m caption_extractor.main --config config.yml --input-folder ./images
```

### Resume Failed Processing

The system automatically detects incomplete states and resumes from the failing step:

```bash
# Run again - incomplete images resume automatically
python -m caption_extractor.main --config config.yml --input-folder ./images
```

### Force Reprocessing

To force all steps to reprocess (even if completed):

```python
# In code, modify the step processor calls
# Add force_reprocess=True parameter (if implemented)
state_manager.reset_failed_step(state, 'ocr_processing')
```

## Configuration

Enable/disable steps in `config.yml`:

```yaml
pipeline:
  enable_ocr: true
  enable_image_agent: true
  enable_text_agent: true
  enable_translation: false  # Optional translation step
```

## Benefits

### 1. No Context Switching
- Each image processes completely through all steps
- No need to cache intermediate results
- Each step independently loads required data from YAML

### 2. State Persistence
- All processing tracked in YAML files
- Easy to inspect processing status
- Audit trail of all operations

### 3. Resume Capability
- Failed images automatically resume from the failing step
- No need to reprocess already-completed steps
- Efficient retry mechanism

### 4. Error Handling
- Individual step failures don't block entire pipeline
- Failures recorded with error messages
- Can continue with remaining steps or retry

### 5. Debugging
- Complete history in YAML files
- Can replay processing chain
- Track execution times per step

## Example Processing Flow

### First Run (Image Not Processed)

```
Image: photo.jpg
State: NOT_EXIST → CREATE

Step 1: OCR (pending → running → completed)
  - Load state: NEW
  - Execute OCR
  - Save state: ocr_data stored
  
Step 2: Image Agent (pending → running → completed)
  - Load state: includes ocr_data
  - Execute image analysis
  - Save state: image_analysis stored
  
Step 3: Text Agent (pending → running → completed)
  - Load state: includes ocr_data + image_analysis
  - Execute text processing
  - Save state: text_processing stored
  
Step 4: Translation (pending → skipped)
  - Load state: check if translation needed
  - Skip (not needed)
  - Save state: marked as skipped
  
Step 5: Metadata (pending → running → completed)
  - Load state: all previous data
  - Combine all metadata
  - Save state: combined_metadata stored
  
Result: COMPLETED ✓
```

### Retry After Failure (OCR Failed)

```
Image: photo.jpg
State: EXISTS (ocr_processing: FAILED)

Step 1: OCR (failed → retry)
  - Load state: includes failure info
  - Reset failed step
  - Retry OCR execution
  - Save state: now completed
  
Step 2: Image Agent (pending → running → completed)
  - Load state: fresh ocr_data
  - Continue normally
  ...
  
Result: COMPLETED ✓
```

### Incremental Update (Already Processed)

```
Image: photo.jpg
State: EXISTS (ALL STEPS: COMPLETED)

Step 1: OCR (completed → skipped)
  - Load state: check if completed
  - Skip (already done)
  
Step 2: Image Agent (completed → skipped)
  - Load state: check if completed
  - Skip (already done)
  
... (all steps skipped)

Result: COMPLETED ✓ (no reprocessing)
```

## Step Details

###OCR Processing Step
- **Input**: Image file path, configuration
- **Output**: Extracted text, layout, elements
- **Storage**: `state['results']['ocr_data']`
- **Dependent On**: None (first step)

### Image Agent Analysis Step
- **Input**: Image file (optionally resized)
- **Output**: Visual analysis, objects detected, descriptions
- **Storage**: `state['results']['image_analysis']`
- **Dependent On**: None
- **Note**: Can resize image based on config for optimization

### Text Agent Processing Step
- **Input**: OCR text + Image analysis text
- **Output**: Corrected text, classifications, metadata
- **Storage**: `state['results']['text_processing']`
- **Dependent On**: OCR + Image Agent steps (data available)

### Translation Step (Optional)
- **Input**: Primary text from text agent
- **Output**: Translated text
- **Storage**: `state['results']['translation_result']`
- **Dependent On**: Text Agent step
- **Condition**: Only if `needTranslation` flag is true

### Metadata Combination Step
- **Input**: All previous step results
- **Output**: Combined final metadata
- **Storage**: `state['results']['combined_metadata']`
- **Dependent On**: All previous steps

## Monitoring & Debugging

### Check Processing Status

```python
state_manager = PipelineStateManager()
state = state_manager.load_state('/path/to/image.jpg')

# Check overall status
print(state['pipeline_status']['overall_status'])

# Check individual steps
for step in state_manager.get_all_steps():
    step_status = state_manager.get_step_status(state, step)
    duration = state['pipeline_status']['steps'][step].get('duration')
    print(f"{step}: {step_status.value} ({duration}s)")

# Get summary
summary = state_manager.get_pipeline_summary(state)
print(summary)
```

### View YAML File

```bash
# View complete state
cat image.yml

# View specific step status
grep -A 10 "ocr_processing:" image.yml

# View processing times
grep "duration:" image.yml
```

## Performance Considerations

1. **YAML I/O**: Each step saves state to disk (minimal overhead)
2. **Resume Speed**: Skipping completed steps is much faster
3. **Memory**: No caching of all images in memory
4. **Threading**: Batch processing still uses threadpooling for multiple images

## Future Enhancements

- [ ] Database backend for state management
- [ ] Real-time progress API
- [ ] Parallel step execution (DAG-based)
- [ ] Distributed processing
- [ ] Performance metrics dashboard
