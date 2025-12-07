"""Image agent for analyzing images using visual LLM models."""

import logging
import re
from typing import Dict, Any, Optional
from ..ollama_client import OllamaClient


class ImageAgent:
    """Agent for analyzing images using visual LLM models."""
    
    def __init__(self, config: Dict[str, Any], ollama_client: OllamaClient):
        """Initialize the image agent.
        
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
        agent_config = ollama_config.get('image_agent', {})
        
        self.vision_model = models_config.get('vision_model', 'llava:latest')
        self.temperature = agent_config.get('temperature', 0.7)
        self.max_tokens = agent_config.get('max_tokens', 1000)
        self.system_prompt = agent_config.get('system_prompt', '')
        
        self.logger.info(f"Initialized Image Agent with model: {self.vision_model}")
        
        # Verify model availability
        if not self.ollama_client.check_model_available(self.vision_model):
            self.logger.warning(
                f"Vision model '{self.vision_model}' not available. "
                "Image agent may not work properly. "
                f"Pull the model using: ollama pull {self.vision_model}"
            )
    
    def analyze_image(self, image_path: str) -> Optional[Dict[str, Any]]:
        """Analyze image to extract description, scene, text, and story.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing analysis results with model and timing info, or None if failed
        """
        try:
            self.logger.info(f"Analyzing image with vision model: {image_path}")
            
            # Prepare prompt
            prompt = """Analyze this image and provide a detailed analysis with the following sections:
1. **Description**: Provide a comprehensive description of what you see in the image (objects, people, colors, composition, etc.)
2. **Scene**: Identify the type of scene or setting (e.g., indoor/outdoor, document/photo, nature/urban, etc.)
3. **Text**: List any visible text in the image, make sure you do not translate or change or provide any other commentary. Only provide text word 2 word exact as extracted. If there's no text, state "No visible text"
4. **Story**: Create a brief narrative or context about what might be happening in the image or its purpose

Please structure your response with clear section headers."""
            
            # Call Ollama with image
            response_data = self.ollama_client.generate_with_image(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_path,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            
            if not response_data:
                self.logger.error("Failed to get response from vision model")
                return None
            
            # Extract response text and metadata
            response = response_data.get('response', '')
            model = response_data.get('model', self.vision_model)
            processing_time = response_data.get('processing_time', 0.0)
            
            # Parse the response
            analysis = self._parse_response(response)
            
            # Add model and timing info
            analysis['model'] = model
            analysis['processing_time'] = processing_time
            
            self.logger.info(f"Successfully analyzed image with vision model in {processing_time}s")
            self.logger.debug(f"Analysis result: {analysis}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error analyzing image: {e}", exc_info=True)
            return None
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """Parse the LLM response into structured data.
        
        Args:
            response: Raw response from LLM
            
        Returns:
            Parsed analysis dictionary
        """
        analysis = {
            'description': '',
            'scene': '',
            'text': '',
            'story': '',
            'raw_response': response
        }
        
        try:
            # Try to extract sections using common patterns
            sections = {
                'description': r'(?:\*\*)?Description(?:\*\*)?:?\s*(.*?)(?=(?:\*\*)?(?:Scene|Text|Story)(?:\*\*)?:|$)',
                'scene': r'(?:\*\*)?Scene(?:\*\*)?:?\s*(.*?)(?=(?:\*\*)?(?:Description|Text|Story)(?:\*\*)?:|$)',
                'text': r'(?:\*\*)?Text(?:\*\*)?:?\s*(.*?)(?=(?:\*\*)?(?:Description|Scene|Story)(?:\*\*)?:|$)',
                'story': r'(?:\*\*)?Story(?:\*\*)?:?\s*(.*?)(?=(?:\*\*)?(?:Description|Scene|Text)(?:\*\*)?:|$)'
            }
            
            for key, pattern in sections.items():
                match = re.search(pattern, response, re.IGNORECASE | re.DOTALL)
                if match:
                    content = match.group(1).strip()
                    # Clean up the content
                    content = re.sub(r'\n\s*\n', '\n', content)  # Remove extra newlines
                    content = content.strip()
                    analysis[key] = content
            
            # If parsing fails, try simpler approach
            if not any([analysis['description'], analysis['scene'], analysis['text'], analysis['story']]):
                # Split by double newlines and try to find sections
                lines = response.split('\n')
                current_section = None
                content_buffer = []
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Check if this is a section header
                    lower_line = line.lower()
                    if any(keyword in lower_line for keyword in ['description', 'scene', 'text', 'story']):
                        # Save previous section
                        if current_section and content_buffer:
                            analysis[current_section] = '\n'.join(content_buffer).strip()
                            content_buffer = []
                        
                        # Determine new section
                        if 'description' in lower_line:
                            current_section = 'description'
                        elif 'scene' in lower_line:
                            current_section = 'scene'
                        elif 'text' in lower_line:
                            current_section = 'text'
                        elif 'story' in lower_line:
                            current_section = 'story'
                        
                        # Remove section header from line and add remaining content
                        content = re.sub(r'(?:\*\*)?(?:description|scene|text|story)(?:\*\*)?:?\s*', '', line, flags=re.IGNORECASE)
                        if content:
                            content_buffer.append(content)
                    elif current_section:
                        content_buffer.append(line)
                
                # Save last section
                if current_section and content_buffer:
                    analysis[current_section] = '\n'.join(content_buffer).strip()
            
            # If still no content, use the whole response as description
            if not any([analysis['description'], analysis['scene'], analysis['text'], analysis['story']]):
                analysis['description'] = response.strip()
                self.logger.warning("Could not parse structured response, using full response as description")
        
        except Exception as e:
            self.logger.error(f"Error parsing response: {e}")
            # Fallback: use entire response as description
            analysis['description'] = response.strip()
        
        return analysis
    
    def get_quick_description(self, image_path: str) -> Optional[str]:
        """Get a quick description of the image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Description string or None if failed
        """
        try:
            prompt = "Provide a brief, one-paragraph description of this image."
            
            response_data = self.ollama_client.generate_with_image(
                model=self.vision_model,
                prompt=prompt,
                image_path=image_path,
                temperature=self.temperature,
                max_tokens=200
            )
            
            if response_data:
                return response_data.get('response', '').strip()
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting quick description: {e}")
            return None
