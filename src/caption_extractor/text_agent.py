"""Text agent for processing and correcting OCR-extracted text using LLM."""

import logging
from typing import Dict, Any, Optional, List
from .ollama_client import OllamaClient


class TextAgent:
    """Agent for processing and correcting OCR text using LLM models."""
    
    def __init__(self, config: Dict[str, Any], ollama_client: OllamaClient):
        """Initialize the text agent.
        
        Args:
            config: Configuration dictionary
            ollama_client: Ollama client instance
        """
        self.config = config
        self.ollama_client = ollama_client
        self.logger = logging.getLogger(__name__)
        
        # Get configuration
        ollama_config = config.get('ollama', {})
        models_config = ollama_config.get('models', {})
        agent_config = ollama_config.get('text_agent', {})
        
        self.text_model = models_config.get('text_model', 'llama3.2:latest')
        self.temperature = agent_config.get('temperature', 0.3)
        self.max_tokens = agent_config.get('max_tokens', 2000)
        self.system_prompt = agent_config.get('system_prompt', '')
        
        self.logger.info(f"Initialized Text Agent with model: {self.text_model}")
        
        # Verify model availability
        if not self.ollama_client.check_model_available(self.text_model):
            self.logger.warning(
                f"Text model '{self.text_model}' not available. "
                "Text agent may not work properly. "
                f"Pull the model using: ollama pull {self.text_model}"
            )
    
    def process_text(
        self, 
        ocr_text: str, 
        image_analysis: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Process and correct OCR-extracted text.
        
        Args:
            ocr_text: Raw OCR-extracted text
            image_analysis: Optional image analysis data for context
            
        Returns:
            Dictionary containing corrected text and metadata or None if failed
        """
        try:
            self.logger.info("Processing text with LLM for correction and completion")
            
            # Build context from image analysis if available
            context = ""
            if image_analysis:
                context = f"\n\nImage Context:\n"
                if image_analysis.get('description'):
                    context += f"- Description: {image_analysis['description']}\n"
                if image_analysis.get('scene'):
                    context += f"- Scene: {image_analysis['scene']}\n"
                if image_analysis.get('text'):
                    context += f"- Visible text (from vision model): {image_analysis['text']}\n"
            
            # Prepare prompt
            prompt = f"""I have extracted text from an image using OCR. Please review and correct any errors, complete incomplete words or sentences, and improve readability while maintaining the original meaning.
{context}
OCR Extracted Text:
{ocr_text}

Please provide:
1. The corrected and completed text
2. A brief summary of changes made (if any)
3. Confidence level in the corrections (low/medium/high)

Format your response as:
CORRECTED TEXT:
[your corrected text here]

CHANGES:
[list of changes made]

CONFIDENCE:
[low/medium/high]"""
            
            # Call Ollama for text processing
            response = self.ollama_client.generate_text(
                model=self.text_model,
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            if not response:
                self.logger.error("Failed to get response from text model")
                return None
            
            # Parse the response
            result = self._parse_response(response, ocr_text)

            # Set primary_text for downstream use
            primary_text = result.get('corrected_text') or ocr_text or ''
            result['primary_text'] = primary_text

            # Detect language of the primary text and mark if translation is needed
            try:
                lang_info = self.detect_language(primary_text)
                result['language'] = lang_info.get('language', 'unknown')
                result['language_code'] = lang_info.get('code', '')
                # Mark needTranslation = True when detected language is not English
                need_translation = False
                code = (lang_info.get('code') or '').lower()
                name = (lang_info.get('language') or '').lower()
                if code and code != 'en' and code != 'eng':
                    need_translation = True
                elif name and 'english' not in name and name != 'en':
                    need_translation = True

                result['needTranslation'] = need_translation
            except Exception:
                # If detection fails, be conservative and assume no translation
                result['language'] = 'unknown'
                result['language_code'] = ''
                result['needTranslation'] = False
            
            self.logger.info("Successfully processed text with LLM")
            self.logger.debug(f"Text processing result: {result}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing text: {e}", exc_info=True)
            return None
    
    def _parse_response(self, response: str, original_text: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data.
        
        Args:
            response: Raw response from LLM
            original_text: Original OCR text for fallback
            
        Returns:
            Parsed processing result dictionary
        """
        result = {
            'corrected_text': '',
            'changes': '',
            'confidence': 'unknown',
            'raw_response': response
        }
        
        try:
            # Extract corrected text
            corrected_match = response.split('CORRECTED TEXT:')
            if len(corrected_match) > 1:
                # Get text after "CORRECTED TEXT:" and before next section
                corrected_section = corrected_match[1].split('CHANGES:')[0]
                result['corrected_text'] = corrected_section.strip()
            
            # Extract changes
            changes_match = response.split('CHANGES:')
            if len(changes_match) > 1:
                changes_section = changes_match[1].split('CONFIDENCE:')[0]
                result['changes'] = changes_section.strip()
            
            # Extract confidence
            confidence_match = response.split('CONFIDENCE:')
            if len(confidence_match) > 1:
                confidence_text = confidence_match[1].strip().lower()
                if 'high' in confidence_text:
                    result['confidence'] = 'high'
                elif 'medium' in confidence_text:
                    result['confidence'] = 'medium'
                elif 'low' in confidence_text:
                    result['confidence'] = 'low'
            
            # Fallback: if no structured output, use the whole response as corrected text
            if not result['corrected_text']:
                result['corrected_text'] = response.strip()
                result['changes'] = 'Unable to parse structured response'
                result['confidence'] = 'unknown'
                self.logger.warning("Could not parse structured response, using full response as corrected text")
        
        except Exception as e:
            self.logger.error(f"Error parsing text processing response: {e}")
            # Fallback to original text
            result['corrected_text'] = original_text
            result['changes'] = f'Error during parsing: {e}'
            result['confidence'] = 'low'
        
        return result

    def detect_language(self, text: str) -> Dict[str, str]:
        """Detect the primary language of the given text using the LLM.

        Returns a dict with keys: 'language' (name) and 'code' (iso code, e.g., 'en').
        """
        try:
            if not text or not text.strip():
                return {'language': 'unknown', 'code': ''}

            prompt = f"""Determine the primary language of the following text. Return ONLY the language name and the ISO 639-1 code in the following JSON format:
{{"language": "<Language Name>", "code": "<iso_code>"}}

Text:
""" + text

            response = self.ollama_client.generate_text(
                model=self.text_model,
                prompt=prompt,
                system_prompt="",
                temperature=0.0,
                max_tokens=50
            )

            if not response:
                return {'language': 'unknown', 'code': ''}

            # Try to parse JSON-like output
            resp = response.strip()
            # crude parse: look for code and language
            lang = ''
            code = ''
            # attempt to find iso code in response
            low = resp.lower()
            # common tokens
            if 'english' in low or 'en' in low.split():
                lang = 'English'
                code = 'en'
            else:
                # try to extract JSON-like fields
                try:
                    import re

                    m_lang = re.search(r'"language"\s*:\s*"([^"]+)"', resp)
                    m_code = re.search(r'"code"\s*:\s*"([^"]+)"', resp)
                    if m_lang:
                        lang = m_lang.group(1)
                    if m_code:
                        code = m_code.group(1)
                except Exception:
                    pass

            # fallback: if nothing parsed, return full response as language field
            if not lang and resp:
                # take first token
                lang = resp.split('\n')[0].strip()

            return {'language': lang or 'unknown', 'code': code or ''}
        except Exception:
            return {'language': 'unknown', 'code': ''}

    
    def correct_text_simple(self, text: str) -> Optional[str]:
        """Simple text correction without detailed analysis.
        
        Args:
            text: Text to correct
            
        Returns:
            Corrected text or None if failed
        """
        try:
            prompt = f"""Please correct any spelling, grammar, or OCR errors in the following text. Return only the corrected text without explanations:

{text}"""
            
            response = self.ollama_client.generate_text(
                model=self.text_model,
                prompt=prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            return response.strip() if response else None
            
        except Exception as e:
            self.logger.error(f"Error in simple text correction: {e}")
            return None
    
    def enhance_text(
        self, 
        text: str, 
        task: str = "improve readability"
    ) -> Optional[str]:
        """Enhance text for specific task.
        
        Args:
            text: Text to enhance
            task: Enhancement task (e.g., "improve readability", "make concise", "expand")
            
        Returns:
            Enhanced text or None if failed
        """
        try:
            prompt = f"""Task: {task}

Text:
{text}

Please {task} for the above text. Return only the enhanced text."""
            
            response = self.ollama_client.generate_text(
                model=self.text_model,
                prompt=prompt,
                temperature=self.temperature + 0.2,  # Slightly higher temperature for creativity
                max_tokens=self.max_tokens
            )
            
            return response.strip() if response else None
            
        except Exception as e:
            self.logger.error(f"Error enhancing text: {e}")
            return None
    
    def combine_texts(
        self, 
        ocr_text: str, 
        vision_text: str
    ) -> Optional[str]:
        """Combine and reconcile text from OCR and vision model.
        
        Args:
            ocr_text: Text from OCR
            vision_text: Text from vision model
            
        Returns:
            Combined and corrected text or None if failed
        """
        try:
            prompt = f"""I have two sources of text from the same image:

OCR Text:
{ocr_text}

Vision Model Text:
{vision_text}

Please combine and reconcile these two sources to produce the most accurate and complete text. Consider that:
- OCR might have spelling errors but captures text structure
- Vision model might miss some text but can provide context
- Look for complementary information

Return only the final combined and corrected text."""
            
            response = self.ollama_client.generate_text(
                model=self.text_model,
                prompt=prompt,
                temperature=0.2,  # Lower temperature for accuracy
                max_tokens=self.max_tokens
            )
            
            return response.strip() if response else None
            
        except Exception as e:
            self.logger.error(f"Error combining texts: {e}")
            return None
