"""Pipeline state management for image processing with YAML persistence."""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from enum import Enum
from datetime import datetime


class StepStatus(Enum):
    """Pipeline step status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class PipelineStateManager:
    """Manages pipeline state persistence in YAML files."""
    
    def __init__(self, state_file_path: str = None):
        """Initialize the pipeline state manager.
        
        Args:
            state_file_path: Optional path to save state YAML file
        """
        self.logger = logging.getLogger(__name__)
        self.state_file_path = state_file_path
        
        # Define pipeline steps in order
        self.pipeline_steps = [
            'ocr_processing',
            'image_agent_analysis',
            'text_agent_processing',
            'translation',
            'metadata_combination'
        ]
    
    def create_initial_state(self, image_path: str) -> Dict[str, Any]:
        """Create initial pipeline state for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Initial state dictionary
        """
        return {
            'image_path': str(image_path),
            'image_name': Path(image_path).name,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'pipeline_status': {
                'overall_status': 'pending',
                'current_step': self.pipeline_steps[0],
                'steps': {
                    step: {
                        'status': StepStatus.PENDING.value,
                        'started_at': None,
                        'completed_at': None,
                        'duration': None,
                        'error': None,
                        'data': None
                    }
                    for step in self.pipeline_steps
                }
            },
            'results': {
                'ocr_data': None,
                'vl_model_data': None,
                'text_processing': None,
                'translation_result': None,
                'combined_metadata': None,
                'processing_time': None
            },
            'metadata': {
                'total_processing_time': 0.0,
                'failed_steps': [],
                'retries': 0
            }
        }
    
    def load_state(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Load state from YAML file for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            State dictionary or None if file doesn't exist
        """
        yaml_path = self._get_yaml_path(image_path)
        
        if not os.path.exists(yaml_path):
            return None
        
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                state = yaml.safe_load(f)
                self.logger.debug(f"Loaded state from {yaml_path}")
                return state
        except Exception as e:
            self.logger.error(f"Error loading state from {yaml_path}: {e}")
            return None
    
    def save_state(self, image_path: str, state: Dict[str, Any]) -> bool:
        """Save state to YAML file.
        
        Args:
            image_path: Path to the image file
            state: State dictionary to save
            
        Returns:
            True if save was successful, False otherwise
        """
        yaml_path = self._get_yaml_path(image_path)
        
        try:
            # Update timestamp
            state['updated_at'] = datetime.now().isoformat()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
            
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(state, f, default_flow_style=False,
                          allow_unicode=True, indent=2)
            
            self.logger.debug(f"Saved state to {yaml_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving state to {yaml_path}: {e}")
            return False
    
    def _get_yaml_path(self, image_path: str) -> str:
        """Get the YAML file path for an image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Path to the corresponding YAML file
        """
        image_file = Path(image_path)
        return str(image_file.parent / f"{image_file.stem}.yml")
    
    def get_step_status(self, state: Dict[str, Any], step: str) -> StepStatus:
        """Get the status of a specific step.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            
        Returns:
            Step status
        """
        try:
            status_str = state['pipeline_status']['steps'][step]['status']
            return StepStatus(status_str)
        except (KeyError, ValueError):
            return StepStatus.PENDING
    
    def is_step_completed(self, state: Dict[str, Any], step: str) -> bool:
        """Check if a step is already completed.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            
        Returns:
            True if step is completed, False otherwise
        """
        status = self.get_step_status(state, step)
        return status == StepStatus.COMPLETED
    
    def is_step_failed(self, state: Dict[str, Any], step: str) -> bool:
        """Check if a step has failed.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            
        Returns:
            True if step has failed, False otherwise
        """
        status = self.get_step_status(state, step)
        return status == StepStatus.FAILED
    
    def should_skip_step(self, state: Dict[str, Any], step: str, 
                        force_reprocess: bool = False) -> bool:
        """Determine if a step should be skipped.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            force_reprocess: If True, never skip (force reprocessing)
            
        Returns:
            True if step should be skipped, False if it should run
        """
        if force_reprocess:
            return False
        
        status = self.get_step_status(state, step)
        return status == StepStatus.COMPLETED
    
    def mark_step_running(self, state: Dict[str, Any], step: str) -> Dict[str, Any]:
        """Mark a step as running.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            
        Returns:
            Updated state dictionary
        """
        state['pipeline_status']['steps'][step]['status'] = StepStatus.RUNNING.value
        state['pipeline_status']['steps'][step]['started_at'] = datetime.now().isoformat()
        state['pipeline_status']['current_step'] = step
        state['pipeline_status']['overall_status'] = 'running'
        return state
    
    def mark_step_completed(self, state: Dict[str, Any], step: str, 
                           data: Any = None, duration: float = None) -> Dict[str, Any]:
        """Mark a step as completed.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            data: Step output data
            duration: Execution duration in seconds
            
        Returns:
            Updated state dictionary
        """
        state['pipeline_status']['steps'][step]['status'] = StepStatus.COMPLETED.value
        state['pipeline_status']['steps'][step]['completed_at'] = datetime.now().isoformat()
        if duration is not None:
            state['pipeline_status']['steps'][step]['duration'] = round(duration, 3)
        
        # Store step result in both locations
        if data is not None:
            state['results'][self._get_result_key(step)] = data
            # Also store in steps.data for direct access
            state['pipeline_status']['steps'][step]['data'] = data
        
        return state
    
    def mark_step_failed(self, state: Dict[str, Any], step: str, 
                        error: str) -> Dict[str, Any]:
        """Mark a step as failed.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            error: Error message
            
        Returns:
            Updated state dictionary
        """
        state['pipeline_status']['steps'][step]['status'] = StepStatus.FAILED.value
        state['pipeline_status']['steps'][step]['error'] = error
        state['pipeline_status']['steps'][step]['completed_at'] = datetime.now().isoformat()
        state['pipeline_status']['overall_status'] = 'failed'
        
        # Add to failed steps list
        if step not in state['metadata']['failed_steps']:
            state['metadata']['failed_steps'].append(step)
        
        return state
    
    def mark_step_skipped(self, state: Dict[str, Any], step: str, 
                         reason: str = None) -> Dict[str, Any]:
        """Mark a step as skipped.
        
        Args:
            state: Pipeline state dictionary
            step: Step name
            reason: Reason for skipping
            
        Returns:
            Updated state dictionary
        """
        state['pipeline_status']['steps'][step]['status'] = StepStatus.SKIPPED.value
        state['pipeline_status']['steps'][step]['completed_at'] = datetime.now().isoformat()
        if reason:
            state['pipeline_status']['steps'][step]['error'] = f"Skipped: {reason}"
        return state
    
    def mark_pipeline_completed(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Mark the entire pipeline as completed.
        
        Args:
            state: Pipeline state dictionary
            
        Returns:
            Updated state dictionary
        """
        state['pipeline_status']['overall_status'] = 'completed'
        state['pipeline_status']['current_step'] = None
        
        # Calculate total processing time
        total_time = 0.0
        for step in self.pipeline_steps:
            step_data = state['pipeline_status']['steps'][step]
            if step_data.get('duration'):
                total_time += step_data['duration']
        
        state['metadata']['total_processing_time'] = round(total_time, 3)
        return state
    
    def get_next_pending_step(self, state: Dict[str, Any]) -> Optional[str]:
        """Get the next pending step to process.
        
        Args:
            state: Pipeline state dictionary
            
        Returns:
            Step name or None if all steps are processed
        """
        for step in self.pipeline_steps:
            status = self.get_step_status(state, step)
            if status == StepStatus.PENDING:
                return step
        return None
    
    def get_pipeline_summary(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get a summary of the pipeline execution.
        
        Args:
            state: Pipeline state dictionary
            
        Returns:
            Summary dictionary
        """
        steps_status = {}
        for step in self.pipeline_steps:
            step_info = state['pipeline_status']['steps'][step]
            steps_status[step] = {
                'status': step_info['status'],
                'duration': step_info.get('duration'),
                'error': step_info.get('error')
            }
        
        return {
            'image_name': state['image_name'],
            'overall_status': state['pipeline_status']['overall_status'],
            'steps': steps_status,
            'total_time': state['metadata']['total_processing_time'],
            'failed_steps': state['metadata']['failed_steps'],
            'created_at': state['created_at'],
            'completed_at': state.get('updated_at')
        }
    
    def _get_result_key(self, step: str) -> str:
        """Map step name to result key.
        
        Args:
            step: Step name
            
        Returns:
            Result key name
        """
        key_map = {
            'ocr_processing': 'ocr_data',
            'image_agent_analysis': 'vl_model_data',
            'text_agent_processing': 'text_processing',
            'translation': 'translation_result',
            'metadata_combination': 'combined_metadata'
        }
        return key_map.get(step, step)
    
    def reset_failed_step(self, state: Dict[str, Any], step: str) -> Dict[str, Any]:
        """Reset a failed step back to pending state.
        
        Args:
            state: Pipeline state dictionary
            step: Step name to reset
            
        Returns:
            Updated state dictionary
        """
        state['pipeline_status']['steps'][step] = {
            'status': StepStatus.PENDING.value,
            'started_at': None,
            'completed_at': None,
            'duration': None,
            'error': None,
            'data': None
        }
        
        # Remove from failed steps list
        if step in state['metadata']['failed_steps']:
            state['metadata']['failed_steps'].remove(step)
        
        return state
    
    def get_all_steps(self) -> List[str]:
        """Get list of all pipeline steps in order.
        
        Returns:
            List of step names
        """
        return self.pipeline_steps.copy()
