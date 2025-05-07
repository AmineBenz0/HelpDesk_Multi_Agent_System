from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from src.monitoring.gmail_monitor import GmailMonitor
from src.utils.logger import logger
from src.utils.email_utils import ensure_thread_persistence

class UserResponseMonitor(GmailMonitor):
    """Monitors a specific email thread for user responses."""
    
    def __init__(self, service: Any, thread_id: str, poll_interval: int = 10):
        """Initialize with Gmail service and thread ID to monitor.
        
        Args:
            service: Gmail API service instance
            thread_id: The thread ID to monitor for responses
            poll_interval: How often to check for new messages (in seconds)
        """
        super().__init__(service, None, poll_interval=poll_interval)
        self.thread_id = thread_id
        self.last_checked_message_id = None
        self.should_monitor = True
        
    def check_for_response(self) -> bool:
        """Check if there's a new response in the monitored thread.
        
        Returns:
            bool: True if a new response is found, False otherwise
        """
        try:
            # Get the thread details
            thread = self.service.users().threads().get(
                userId='me',
                id=self.thread_id,
                format='full'
            ).execute()
            
            messages = thread.get('messages', [])
            if not messages:
                logger.debug(f"No messages found in thread {self.thread_id}")
                return False
                
            # Get the latest message
            latest_msg = messages[-1]
            latest_msg_id = latest_msg['id']
            
            # If this is the first check, just store the message ID
            if not self.last_checked_message_id:
                self.last_checked_message_id = latest_msg_id
                logger.debug(f"Initial message ID stored: {latest_msg_id}")
                return False
                
            # Check if there's a new message
            if latest_msg_id != self.last_checked_message_id:
                logger.info(f"New response found in thread {self.thread_id}")
                self.last_checked_message_id = latest_msg_id
                return True
                
            logger.debug(f"No new responses in thread {self.thread_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error checking for response in thread {self.thread_id}: {str(e)}")
            return False
            
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to check for user response.
        
        Args:
            state: Current workflow state
            
        Returns:
            Updated state with response status
        """
        logger.info("Checking for user response...")
        
        # Get thread ID from state
        thread_id = state["email_data"].get("persistent_thread_id")
        if not thread_id:
            logger.error("No thread ID found in state")
            return {**state, "user_responded": False}
        
        logger.debug(f"Processing thread_id: {thread_id}")
            
        # Update the thread ID if needed
        if self.thread_id != thread_id:
            self.thread_id = thread_id
            self.last_checked_message_id = None
            logger.info(f"Updated monitoring thread ID to {thread_id}")
            
        # Check for response
        has_response = self.check_for_response()

        if has_response:
            # Fetch the latest thread and update messages
            try:
                thread = self.service.users().threads().get(
                    userId='me',
                    id=thread_id,
                    format='full'
                ).execute()
                messages = thread.get('messages', [])
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
                # Use utility function to ensure thread persistence
                updated_email_data = ensure_thread_persistence(state["email_data"], filtered_messages)
            except Exception as e:
                logger.error(f"Failed to fetch latest thread after user response: {str(e)}")
                updated_email_data = state["email_data"]
            return {
                **state,
                "user_responded": True,
                "last_checked_at": datetime.now().isoformat(),
                "email_data": updated_email_data
            }
        else:
            return {
                **state,
                "user_responded": False,
                "last_checked_at": datetime.now().isoformat()
            } 