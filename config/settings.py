# config/settings.py
from pathlib import Path
from typing import List, Optional

# Base directories
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
CREDENTIALS_DIR = BASE_DIR / "config" / "credentials"

class Settings:
    DEBUG_MODE: bool = True
    CREDENTIALS_FILE: Path = CREDENTIALS_DIR / "credentials.json"
    TOKEN_FILE: Path = CREDENTIALS_DIR / "token.json"
    API_KEY_FILE: Path = CREDENTIALS_DIR / "groq_api_key.txt"

    # Base directories
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    CREDENTIALS_DIR = BASE_DIR / "config" / "credentials"

    # Gmail Settings
    GMAIL_SCOPES = [
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.labels'
    ]
    AUTHORIZED_EMAILS = ["airzet.game@gmail.com"] # Change this to your authorized emails
    POLL_INTERVAL_SECONDS = 10

    # LLM Settings
    LLM_MODEL_NAME = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE = 0.1
    LLM_MAX_TOKENS = 200
    LLM_MODEL_KWARGS = {
        "top_p": 0.9,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.5,
        "response_format": {"type": "json_object"}
    }

settings = Settings()