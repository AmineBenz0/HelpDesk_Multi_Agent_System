# src/monitoring/gmail_monitor.py
import base64
import time
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from googleapiclient.discovery import Resource
from config.settings import settings
from src.utils.logger import logger
from bs4 import BeautifulSoup
from config.settings import settings
import json
import re

class GmailMonitor:
    """Monitors Gmail inbox for new emails and processes them."""
    
    def __init__(self, service: Any, workflow: Any, authorized_emails: Optional[List[str]] = None, poll_interval: int = settings.POLL_INTERVAL_SECONDS):
        logger.info("Initializing GmailMonitor...")
        self.service = service
        self.workflow = workflow
        self.authorized_emails = authorized_emails if authorized_emails else []
        self.poll_interval = poll_interval
        self.processing_flag = False
        self.last_processed_thread = None
        self.should_monitor = True
        
        logger.info(f"Configured to monitor emails from: {authorized_emails or 'Any sender'}")
        logger.info(f"Poll interval: {poll_interval} seconds")
    
    def start_monitoring(self) -> None:
        """Start the email monitoring loop."""
        logger.info("Starting email monitoring...")
        
        try:
            while self.should_monitor:  # Use the control flag
                if not self.processing_flag:
                    self._check_for_new_emails()
                
                self._wait_for_next_check()
                
        except KeyboardInterrupt:
            logger.info("Monitoring stopped by user")
        except Exception as e:
            logger.error(f"Monitoring error: {str(e)}")
            raise
        finally:
            logger.info("Email monitoring stopped")
    
    def stop_monitoring(self) -> None:
        """Stop the email monitoring loop."""
        logger.info("Stopping email monitoring...")
        self.should_monitor = False
    
    def _check_for_new_emails(self) -> None:
        """Check for new emails and process them."""
        logger.info("Checking for new emails...")
        
        thread_data = self._get_latest_thread()
        if not thread_data:
            logger.info("No new emails found")
            return
        
        thread_id = thread_data['persistent_thread_id']
        
        if self.last_processed_thread == thread_id:
            logger.debug(f"Thread {thread_id} already processed, skipping")
            return
        
        logger.debug(f"New thread detected: {thread_id}")
        self._process_thread(thread_data, thread_id)
        # Stop monitoring after processing a new thread
        self.stop_monitoring()
    
    def _get_latest_thread(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest unread thread from Gmail."""
        logger.info("Fetching latest thread...")
        
        try:
            query = self._build_gmail_query()
            
            # Get the latest unread message
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
            
            # Get full thread details
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            
            messages = thread.get('messages', [])
            latest_msg = messages[-1]
            
            # Filter messages not from the specified email
            filtered_messages = []
            for msg in messages:
                msg_headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                sender = msg_headers.get('from', 'Unknown')
                if 'amine.benzaarit0@gmail.com' not in sender:
                    filtered_messages.append({
                        'message_id': msg['id'],
                        'subject': msg_headers.get('subject', 'No Subject'),
                        'from': sender,
                        'date': msg_headers.get('date', 'Unknown'),
                        'body': self._extract_email_body(msg)
                    })
            
            # If more than one message, trim reply content from each message body
            if len(filtered_messages) > 1:
                for msg in filtered_messages:
                    body = msg['body']
                    match = re.search(r"\nOn .+? <.+?> wrote:", body)
                    if match:
                        msg['body'] = body[:match.start()].strip()
                # Remove subject for all but the first message
                for i in range(1, len(filtered_messages)):
                    filtered_messages[i]['subject'] = ''
            
            result = {
                'persistent_thread_id': thread_id,
                'messages': filtered_messages
            }
            logger.debug(f"Setting persistent_thread_id={thread_id} in result")
            logger.debug(f"Retrieved thread for agent input: {json.dumps(result, ensure_ascii=False, indent=2)}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching thread: {str(e)}")
            return None
    
    def _build_gmail_query(self) -> str:
        """Build the Gmail API query string."""
        logger.info("Building Gmail query...")
        
        # Base query for unread inbox messages
        query = "is:inbox is:unread"
        
        # Add specific email filter
        specific_email = settings.AUTHORIZED_EMAILS
        query += f" from:{specific_email}"
        
        logger.info(f"Using query: {query}")
        return query
    
    def _extract_email_body(self, message: Dict[str, Any]) -> str:
        """Extract the body text from an email message."""
        logger.info("Extracting email body...")
        
        try:
            payload = message['payload']
            
            # Check for multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    mime_type = part.get('mimeType', '')
                    body_data = part.get('body', {}).get('data', '')
                    
                    if mime_type == 'text/plain' and body_data:
                        return base64.urlsafe_b64decode(body_data).decode('utf-8')
                    
                    # If no plain text, try HTML
                    if mime_type == 'text/html' and body_data:
                        html_content = base64.urlsafe_b64decode(body_data).decode('utf-8')
                        try:
                            soup = BeautifulSoup(html_content, 'html.parser')
                            return soup.get_text(separator='\n', strip=True)
                        except ImportError:
                            return html_content
                    
                    # Recursively check nested parts
                    if 'parts' in part:
                        nested_body = self._extract_email_body({'payload': part})
                        if nested_body != "No body content found":
                            return nested_body
            
            # For simple messages
            if 'body' in payload and 'data' in payload['body']:
                return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
            
            return "No body content found"
            
        except Exception as e:
            logger.error(f"Error extracting body: {str(e)}")
            return "Error extracting body content"
    
    def _process_thread(self, thread_data: Dict[str, Any], thread_id: str) -> None:
        """Process a thread through the workflow."""
        logger.info(f"Processing thread {thread_id}...")
        self.processing_flag = True
        
        try:
            initial_state = {
                "email_data": thread_data,
                "processed": False,
                "category": "",
                "description": "",
                "status": "",
                "ticket_id": "",
                "missing_fields": [],
                "follow_up_sent_at": "",
                "user_responded": False,
                "last_checked_at": "",
                "user": {},
                "subcategories": [],
                "can_detect_priority": False,
                "priority": ""
            }
            
            # Log that thread_id is set in email_data
            if "persistent_thread_id" in thread_data:
                logger.debug(f"Initial state contains persistent_thread_id: {thread_data['persistent_thread_id']}")
            else:
                logger.warning("persistent_thread_id missing in thread_data for initial state")

            logger.info("Executing workflow...")
            final_state = self.workflow.invoke(initial_state)
            
            logger.info(f"Workflow completed. Final state: {final_state}")
            self.last_processed_thread = thread_id
            
        except KeyError as e:
            logger.error(f"Missing required key in state: {str(e)}")
            logger.error(f"Thread data: {thread_data}")
            logger.error(f"Initial state: {initial_state}")
        except Exception as e:
            logger.error(f"Error processing thread {thread_id}: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Thread data: {thread_data}")
            logger.error(f"Initial state: {initial_state}")
            if hasattr(e, '__traceback__'):
                import traceback
                logger.error(f"Traceback: {''.join(traceback.format_tb(e.__traceback__))}")
        finally:
            self.processing_flag = False
    
    def _wait_for_next_check(self) -> None:
        """Wait for the next polling interval."""
        next_check = datetime.now() + timedelta(seconds=self.poll_interval)
        logger.info(f"Next check at {next_check.strftime('%Y-%m-%d %H:%M:%S')}")
        time.sleep(self.poll_interval)