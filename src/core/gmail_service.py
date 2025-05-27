# src/core/gmail_service.py
import os
import json
from typing import Any, List, Dict, Optional
from pathlib import Path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from src.utils.logger import logger
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import base64
from src.core.email_service import EmailService

class GmailService(EmailService):
    """Handles Gmail API authentication and service initialization."""
    
    def __init__(self):
        self.token_file = os.getenv('TOKEN_FILE', 'config/credentials/token.json')
        self.credentials_file = os.getenv('CREDENTIALS_FILE', 'config/credentials/credentials.json')
        self.gmail_scopes = [scope.strip() for scope in os.getenv('GMAIL_SCOPES', 'https://www.googleapis.com/auth/gmail.modify,https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.labels').split(',')]
        self.service = self._initialize_service()

    def _initialize_service(self) -> Any:
        """Initialize and return an authorized Gmail API service instance."""
        logger.info("Initializing Gmail service...")
        creds = self._get_credentials()
        return build('gmail', 'v1', credentials=creds)

    def _get_credentials(self) -> Credentials:
        """Obtain valid credentials, refreshing if necessary."""
        if os.path.exists(self.token_file):
            logger.debug(f"Loading credentials from {self.token_file}")
            with open(self.token_file, 'r') as token:
                creds = Credentials.from_authorized_user_info(json.load(token), self.gmail_scopes)
            
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
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_file}")
        
        logger.info("Initiating OAuth flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            self.credentials_file,
            self.gmail_scopes
        )
        creds = flow.run_local_server(port=0)
        self._save_credentials(creds)
        return creds

    def _save_credentials(self, creds: Credentials) -> None:
        """Save credentials to token file."""
        logger.info(f"Saving credentials to {self.token_file}")
        with open(self.token_file, 'w') as token:
            token.write(creds.to_json())

    def send_message(self, to: str, subject: str, body: str, cc: Optional[list] = None, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
        try:
            message = self._create_message(to, subject, body, cc, thread_id, message_id)
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            logger.info(f"Email sent successfully to {to} (Message ID: {sent_message.get('id')}, Thread ID: {sent_message.get('threadId')})")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}", exc_info=True)
            return False

    def _create_message(self, to: str, subject: str, message_text: str, cc: Optional[list] = None, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> dict:
        message = MIMEMultipart()
        message['to'] = to
        if cc:
            message['cc'] = ', '.join(cc)
        if message_id:
            if not subject.startswith('Re:'):
                subject = f"Re: {subject}"
        message['subject'] = subject
        if message_id:
            try:
                original_message = self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='metadata',
                    metadataHeaders=['References', 'Message-ID']
                ).execute()
                references = None
                for header in original_message.get('payload', {}).get('headers', []):
                    if header['name'].lower() == 'references':
                        references = header['value']
                        break
                if references:
                    message['References'] = f"{references} {message_id}"
                else:
                    message['References'] = message_id
                message['In-Reply-To'] = message_id
            except Exception as e:
                logger.error(f"Failed to get original message headers: {str(e)}")
                message['In-Reply-To'] = message_id
                message['References'] = message_id
        msg = MIMEText(message_text, 'plain', 'utf-8')
        message.attach(msg)
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        message_dict = {'raw': raw_message}
        if thread_id:
            message_dict['threadId'] = thread_id
        return message_dict

    def get_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            messages = thread.get('messages', [])
            normalized = []
            for msg in messages:
                headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                normalized.append({
                    'message_id': msg['id'],
                    'thread_id': msg['threadId'],
                    'subject': headers.get('subject', 'No Subject'),
                    'body': self._extract_email_body(msg),
                    'from': headers.get('from', 'Unknown'),
                    'date': headers.get('date', 'Unknown'),
                })
            return normalized
        except Exception as e:
            logger.error(f"Error fetching thread messages: {str(e)}")
            return []

    def _extract_email_body(self, msg: dict) -> str:
        try:
            parts = msg.get('payload', {}).get('parts', [])
            if not parts:
                data = msg.get('payload', {}).get('body', {}).get('data', '')
                return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8') if data else ''
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8') if data else ''
            return ''
        except Exception as e:
            logger.error(f"Failed to extract email body: {str(e)}")
            return ''

    def reply_to_message(self, message_id: str, body: str, html_content: bool = True) -> bool:
        try:
            # For Gmail, reply is just sending a message with In-Reply-To and References headers
            # Find the thread_id for the message
            msg = self.service.users().messages().get(userId='me', id=message_id, format='metadata').execute()
            thread_id = msg.get('threadId')
            headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
            subject = headers.get('subject', 'No Subject')
            sender = headers.get('from', 'Unknown')
            return self.send_message(sender, subject, body, thread_id=thread_id, message_id=message_id)
        except Exception as e:
            logger.error(f"Failed to reply to message: {str(e)}")
            return False