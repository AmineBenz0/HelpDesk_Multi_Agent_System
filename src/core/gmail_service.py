# src/core/gmail_service.py
import json
from typing import Any
from pathlib import Path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from config.settings import settings
from src.utils.logger import logger

class GmailService:
    """Handles Gmail API authentication and service initialization."""
    
    def __init__(self):
        self.service = self._initialize_service()

    def _initialize_service(self) -> Any:
        """Initialize and return an authorized Gmail API service instance."""
        logger.info("Initializing Gmail service...")
        creds = self._get_credentials()
        return build('gmail', 'v1', credentials=creds)

    def _get_credentials(self) -> Credentials:
        """Obtain valid credentials, refreshing if necessary."""
        if settings.TOKEN_FILE.exists():
            logger.debug(f"Loading credentials from {settings.TOKEN_FILE}")
            with open(settings.TOKEN_FILE, 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), settings.GMAIL_SCOPES)
            
            if creds and creds.valid:
                return creds
            
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials...")
                creds.refresh(Request())
                self._save_credentials(creds)
                return creds
        
        return self._create_new_credentials()

    def _create_new_credentials(self) -> Credentials:
        """Create new credentials via OAuth flow."""
        if not settings.CREDENTIALS_FILE.exists():
            raise FileNotFoundError(f"Credentials file not found at {settings.CREDENTIALS_FILE}")
        
        logger.info("Initiating OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(settings.CREDENTIALS_FILE),
            settings.GMAIL_SCOPES
        )
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        logger.info(f"Saving credentials to {settings.TOKEN_FILE}")
        with open(settings.TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())