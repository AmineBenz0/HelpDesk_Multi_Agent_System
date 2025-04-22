# src/core/gmail_sender.py
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from src.utils.logger import logger

class GmailSender:
    """Handles Gmail email sending operations."""
    
    def __init__(self, gmail_service):
        """Initialize with a Gmail service instance.
        
        Args:
            gmail_service: The Gmail API service instance from googleapiclient.discovery.build
        """
        logger.debug(f"Initializing GmailSender with service type: {type(gmail_service)}")
        logger.debug(f"Service object: {gmail_service}")
        self.service = gmail_service
        # Debug service attributes
        logger.debug(f"Service attributes: {dir(self.service)}")

    def create_message(self, to: str, subject: str, message_text: str, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> dict:
        """Create a message for an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body text
            thread_id: Optional thread ID to reply to
            message_id: Optional message ID to reply to
            
        Returns:
            dict: A message object ready to be sent
        """
        logger.debug("Creating email message...")
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        
        # Add thread headers if replying
        if thread_id and message_id:
            message['In-Reply-To'] = message_id
            message['References'] = message_id
            logger.debug(f"Setting up reply to message {message_id} in thread {thread_id}")
        
        # Create the body of the message
        msg = MIMEText(message_text, 'plain', 'utf-8')
        message.attach(msg)
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        logger.debug("Message created and encoded successfully")
        return {'raw': raw_message}

    def send_message(self, to: str, subject: str, message_text: str, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
        """Send an email message.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body text
            thread_id: Optional thread ID to reply to
            message_id: Optional message ID to reply to
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            logger.debug("Starting email send process...")
            
            # Create the message
            message = self.create_message(to, subject, message_text, thread_id, message_id)
            logger.debug("Message created successfully")
            
            # Send the message using the Gmail API
            logger.debug("Attempting to send message...")
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent successfully to {to} (Message ID: {sent_message.get('id')})")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            return False 