import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class OutlookSender:
    """Handles Outlook email sending operations."""

    def __init__(self, outlook_service):
        """Initialize with an OutlookService instance."""
        logger.debug(f"Initializing OutlookSender with service type: {type(outlook_service)}")
        self.service = outlook_service

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        html_content: bool = True
    ) -> Dict[str, Any]:
        """Send an email using OutlookService."""
        try:
            success = self.service.send_message(to, subject, body, cc=cc)
            if success:
                logger.info(f"Email sent successfully to {to}")
                return {"status": "success", "message": "Email sent successfully"}
            else:
                logger.error(f"Failed to send email to {to}")
                return {"status": "error", "message": "Failed to send email"}
        except Exception as e:
            error_msg = f"Error sending email to {to}: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg}

    def reply_to_email(
        self,
        message_id: str,
        reply_content: str,
        html_content: bool = True
    ) -> Dict[str, Any]:
        """Reply to an existing email thread using OutlookService."""
        try:
            success = self.service.reply_to_message(message_id, reply_content, html_content=html_content)
            if success:
                logger.info(f"Reply sent successfully to message {message_id}")
                return {"status": "success", "message": "Reply sent successfully"}
            else:
                logger.error(f"Failed to send reply to message {message_id}")
                return {"status": "error", "message": "Failed to send reply"}
        except Exception as e:
            error_msg = f"Error sending reply to message {message_id}: {str(e)}"
            logger.error(error_msg)
            return {"status": "error", "message": error_msg} 