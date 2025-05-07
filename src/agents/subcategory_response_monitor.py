# src/agents/subcategory_response_monitor.py
import json
from typing import Dict, Any
from datetime import datetime
from src.monitoring.gmail_monitor import GmailMonitor
from src.utils.logger import logger
from src.utils.email_utils import ensure_thread_persistence

class SubcategoryResponseMonitor(GmailMonitor):
    """Agent responsible for monitoring user responses to subcategory confirmation."""
    
    def __init__(self, service: Any, poll_interval: int = 10):
        super().__init__(service, None, poll_interval=poll_interval)
        self.thread_id = None
        self.last_checked_message_id = None
        self.should_monitor = True

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to check for user response to subcategory confirmation."""
        logger.info("Checking for subcategory confirmation response...")
        
        # Get email data and thread info
        email_data = state["email_data"]
        thread_id = email_data.get("persistent_thread_id")
        if not thread_id:
            logger.error("No thread ID found in state")
            return {**state, "user_responded": False}
        
        logger.debug(f"Processing thread_id: {thread_id}")
        
        if self.thread_id != thread_id:
            self.thread_id = thread_id
            self.last_checked_message_id = None
            logger.info(f"Updated monitoring thread ID to {thread_id}")
        
        # Fetch the thread and check for new messages
        try:
            thread = self.service.users().threads().get(
                userId='me',
                id=thread_id,
                format='full'
            ).execute()
            messages = thread.get('messages', [])
            if not messages:
                logger.debug(f"No messages found in thread {thread_id}")
                return {**state, "user_responded": False, "last_checked_at": datetime.now().isoformat()}
            latest_msg = messages[-1]
            latest_msg_id = latest_msg['id']
            # If this is the first check, just store the message ID
            if not self.last_checked_message_id:
                self.last_checked_message_id = latest_msg_id
                logger.debug(f"Initial message ID stored: {latest_msg_id}")
                return {**state, "user_responded": False, "last_checked_at": datetime.now().isoformat()}
            # Check if there's a new message
            if latest_msg_id != self.last_checked_message_id:
                logger.info(f"New response found in thread {thread_id}")
                self.last_checked_message_id = latest_msg_id
                # Update messages for persistence
                filtered_messages = []
                for msg in messages:
                    msg_headers = {h['name'].lower(): h['value'] for h in msg['payload']['headers']}
                    sender = msg_headers.get('from', 'Unknown')
                    filtered_messages.append({
                        'message_id': msg['id'],
                        'subject': msg_headers.get('subject', 'No Subject'),
                        'from': sender,
                        'date': msg_headers.get('date', 'Unknown'),
                        'body': self._extract_email_body(msg)
                    })
                updated_email_data = ensure_thread_persistence(state["email_data"], filtered_messages)
                return {
                    **state,
                    "user_responded": True,
                    "last_checked_at": datetime.now().isoformat(),
                    "email_data": updated_email_data
                }
            logger.debug(f"No new responses in thread {thread_id}")
            return {**state, "user_responded": False, "last_checked_at": datetime.now().isoformat()}
        except Exception as e:
            logger.error(f"Error checking for response in thread {thread_id}: {str(e)}")
            return {**state, "user_responded": False, "last_checked_at": datetime.now().isoformat()}
        finally:
            pass

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {"subcategories": []} 