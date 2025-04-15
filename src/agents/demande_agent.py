# src/agents/demande_agent.py
import base64
from email.mime.text import MIMEText
from typing import Dict, Any
from src.utils.logger import logger
from config.settings import settings

class DemandeAgent:
    def __init__(self, gmail_service):
        self.gmail_service = gmail_service
    
    def process(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process demande by sending acknowledgment email"""
        logger.info("Processing demande...")
        
        # Create response email
        response_text = self._generate_response(email_data)
        message = self._create_message(
            to=email_data["from"],
            subject=f"Re: {email_data['subject']}",
            message_text=response_text
        )
        
        # Send email
        try:
            sent_message = self.gmail_service.users().messages().send(
                userId="me",
                body={"raw": message}
            ).execute()
            logger.info(f"Demande acknowledgment sent: {sent_message['id']}")
            return {"status": "acknowledged", "message_id": sent_message["id"]}
        except Exception as e:
            logger.error(f"Failed to send demande acknowledgment: {str(e)}")
            return {"error": str(e)}

    def _generate_response(self, email_data: Dict[str, Any]) -> str:
        """Generate acknowledgment email text"""
        return f"""
        Cher/Chère {email_data['from'].split('@')[0]},
        
        Merci pour votre demande. Nous avons bien reçu votre requête concernant :
        "{email_data['subject']}"
        
        Notre équipe d'assistance va l'examiner et vous répondra dans un délai de 24 heures.
        Votre demande a été enregistrée sous le numéro de référence : {email_data['message_id']}
        
        Cordialement,
        L’équipe du support technique
        """

    def _create_message(self, to: str, subject: str, message_text: str) -> str:
        """Create MIME message for Gmail API"""
        message = MIMEText(message_text)
        message["to"] = to
        message["from"] = settings.HELPDESK_EMAIL
        message["subject"] = subject
        return base64.urlsafe_b64encode(message.as_bytes()).decode()