"""Ollama client for connecting to local Ollama instance."""

import logging
import base64
import requests
from typing import Dict, Any, Optional
from pathlib import Path


class OllamaClient:
    """Client for interacting with local Ollama API."""
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize the Ollama client.
        
        Args:
            config: Ollama configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        ollama_config = config.get('ollama', {})
        self.host = ollama_config.get('host', 'http://localhost:11434')
        self.timeout = ollama_config.get('timeout', 120)
        
        self.logger.info(f"Initialized Ollama client with host: {self.host}")
        
        # Verify connection
        if not self._check_connection():
            self.logger.warning("Could not connect to Ollama. Make sure Ollama is running.")
    
    def _check_connection(self) -> bool:
        """Check if Ollama server is accessible.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            if response.status_code == 200:
                self.logger.info("Successfully connected to Ollama")
                return True
            else:
                self.logger.warning(f"Ollama returned status code: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Failed to connect to Ollama: {e}")
            return False
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 string.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Base64 encoded image string
        """
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def generate_with_image(
        self, 
        model: str, 
        prompt: str, 
        image_path: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """Generate text response based on image and prompt.
        
        Args:
            model: Model name to use
            prompt: User prompt
            image_path: Path to image file
            system_prompt: System prompt (optional)
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response or None if failed
        """
        try:
            self.logger.debug(f"Generating with image using model: {model}")
            
            # Encode image
            image_b64 = self._encode_image(image_path)
            
            # Prepare request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "images": [image_b64],
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Make request
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                self.logger.debug(f"Successfully generated response ({len(generated_text)} chars)")
                return generated_text
            else:
                self.logger.error(f"Ollama API returned status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timed out after {self.timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"Error generating with image: {e}", exc_info=True)
            return None
    
    def generate_text(
        self,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """Generate text response based on prompt.
        
        Args:
            model: Model name to use
            prompt: User prompt
            system_prompt: System prompt (optional)
            temperature: Generation temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response or None if failed
        """
        try:
            self.logger.debug(f"Generating text using model: {model}")
            
            # Prepare request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            # Make request
            response = requests.post(
                f"{self.host}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                generated_text = result.get('response', '')
                self.logger.debug(f"Successfully generated response ({len(generated_text)} chars)")
                return generated_text
            else:
                self.logger.error(f"Ollama API returned status {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            self.logger.error(f"Request timed out after {self.timeout}s")
            return None
        except Exception as e:
            self.logger.error(f"Error generating text: {e}", exc_info=True)
            return None
    
    def list_models(self) -> Optional[list]:
        """List available models in Ollama.
        
        Returns:
            List of available models or None if failed
        """
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=10)
            if response.status_code == 200:
                result = response.json()
                models = result.get('models', [])
                return models
            else:
                self.logger.error(f"Failed to list models: {response.status_code}")
                return None
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            return None
    
    def check_model_available(self, model_name: str) -> bool:
        """Check if a specific model is available.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if model is available, False otherwise
        """
        models = self.list_models()
        if models is None:
            return False
        
        model_names = [model.get('name', '') for model in models]
        is_available = model_name in model_names
        
        if is_available:
            self.logger.info(f"Model '{model_name}' is available")
        else:
            self.logger.warning(f"Model '{model_name}' is not available")
            self.logger.info(f"Available models: {', '.join(model_names)}")
        
        return is_available
