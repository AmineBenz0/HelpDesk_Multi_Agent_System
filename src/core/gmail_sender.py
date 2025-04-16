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

    def create_message(self, to: str, subject: str, message_text: str) -> dict:
        """Create a message for an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body text
            
        Returns:
            dict: A message object ready to be sent
        """
        logger.debug("Creating email message...")
        message = MIMEMultipart()
        message['to'] = to
        message['subject'] = subject
        
        # Create the body of the message
        msg = MIMEText(message_text, 'plain', 'utf-8')
        message.attach(msg)
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        logger.debug("Message created and encoded successfully")
        return {'raw': raw_message}

    def send_message(self, to: str, subject: str, message_text: str) -> bool:
        """Send an email message.
        
        Args:
            to: Recipient email address
            subject: Email subject
            message_text: Email body text
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            logger.debug("Starting email send process...")
            logger.debug(f"Service object type: {type(self.service)}")
            logger.debug(f"Service object: {self.service}")
            
            # Create the message
            message = self.create_message(to, subject, message_text)
            logger.debug("Message created successfully")
            
            # Debug service chain
            logger.debug("Attempting to access service.users()...")
            users = self.service.users()
            logger.debug(f"Users object type: {type(users)}")
            logger.debug(f"Users object: {users}")
            
            logger.debug("Attempting to access users.messages()...")
            messages = users.messages()
            logger.debug(f"Messages object type: {type(messages)}")
            logger.debug(f"Messages object: {messages}")
            
            # Send the message using the Gmail API
            logger.debug("Attempting to send message...")
            sent_message = messages.send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent successfully to {to} (Message ID: {sent_message.get('id')})")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Service object type at error: {type(self.service)}")
            logger.error(f"Service object at error: {self.service}")
            return False 