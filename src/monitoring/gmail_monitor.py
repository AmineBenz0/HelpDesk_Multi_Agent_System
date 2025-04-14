# src/monitoring/gmail_monitor.py
import base64
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from googleapiclient.discovery import Resource
from config.settings import settings
from src.utils.logger import logger

class GmailMonitor:
    """Monitors Gmail inbox for new emails and processes them."""
    
    def __init__(
        self,
        service: Resource,
        workflow,
        authorized_emails: Optional[List[str]] = None,
        poll_interval: int = settings.POLL_INTERVAL_SECONDS
    ):
        self.service = service
        self.workflow = workflow
        self.authorized_emails = authorized_emails or settings.AUTHORIZED_EMAILS
        self.poll_interval = poll_interval
        self.processing_flag = False
        self.last_processed_thread = None
        
        logger.info(f"Initialized monitor for {self.authorized_emails}")
        logger.info(f"Poll interval: {self.poll_interval}s")

    def start_monitoring(self) -> None:
        """Start the email monitoring loop."""
        logger.info("Starting monitoring service...")
        try:
            while True:
                if not self.processing_flag:
                    self._check_for_new_emails()
                self._wait_for_next_check()
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
            raise

    def _check_for_new_emails(self) -> None:
        """Check for new emails and process them."""
        thread_data = self._get_latest_thread()
        if not thread_data:
            logger.debug("No new emails found")
            return
        
        thread_id = thread_data['persistent_thread_id']
        if self.last_processed_thread == thread_id:
            logger.debug(f"Already processed thread {thread_id}")
            return
        
        logger.info(f"Processing new thread: {thread_id}")
        self._process_thread(thread_data, thread_id)

    def _get_latest_thread(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest unread thread from Gmail."""
        try:
            query = "is:inbox is:unread"
            if self.authorized_emails:
                query += f" ({' OR '.join(f'from:{email}' for email in self.authorized_emails)})"
            
            response = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=1,
                includeSpamTrash=False
            ).execute()
            
            if not response.get('messages'):
                return None
            
            message = response['messages'][0]
            thread_id = message['threadId']
            
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='metadata'
            ).execute()
            
            messages = thread.get('messages', [])
            latest_msg = messages[-1]
            headers = {h['name'].lower(): h['value'] for h in latest_msg['payload']['headers']}
            
            return {
                'persistent_thread_id': thread_id,
                'message_id': latest_msg['id'],
                'subject': headers.get('subject', 'No Subject'),
                'from': headers.get('from', 'Unknown'),
                'date': headers.get('date', 'Unknown'),
                'body': self._extract_email_body(latest_msg)
            }
            
        except Exception as e:
            logger.error(f"Error fetching thread: {str(e)}")
            return None

    def _extract_email_body(self, message: Dict[str, Any]) -> str:
        """Extract the body text from an email message."""
        try:
            payload = message['payload']
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] in ['text/plain', 'text/html']:
                        if 'data' in part['body']:
                            return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
        except Exception as e:
            logger.error(f"Error extracting body: {str(e)}")
            return "Error extracting body content"

    def _process_thread(self, thread_data: Dict[str, Any], thread_id: str) -> None:
        """Process a thread through the workflow."""
        self.processing_flag = True
        try:
            initial_state = {
                "email_data": thread_data,
                "classification_result": {},
                "processed": False,
                "category": ""
            }
            final_state = self.workflow.invoke(initial_state)
            self.last_processed_thread = thread_id
        except Exception as e:
            logger.error(f"Error processing thread: {str(e)}")
        finally:
            self.processing_flag = False

    def _wait_for_next_check(self) -> None:
        """Wait for the next polling interval."""
        next_check = datetime.now() + timedelta(seconds=self.poll_interval)
        logger.debug(f"Next check at {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(self.poll_interval)