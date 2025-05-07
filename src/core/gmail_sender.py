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
        self.service = gmail_service

    def create_message(self, to: str, subject: str, message_text: str, 
                      thread_id: Optional[str] = None, message_id: Optional[str] = None) -> dict:
        """Create a message for an email.
        
        Args:
            to: Recipient email address
            subject: Email subject (should match original thread subject)
            message_text: Email body text
            thread_id: Optional thread ID to reply to
            message_id: Optional message ID to reply to (required for proper threading)
            
        Returns:
            dict: A message object ready to be sent
        """
        logger.debug("Creating email message...")
        
        # Create the email message
        message = MIMEMultipart()
        message['to'] = to
        
        # Handle subject for replies
        if message_id:
            # If replying, add 'Re:' prefix if not already present
            if not subject.startswith('Re:'):
                subject = f"Re: {subject}"
        message['subject'] = subject
        
        # Add thread headers if replying
        if message_id:
            # Get the original message's headers
            try:
                original_message = self.service.users().messages().get(
                    userId='me',
                    id=message_id,
                    format='metadata',
                    metadataHeaders=['References', 'Message-ID']
                ).execute()
                
                # Get the References header from original message
                references = None
                for header in original_message.get('payload', {}).get('headers', []):
                    if header['name'].lower() == 'references':
                        references = header['value']
                        break
                
                # Set up threading headers
                if references:
                    # Add the original message ID to the References chain
                    message['References'] = f"{references} {message_id}"
                else:
                    # If no References header, use the message ID
                    message['References'] = message_id
                
                # Set In-Reply-To to the message we're replying to
                message['In-Reply-To'] = message_id
                
                logger.debug(f"Setting up reply to message {message_id} with References: {message['References']}")
            except Exception as e:
                logger.error(f"Failed to get original message headers: {str(e)}")
                # Fallback to basic threading
                message['In-Reply-To'] = message_id
                message['References'] = message_id
        
        # Create the body of the message
        msg = MIMEText(message_text, 'plain', 'utf-8')
        message.attach(msg)
        
        # Encode the message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        logger.debug("Message created and encoded successfully")
        
        # Include threadId in the message if provided
        message_dict = {'raw': raw_message}
        if thread_id:
            message_dict['threadId'] = thread_id
            
        return message_dict

    def send_message(self, to: str, subject: str, message_text: str, 
                    thread_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
        """Send an email message.
        
        Args:
            to: Recipient email address
            subject: Email subject (should match original thread subject)
            message_text: Email body text
            thread_id: Optional thread ID to reply to
            message_id: Optional message ID to reply to (required for proper threading)
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            logger.debug("Starting email send process...")
            
            # Create the message with threading information
            message = self.create_message(to, subject, message_text, thread_id, message_id)
            logger.debug("Message created successfully")
            
            # Send the message using the Gmail API
            logger.debug("Attempting to send message...")
            sent_message = self.service.users().messages().send(
                userId='me',
                body=message
            ).execute()
            
            logger.info(f"Email sent successfully to {to} "
                       f"(Message ID: {sent_message.get('id')}, "
                       f"Thread ID: {sent_message.get('threadId')})")
            return True
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}", exc_info=True)
            return False