# src/monitoring/gmail_monitor.py
import base64
import time
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from googleapiclient.discovery import Resource
from src.utils.logger import logger
from bs4 import BeautifulSoup
import json
import re
import os

class GmailMonitor:
    """Monitors Gmail inbox for new emails and processes them."""
    
    def __init__(self, gmail_service, workflow, poll_interval: Optional[int] = None):
        """Initialize the Gmail monitor.
        
        Args:
            gmail_service: The Gmail API service instance
            workflow: The workflow to process new messages
            poll_interval: Time in seconds between inbox checks
        """
        logger.info("Initializing GmailMonitor...")
        
        self.service = gmail_service
        self.workflow = workflow
        self.poll_interval = poll_interval if poll_interval is not None else int(os.getenv('POLL_INTERVAL_SECONDS', 15))
        self.running = False
        self.monitoring_thread = None
        self.recently_processed_threads = set()  # Track processed thread IDs in memory
        
    def start_monitoring(self):
        """Start monitoring the inbox for new messages."""
        logger.info("Starting Gmail inbox monitoring...")
        
        self.running = True
        
        while self.running:
            try:
                # Process any new messages
                self._process_new_messages()
                
                # Wait for the next poll interval
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in Gmail monitor loop: {str(e)}")
                # Wait a bit before retrying
                time.sleep(5)
                
    def stop_monitoring(self):
        """Stop the monitoring loop."""
        logger.info("Stopping Gmail inbox monitoring...")
        self.running = False
                
    def _process_new_messages(self):
        """Process new unread messages from the inbox."""
        try:
            # Fetch the latest unread message
            thread = self._fetch_latest_unread_thread()
            
            if not thread:
                logger.debug("No new unread threads found")
                return
            
            thread_id = thread['id']
            # Prevent double-processing in the same session
            if thread_id in self.recently_processed_threads:
                logger.debug(f"Thread {thread_id} already processed in this session, skipping.")
                return
            
            logger.info(f"New unread thread found with ID: {thread_id}")
            
            # Extract the message data
            message_data = self._extract_message_data(thread)
            
            # Mark as processed in this session
            self.recently_processed_threads.add(thread_id)
            
            # Process the message through the workflow
            if self.workflow:
                try:
                    self.workflow.process_message({"email_data": message_data})
                except Exception as e:
                    logger.error(f"Error processing message through workflow: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching/processing new messages: {str(e)}")
            
    def _fetch_latest_unread_thread(self) -> Optional[Dict[str, Any]]:
        """Fetch the latest unread thread from Gmail."""
        try:
            # Build query for unread messages
            query = self._build_gmail_query()
            
            # Search for unread threads
            result = self.service.users().threads().list(
                userId='me',
                q=query,
                maxResults=1
            ).execute()
            
            threads = result.get('threads', [])
            
            if not threads:
                return None
                
            # Get the first thread details
            thread_id = threads[0]['id']
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            
            return thread
            
        except Exception as e:
            logger.error(f"Error fetching latest unread thread: {str(e)}")
            return None
            
    def _extract_message_data(self, thread: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from a thread.
        
        Args:
            thread: The thread object from Gmail API
            
        Returns:
            dict: Extracted thread data with messages in a standardized format
        """
        thread_id = thread['id']
        messages = thread.get('messages', [])
        
        if not messages:
            logger.warning(f"Thread {thread_id} has no messages")
            return {"thread_id": thread_id, "messages": []}
            
        # Extract messages in a standard format
        extracted_messages = []
        for msg in messages:
            # Extract headers
            headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
            
            # Build message dict
            message_dict = {
                'message_id': msg['id'],
                'thread_id': thread_id,
                'subject': headers.get('subject', 'No Subject'),
                'from': headers.get('from', 'Unknown'),
                'to': headers.get('to', 'Unknown'),
                'date': headers.get('date', 'Unknown'),
                'body': self._extract_email_body(msg)
            }
            
            extracted_messages.append(message_dict)
            
        # Mark the thread as read
        try:
            self.service.users().threads().modify(
                userId='me',
                id=thread_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.debug(f"Marked thread {thread_id} as read")
        except Exception as e:
            logger.error(f"Failed to mark thread {thread_id} as read: {str(e)}")
            
        # Return the extracted data
        return {
            'thread_id': thread_id,
            'persistent_thread_id': thread_id,  # For tracking across processing
            'messages': extracted_messages,
            'raw_thread': thread
        }
        
    def _extract_email_body(self, msg: Dict[str, Any]) -> str:
        """Extract the email body text from a message.
        
        Args:
            msg: The message object from Gmail API
            
        Returns:
            str: The extracted body text
        """
        try:
            parts = msg.get('payload', {}).get('parts', [])
            
            # If no parts, try to get body from payload directly
            if not parts:
                data = msg.get('payload', {}).get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8')
                return ''
                
            # Find and decode the text/plain part
            for part in parts:
                if part.get('mimeType') == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8')
                        
            # If no plain text part found, try alternative approaches
            # Check for nested parts
            for part in parts:
                if 'parts' in part:
                    for nested_part in part['parts']:
                        if nested_part.get('mimeType') == 'text/plain':
                            data = nested_part.get('body', {}).get('data', '')
                            if data:
                                return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8')
                                
            # Fallback to any part's body
            for part in parts:
                data = part.get('body', {}).get('data', '')
                if data:
                    return base64.urlsafe_b64decode(data.encode('UTF-8')).decode('utf-8')
                    
            return ''
            
        except Exception as e:
            logger.error(f"Failed to extract email body: {str(e)}")
            return ''
            
    def _build_gmail_query(self) -> str:
        """Build the Gmail API query string."""
        logger.info("Building Gmail query...")
        
        # Start with basic filter for unread messages
        query = "is:unread"
        
        return query