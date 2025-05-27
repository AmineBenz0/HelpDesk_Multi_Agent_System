import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class OutlookSender:
    """Handles Outlook email sending operations."""

    def __init__(self, outlook_service):
        """Initialize with a Microsoft Graph API service instance.
        
        Args:
            outlook_service: The Microsoft Graph API service instance
        """
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
        """Send an email using Microsoft Graph API.
        
        Args:
            to: Email address of the recipient
            subject: Subject of the email
            body: Body content of the email
            cc: List of CC recipients
            html_content: Whether the body contains HTML content
            
        Returns:
            dict: Response from the API
        """
        try:
            # Prepare the message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML" if html_content else "Text",
                        "content": body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to
                            }
                        }
                    ]
                }
            }

            # Add CC recipients if provided
            if cc:
                message["message"]["ccRecipients"] = [
                    {
                        "emailAddress": {
                            "address": email
                        }
                    } for email in cc
                ]

            # Send the message using Microsoft Graph API
            endpoint = "/me/sendMail"
            response = self.service.post(endpoint, json=message)
            response.raise_for_status()

            logger.info(f"Email sent successfully to {to}")
            return {"status": "success", "message": "Email sent successfully"}

        except Exception as e:
            error_msg = f"Error sending email to {to}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg)

    def reply_to_email(
        self,
        message_id: str,
        reply_content: str,
        html_content: bool = True
    ) -> Dict[str, Any]:
        """Reply to an existing email thread.
        
        Args:
            message_id: ID of the message to reply to
            reply_content: Content of the reply
            html_content: Whether the reply content contains HTML
            
        Returns:
            dict: Response from the API
        """
        try:
            # Prepare the reply
            reply = {
                "message": {
                    "body": {
                        "contentType": "HTML" if html_content else "Text",
                        "content": reply_content
                    }
                }
            }

            # Send the reply using Microsoft Graph API
            endpoint = f"/me/messages/{message_id}/reply"
            response = self.service.post(endpoint, json=reply)
            response.raise_for_status()

            logger.info(f"Reply sent successfully to message {message_id}")
            return {"status": "success", "message": "Reply sent successfully"}

        except Exception as e:
            error_msg = f"Error sending reply to message {message_id}: {str(e)}"
            logger.error(error_msg)
            raise Exception(error_msg) 