"""Metadata combiner to merge data from OCR, image agent, and text agent."""

import logging
import time
from typing import Dict, Any, Optional
from pathlib import Path


class MetadataCombiner:
    """Combines metadata from multiple sources into a comprehensive object."""
    
    def __init__(self):
        """Initialize the metadata combiner."""
        self.logger = logging.getLogger(__name__)
    
    def combine_metadata(
        self,
        image_path: str,
        ocr_data: Optional[Dict[str, Any]] = None,
        image_analysis: Optional[Dict[str, Any]] = None,
        text_processing: Optional[Dict[str, Any]] = None,
        translation_result: Optional[Dict[str, Any]] = None,
        processing_time: float = 0.0
    ) -> Dict[str, Any]:
        """Combine metadata from all sources.
        
        Args:
            image_path: Path to the image file
            ocr_data: OCR extraction results
            image_analysis: Image agent analysis results
            text_processing: Text agent processing results
            translation_result: Translation results (optional)
            processing_time: Total processing time
            
        Returns:
            Combined metadata dictionary
        """
        try:
            self.logger.debug(f"Combining metadata for image: {image_path}")
            
            # Base metadata
            image_file = Path(image_path)
            metadata = {
                'image_file': image_file.name,
                'image_path': str(image_path),
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'processing_time': round(processing_time, 3)
            }
            
            # Add OCR data
            if ocr_data:
                metadata['ocr'] = {
                    'full_text': ocr_data.get('full_text', ''),
                    'text_lines': ocr_data.get('text_lines', []),
                    'total_elements': ocr_data.get('total_elements', 0),
                    'avg_confidence': ocr_data.get('avg_confidence', 0.0),
                    'min_confidence': ocr_data.get('min_confidence', 0.0),
                    'max_confidence': ocr_data.get('max_confidence', 0.0)
                }
            else:
                metadata['ocr'] = {
                    'full_text': '',
                    'text_lines': [],
                    'total_elements': 0,
                    'note': 'OCR processing was disabled or failed'
                }
            
            # Add image analysis
            if image_analysis:
                metadata['image_analysis'] = {
                    'description': image_analysis.get('description', ''),
                    'scene': image_analysis.get('scene', ''),
                    'text': image_analysis.get('text', ''),
                    'story': image_analysis.get('story', '')
                }
            else:
                metadata['image_analysis'] = {
                    'description': '',
                    'scene': '',
                    'text': '',
                    'story': '',
                    'note': 'Image analysis was disabled or failed'
                }
            
            # Add text processing
            if text_processing:
                metadata['text_processing'] = {
                    'corrected_text': text_processing.get(
                        'corrected_text', ''
                    ),
                    'changes': text_processing.get('changes', ''),
                    'confidence': text_processing.get('confidence',
                                                      'unknown'),
                    # Optional translation fields
                    'translated_text': text_processing.get(
                        'translated_text', ''
                    ),
                    'translation': text_processing.get('translation', {}),
                    'language': text_processing.get('language', ''),
                    'language_code': text_processing.get(
                        'language_code', ''
                    ),
                    'needTranslation': text_processing.get(
                        'needTranslation', False
                    )
                }
            else:
                metadata['text_processing'] = {
                    'corrected_text': '',
                    'changes': '',
                    'confidence': 'unknown',
                    'note': 'Text processing was disabled or failed'
                }
            
            # Add translation result if available
            if translation_result:
                metadata['translation'] = {
                    'translated_text': translation_result.get(
                        'translated_text', ''
                    ),
                    'source_language': translation_result.get(
                        'source_language', ''
                    ),
                    'target_language': translation_result.get(
                        'target_language', ''
                    ),
                    'translation_model': translation_result.get(
                        'translation_model', ''
                    )
                }
            else:
                metadata['translation'] = {
                    'translated_text': '',
                    'note': 'Translation was disabled or not needed'
                }
            
            # Create a unified text section combining all sources
            metadata['unified_text'] = self._create_unified_text(
                ocr_data, image_analysis, text_processing
            )
            
            # Add summary statistics
            metadata['summary'] = self._create_summary(metadata)
            
            self.logger.debug("Successfully combined metadata")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Error combining metadata: {e}", exc_info=True)
            # Return minimal metadata on error
            return {
                'image_file': Path(image_path).name,
                'image_path': str(image_path),
                'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'processing_time': round(processing_time, 3),
                'error': str(e)
            }
    
    def _create_unified_text(
        self,
        ocr_data: Optional[Dict[str, Any]],
        image_analysis: Optional[Dict[str, Any]],
        text_processing: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Create unified text section from all sources.
        
        Args:
            ocr_data: OCR results
            image_analysis: Image analysis results
            text_processing: Text processing results
            
        Returns:
            Unified text dictionary
        """
        unified = {
            'primary_text': '',
            'alternative_texts': [],
            'recommended_source': 'none'
        }
        
        # Determine primary text source based on availability and quality
        if text_processing and text_processing.get('corrected_text'):
            unified['primary_text'] = text_processing['corrected_text']
            unified['recommended_source'] = 'text_processing'
        elif ocr_data and ocr_data.get('full_text'):
            unified['primary_text'] = ocr_data['full_text']
            unified['recommended_source'] = 'ocr'
        elif image_analysis and image_analysis.get('text'):
            unified['primary_text'] = image_analysis['text']
            unified['recommended_source'] = 'image_analysis'
        
        # Add alternative text sources
        if (ocr_data and ocr_data.get('full_text') and
                unified['recommended_source'] != 'ocr'):
            unified['alternative_texts'].append({
                'source': 'ocr',
                'text': ocr_data['full_text']
            })
        
        if (image_analysis and image_analysis.get('text') and
                unified['recommended_source'] != 'image_analysis'):
            unified['alternative_texts'].append({
                'source': 'image_analysis',
                'text': image_analysis['text']
            })
        
        return unified
    
    def _create_summary(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Create summary statistics.
        
        Args:
            metadata: Combined metadata
            
        Returns:
            Summary dictionary
        """
        summary = {
            'has_ocr_data': False,
            'has_image_analysis': False,
            'has_text_processing': False,
            'text_sources_count': 0,
            'processing_stages': []
        }
        
        # Check what data we have
        ocr_data = metadata.get('ocr', {})
        if ocr_data.get('total_elements', 0) > 0:
            summary['has_ocr_data'] = True
            summary['text_sources_count'] += 1
            summary['processing_stages'].append('ocr')
        
        image_analysis = metadata.get('image_analysis', {})
        if image_analysis.get('description') or image_analysis.get('text'):
            summary['has_image_analysis'] = True
            if image_analysis.get('text'):
                summary['text_sources_count'] += 1
            summary['processing_stages'].append('image_analysis')
        
        text_processing = metadata.get('text_processing', {})
        if text_processing.get('corrected_text'):
            summary['has_text_processing'] = True
            summary['processing_stages'].append('text_processing')
        
        # Add quality indicators
        if ocr_data.get('avg_confidence'):
            summary['ocr_avg_confidence'] = ocr_data['avg_confidence']
        
        if text_processing.get('confidence'):
            summary['text_processing_confidence'] = (
                text_processing['confidence']
            )
        
        # Add content indicators
        unified_text = metadata.get('unified_text', {})
        if unified_text.get('primary_text'):
            summary['has_extracted_text'] = True
            summary['text_length'] = len(unified_text['primary_text'])
        else:
            summary['has_extracted_text'] = False
            summary['text_length'] = 0
        
        return summary
    
    def create_minimal_metadata(
        self,
        image_path: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create minimal metadata for failed processing.
        
        Args:
            image_path: Path to the image file
            error: Error message if any
            
        Returns:
            Minimal metadata dictionary
        """
        image_file = Path(image_path)
        metadata = {
            'image_file': image_file.name,
            'image_path': str(image_path),
            'processed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'processing_time': 0.0,
            'status': 'failed'
        }
        
        if error:
            metadata['error'] = error
        
        return metadata
    
    def validate_metadata(self, metadata: Dict[str, Any]) -> bool:
        """Validate metadata structure.
        
        Args:
            metadata: Metadata dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            required_fields = ['image_file', 'image_path', 'processed_at']
            for field in required_fields:
                if field not in metadata:
                    self.logger.warning(f"Missing required field: {field}")
                    return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating metadata: {e}")
            return False
