from typing import Dict, Any, Optional
from datetime import datetime
from src.utils.logger import logger
from src.utils.email_utils import ensure_thread_persistence
from src.core.email_service import EmailService

class UserResponseMonitor:
    def __init__(self, email_service: EmailService, llm_handler: Any, poll_interval: int = 10):
        self.email_service = email_service
        self.poll_interval = poll_interval
        self.thread_id = None
        self.last_checked_message_id = None
        self.should_monitor = True
        self.llm_handler = llm_handler

    def check_for_response(self) -> bool:
        try:
            messages = self.email_service.get_thread_messages(self.thread_id)
            if not messages:
                logger.debug(f"No messages found in thread {self.thread_id}")
                return False
            latest_msg = messages[-1]
            latest_msg_id = latest_msg['message_id']
            if not self.last_checked_message_id:
                self.last_checked_message_id = latest_msg_id
                logger.debug(f"Initial message ID stored: {latest_msg_id}")
                return False
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
        logger.info("Checking for user response...")
        thread_id = state["email_data"].get("persistent_thread_id")
        if not thread_id:
            logger.error("No thread ID found in state")
            return {**state, "user_responded": False}
        logger.debug(f"Processing thread_id: {thread_id}")
        if self.thread_id != thread_id:
            self.thread_id = thread_id
            self.last_checked_message_id = None
            logger.info(f"Updated monitoring thread ID to {thread_id}")
        has_response = self.check_for_response()
        if has_response:
            try:
                messages = self.email_service.get_thread_messages(thread_id)
                filtered_messages = []
                for msg in messages:
                    filtered_messages.append({
                        'message_id': msg['message_id'],
                        'subject': msg['subject'],
                        'from': msg['from'],
                        'date': msg['date'],
                        'body': msg['body']
                    })
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