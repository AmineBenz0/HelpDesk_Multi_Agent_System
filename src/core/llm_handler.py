# src/core/llm_handler.py
from pathlib import Path
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from config.settings import settings
from src.utils.logger import logger

class LLMHandler:
    """Handles all LLM-related operations."""
    
    def __init__(self):
        self.api_key = self._load_api_key()
        self.client = self._initialize_client()

    def _load_api_key(self) -> str:
        """Load the API key from file."""
        logger.info("Loading LLM API key...")
        
        if not settings.API_KEY_FILE.exists():
            raise FileNotFoundError(f"API key file not found at {settings.API_KEY_FILE}")
        
        with open(settings.API_KEY_FILE, 'r') as file:
            api_key = file.read().strip()
            if not api_key:
                raise ValueError("API key file is empty")
            
        logger.debug("API key loaded successfully")
        return api_key

    def _initialize_client(self) -> ChatOpenAI:
        """Initialize and return the LLM client configured for OpenRouter."""
        logger.info("Initializing LLM client...")
        
        # For OpenRouter, we need to configure base_url and model_kwargs properly
        # But don't use default_headers as it causes issues with some versions
        model_kwargs = settings.LLM_MODEL_KWARGS.copy() if hasattr(settings, 'LLM_MODEL_KWARGS') else {}
        
        # Remove any headers from model_kwargs if they exist
        if "headers" in model_kwargs:
            logger.warning("Removing 'headers' from model_kwargs to avoid compatibility issues")
            del model_kwargs["headers"]
        
        logger.debug(f"Initializing LLM with model: {settings.LLM_MODEL_NAME}")
        logger.debug(f"Using model_kwargs: {model_kwargs}")
        
        # Configure extra parameters for HTTP requests but not as headers
        extra_body = {
            "http_referer": settings.OPENROUTER_HTTP_REFERER,
            "x-title": settings.OPENROUTER_X_TITLE
        }
        
        return ChatOpenAI(
            openai_api_key=self.api_key,
            base_url=settings.OPENROUTER_BASE_URL,
            model_name=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            model_kwargs=model_kwargs,
            extra_body=extra_body
        )

    def get_response(self, prompt: str) -> Any:
        """Get response from LLM for the given prompt."""
        logger.debug(f"Sending prompt to LLM (model: {settings.LLM_MODEL_NAME})")
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