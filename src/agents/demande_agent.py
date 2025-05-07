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
        
        # Log thread ID for persistence tracking
        thread_id = email_data.get("persistent_thread_id")
        if thread_id:
            logger.debug(f"Processing thread_id: {thread_id}")
        else:
            logger.warning("No persistent_thread_id found in email_data")
        
        # If thread, use first message for sender/subject, combine all bodies
        if "messages" in email_data:
            sender = email_data["messages"][0].get("from", "Unknown")
            subject = email_data["messages"][0].get("subject", "No Subject")
            message_id = email_data["messages"][0].get("message_id", "")
            body = "\n".join([msg.get("body", "") for msg in email_data["messages"]])
            email_info = {"from": sender, "subject": subject, "message_id": message_id, "body": body}
        else:
            email_info = email_data
        
        # Create response email
        response_text = self._generate_response(email_info)
        
        # Send email
        try:
            success = self.gmail_sender.send_message(email_info["from"], email_info["subject"], response_text)
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
        \nMerci pour votre demande. Nous avons bien reçu votre requête concernant :\n    \"{email_data['subject']}\"\n        \nNotre équipe d'assistance va l'examiner et vous répondra dans un délai de 24 heures.\nVotre demande a été enregistrée sous le numéro de référence : {email_data['message_id']}\n\n    Cordialement,\n    L'équipe du support technique\n        """