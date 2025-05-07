from typing import Dict, Any, Optional
from datetime import datetime
from src.utils.logger import logger
from src.core.gmail_sender import GmailSender

def ensure_thread_persistence(email_data: Dict[str, Any], messages: Optional[list] = None) -> Dict[str, Any]:
    """
    Ensure thread persistence when updating email_data by preserving the persistent_thread_id.
    
    Args:
        email_data: The original email_data dictionary
        messages: Optional new messages to update in the email_data
        
    Returns:
        Updated email_data with persistent_thread_id preserved
    """
    # Create a copy of the original email_data
    updated_email_data = dict(email_data)
    
    # Update messages if provided
    if messages is not None:
        updated_email_data["messages"] = messages
    
    # Ensure persistent_thread_id is preserved
    if "persistent_thread_id" in email_data:
        thread_id = email_data["persistent_thread_id"]
        updated_email_data["persistent_thread_id"] = thread_id
        logger.debug(f"Thread persistence maintained: persistent_thread_id={thread_id}")
    else:
        logger.warning("No persistent_thread_id found in email_data")
    
    return updated_email_data

def send_follow_up_email(
    gmail_sender: GmailSender,
    to: str,
    subject: str,
    message_text: str,
    thread_id: Optional[str] = None,
    message_id: Optional[str] = None
) -> bool:
    """
    Send a follow-up email as a reply to an existing thread.
    
    Args:
        gmail_sender: GmailSender instance
        to: Recipient email address
        subject: Email subject
        message_text: Email body text
        thread_id: Thread ID to reply to
        message_id: Message ID to reply to
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not thread_id or not message_id:
        logger.error("Missing thread_id or message_id for follow-up email")
        return False
        
    # Send follow-up email as a reply
    success = gmail_sender.send_message(
        to=to,
        subject=subject,
        message_text=message_text,
        thread_id=thread_id,
        message_id=message_id
    )
    
    if not success:
        logger.error("Failed to send follow-up email")
        return False
        
    logger.info("Follow-up email sent successfully")
    return True 