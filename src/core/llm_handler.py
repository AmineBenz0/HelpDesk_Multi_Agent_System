# src/core/llm_handler.py
from pathlib import Path
from typing import Any, Dict
from langchain_groq import ChatGroq
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

    def _initialize_client(self) -> ChatGroq:
        """Initialize and return the LLM client."""
        logger.info("Initializing LLM client...")
        return ChatGroq(
            groq_api_key=self.api_key,
            model_name=settings.LLM_MODEL_NAME,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
            model_kwargs=settings.LLM_MODEL_KWARGS
        )

    def get_response(self, prompt: str) -> Any:
        """Get response from LLM for the given prompt."""
        logger.debug(f"Sending prompt to LLM (model: {settings.LLM_MODEL_NAME})")
        try:
            response = self.client.invoke(prompt)
            logger.debug("Received LLM response")
            return response
        except Exception as e:
            logger.error(f"LLM request failed: {str(e)}")
            raise