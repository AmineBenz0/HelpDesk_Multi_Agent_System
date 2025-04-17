# src/agents/demande_agent.py
import base64
from email.mime.text import MIMEText
from typing import Dict, Any
from src.utils.logger import logger
from config.settings import settings

class DemandeAgent:
    def __init__(self, gmail_sender):
        self.gmail_sender = gmail_sender
    
    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process demande by sending acknowledgment email"""
        logger.info("Processing demande...")
        
        email_data = state["email_data"]
        
        # Create response email
        response_text = self._generate_response(email_data)
        
        # Send email
        try:
            success = self.gmail_sender.send_message(email_data["from"], email_data["subject"], response_text)
            if success:
                logger.info("Demande acknowledgment sent successfully")
                return {**state, "status": "acknowledged"}
            else:
                logger.error("Failed to send demande acknowledgment")
                return {**state, "error": "Failed to send acknowledgment email"}
        except Exception as e:
            logger.error(f"Failed to send demande acknowledgment: {str(e)}")
            return {**state, "error": str(e)}

    def _generate_response(self, email_data: Dict[str, Any]) -> str:
        """Generate acknowledgment email text"""
        return f"""
        
Merci pour votre demande. Nous avons bien reçu votre requête concernant :
    "{email_data['subject']}"
        
Notre équipe d'assistance va l'examiner et vous répondra dans un délai de 24 heures.
Votre demande a été enregistrée sous le numéro de référence : {email_data['message_id']}

    Cordialement,
    L'équipe du support technique
        """