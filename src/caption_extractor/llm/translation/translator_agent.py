"""Translator agent to translate text to English using an LLM (Ollama)."""

import logging
from typing import Dict, Any, Optional
from ..ollama_client import OllamaClient


class TranslatorAgent:
    """Agent that translates text to English."""

    def __init__(self, config: Dict[str, Any], ollama_client: OllamaClient):
        self.config = config
        self.ollama_client = ollama_client
        self.logger = logging.getLogger(__name__)

        ollama_config = config.get('ollama', {})
        agent_conf = ollama_config.get('translator_agent', {})
        models_conf = ollama_config.get('models', {})

        # Translator model may be specified under translator_agent or fall back to text_model
        self.model = agent_conf.get('model') or models_conf.get('text_model')
        self.temperature = agent_conf.get('temperature', 0.0)
        self.max_tokens = agent_conf.get('max_tokens', 1500)
        self.system_prompt = agent_conf.get('system_prompt', '')

        if not self.ollama_client.check_model_available(self.model):
            self.logger.warning(f"Translator model '{self.model}' not available")

    def translate_to_english(self, text: str) -> Optional[Dict[str, Any]]:
        """Translate given text to English. Returns a dict with translated_text, model, processing_time and optional metadata.

        If the text appears already English, the translator may return the original text.
        """
        try:
            if not text:
                return {'translated_text': '', 'note': 'empty input', 'model': self.model, 'processing_time': 0.0}

            prompt = (
                "Translate the following text to fluent, natural English. "
                "If the text is already English, return it unchanged. Return ONLY the translation.\n\n"
                f"Text:\n{text}"
            )

            response_data = self.ollama_client.generate_text(
                model=self.model,
                prompt=prompt,
                system_prompt=self.system_prompt,
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )

            if response_data is None:
                self.logger.error("Translator agent failed to get a response")
                return None

            translated = response_data.get('response', '').strip()
            model = response_data.get('model', self.model)
            processing_time = response_data.get('processing_time', 0.0)
            
            return {
                'translated_text': translated,
                'model': model,
                'processing_time': processing_time
            }

        except Exception as e:
            self.logger.error(f"Error translating text: {e}", exc_info=True)
            return None
