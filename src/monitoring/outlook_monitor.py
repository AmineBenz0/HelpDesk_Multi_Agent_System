import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class OutlookMonitor:
    """Monitors Outlook inbox for new emails and processes them."""

    def __init__(self, outlook_service, workflow, poll_interval: Optional[int] = None):
        """Initialize the Outlook monitor.
        
        Args:
            outlook_service: The Microsoft Graph API service instance
            workflow: The workflow to process new messages
            poll_interval: Time in seconds between inbox checks
        """
        logger.info("Initializing OutlookMonitor...")
        self.service = outlook_service
        self.workflow = workflow
        self.poll_interval = poll_interval if poll_interval is not None else int(os.getenv('POLL_INTERVAL_SECONDS', 15))
        self.last_check_time = datetime.utcnow() - timedelta(minutes=5)  # Start by checking last 5 minutes

    def run(self):
        """Start monitoring the inbox for new messages."""
        logger.info("Starting Outlook inbox monitoring...")
        
        while True:
            try:
                # Process any new messages
                self._process_new_messages()
                
                # Update last check time
                self.last_check_time = datetime.utcnow()
                
                # Wait for next poll interval
                time.sleep(self.poll_interval)
                
            except Exception as e:
                logger.error(f"Error in Outlook monitor loop: {str(e)}")
                # Wait a bit before retrying
                time.sleep(5)

    def _process_new_messages(self):
        """Process new unread messages from the inbox."""
        try:
            # Get new messages since last check
            messages = self._fetch_new_messages()
            
            if not messages:
                return
                
            logger.info(f"Found {len(messages)} new messages to process")
            
            for message in messages:
                try:
                    # Extract relevant message data
                    message_data = self._extract_message_data(message)
                    
                    # Process the message through the workflow
                    self.workflow.process_message({"email_data": message_data})
                    
                except Exception as e:
                    logger.error(f"Error processing message {message.get('id')}: {str(e)}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error fetching/processing new messages: {str(e)}")
            raise

    def _fetch_new_messages(self):
        """Fetch new unread messages from Outlook."""
        # Build filter query for unread messages received after last check
        filter_query = (
            f"isRead eq false and "
            f"receivedDateTime gt {self.last_check_time.isoformat()}Z"
        )
        
        return self.service.list_messages(
            filter_query=filter_query,
            top=50  # Limit to 50 messages per batch
        )

    def _extract_message_data(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant data from an Outlook message.
        
        Args:
            message: Raw message object from Microsoft Graph API
            
        Returns:
            dict: Extracted message data in a standardized format
        """
        return {
            'id': message.get('id'),
            'thread_id': message.get('conversationId'),
            'subject': message.get('subject', ''),
            'body': message.get('body', {}).get('content', ''),
            'sender': message.get('from', {}).get('emailAddress', {}).get('address', ''),
            'recipient': message.get('toRecipients', [{}])[0].get('emailAddress', {}).get('address', ''),
            'cc': [r.get('emailAddress', {}).get('address', '') 
                  for r in message.get('ccRecipients', [])],
            'date': message.get('receivedDateTime'),
            'raw_message': message
        } 