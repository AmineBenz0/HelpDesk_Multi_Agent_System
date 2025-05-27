# src/core/llm_handler.py
import os
import json
from pathlib import Path
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from src.utils.logger import logger

class LLMHandler:
    """Handles all LLM-related operations."""
    
    def __init__(self):
        api_key = os.getenv('OPENROUTER_API_KEY')
        if api_key:
            self.api_key = api_key
        else:
            api_key_file = os.getenv('API_KEY_FILE', 'config/credentials/openrouter_api_key.txt')
            if not os.path.exists(api_key_file):
                raise FileNotFoundError(f"API key file not found at {api_key_file}")
            with open(api_key_file, 'r') as f:
                self.api_key = f.read().strip()
        self.model_name = os.getenv('LLM_MODEL_NAME', 'openai/gpt-4o-mini')
        self.temperature = float(os.getenv('LLM_TEMPERATURE', 0.1))
        self.max_tokens = int(os.getenv('LLM_MAX_TOKENS', 8192))
        self.base_url = os.getenv('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
        self.http_referer = os.getenv('OPENROUTER_HTTP_REFERER', 'https://helpdesk.example.com')
        self.x_title = os.getenv('OPENROUTER_X_TITLE', 'Helpdesk Multi-Agent System')
        # Load model kwargs from environment as JSON
        model_kwargs_env = os.getenv('LLM_MODEL_KWARGS', '{}')
        try:
            self.model_kwargs = json.loads(model_kwargs_env)
        except Exception as e:
            logger.warning(f"Invalid JSON for LLM_MODEL_KWARGS: {e}. Using empty dict.")
            self.model_kwargs = {}
        logger.debug(f"Initializing LLM with model: {self.model_name}")
        self.client = self._initialize_client()

    def _initialize_client(self) -> ChatOpenAI:
        """Initialize and return the LLM client configured for OpenRouter."""
        logger.info("Initializing LLM client...")
        model_kwargs = self.model_kwargs.copy() if isinstance(self.model_kwargs, dict) else {}
        # Remove any headers from model_kwargs if they exist
        if "headers" in model_kwargs:
            logger.warning("Removing 'headers' from model_kwargs to avoid compatibility issues")
            del model_kwargs["headers"]
        logger.debug(f"Initializing LLM with model: {self.model_name}")
        logger.debug(f"Using model_kwargs: {model_kwargs}")
        extra_body = {
            "http_referer": self.http_referer,
            "x-title": self.x_title
        }
        return ChatOpenAI(
            openai_api_key=self.api_key,
            base_url=self.base_url,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            model_kwargs=model_kwargs,
            extra_body=extra_body
        )

    def get_response(self, prompt: str) -> Any:
        """Get response from LLM for the given prompt."""
        logger.debug(f"Sending prompt to LLM (model: {self.model_name})")
        try:
            response = self.client.invoke(prompt)
            
            # Check if response is None or invalid
            if response is None:
                logger.error("Received None response from LLM")
                # Return a default response object with content
                return type('obj', (object,), {
                    'content': '{"error": "LLM returned None response"}'
                })
                
            logger.debug("Received LLM response")
            return response
            
        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Return a default response with error message instead of raising
            return type('obj', (object,), {
                'content': f'{{"error": "LLM request failed: {str(e)}"}}'
            })