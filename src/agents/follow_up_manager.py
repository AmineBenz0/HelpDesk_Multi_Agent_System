# src/agents/follow_up_manager.py
import json
from typing import Dict, Any, List
from src.utils.logger import logger
from src.utils.prompts import get_follow_up_questions_prompt
from src.core.ticket_management import Ticket
from src.core.gmail_sender import GmailSender

class FollowUpManager:
    def __init__(self, llm_handler, gmail_service):
        """Initialize the FollowUpManager.
        
        Args:
            llm_handler: The language model handler for generating follow-up questions
            gmail_service: A Gmail API service resource object (not GmailService class instance)
        """
        self.llm_handler = llm_handler
        # We directly use the GmailSender without wrapping it in another GmailSender
        self.gmail_sender = gmail_service if isinstance(gmail_service, GmailSender) else GmailSender(gmail_service)
        logger.debug(f"FollowUpManager initialized with gmail_sender type: {type(self.gmail_sender)}")

    def check_missing_info(self, ticket: Ticket) -> List[str]:
        """Check for missing information in the ticket."""
        missing_fields = []
        
        # Check for low confidence subcategories
        if ticket.subcategories:
            low_confidence = False
            for subcategory in ticket.subcategories:
                if isinstance(subcategory, dict) and "confidence" in subcategory:
                    if float(subcategory["confidence"]) < 0.8:
                        low_confidence = True
                        break
            
            if low_confidence:
                missing_fields.append("Département")
        
        if not ticket.submitted_by.location:
            missing_fields.append("Localisation")
        if not ticket.description:
            missing_fields.append("Description détaillée du problème")
        
        return missing_fields

    def generate_follow_up_email(self, ticket: Ticket, missing_fields: List[str]) -> Dict[str, str]:
        """Generate a follow-up email for missing information."""
        logger.info(f"Generating follow-up email for ticket {ticket.ticket_id}")
        
        prompt = get_follow_up_questions_prompt(missing_fields)
        
        try:
            llm_response = self.llm_handler.get_response(prompt)
            result = self._parse_response(llm_response)
            
            # Add ticket reference and department information to the email
            subcategories_text = ""
            if ticket.subcategories:
                subcategories_text = "\n".join([
                    f"- {sc['category']} (Confiance: {float(sc['confidence']):.2f})"
                    for sc in ticket.subcategories
                    if isinstance(sc, dict) and "category" in sc and "confidence" in sc
                ])
            
            result["body"] = f"""
                            Bonjour {ticket.submitted_by.name},
                            
                            {result['body']}
                            
                            Pour votre référence :
                            - Identifiant du ticket : {ticket.ticket_id}
                            - Catégories identifiées :
                            {subcategories_text}
                            
                            Cordialement,
                            L'équipe du support technique
                            """
            return result
        except Exception as e:
            logger.error(f"Failed to generate follow-up email: {str(e)}")
            raise

    def send_follow_up_email(self, ticket: Ticket, email_content: Dict[str, str]) -> bool:
        """Send the follow-up email."""
        try:
            logger.debug(f"Sending follow-up email via gmail_sender of type: {type(self.gmail_sender)}")
            return self.gmail_sender.send_message(
                to=ticket.submitted_by.email,
                subject=email_content["subject"],
                message_text=email_content["body"]
            )
        except Exception as e:
            logger.error(f"Failed to send follow-up email: {str(e)}")
            return False

    def _parse_response(self, response: Any) -> Dict[str, str]:
        """Parse and validate the LLM response."""
        logger.debug("Parsing LLM response for follow-up email...")
        
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            
            logger.debug(f"Raw response: {content[:200]}")  # Log first 200 chars
            
            result = json.loads(content)
            
            required_fields = ["subject", "body"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            return result
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from LLM")
            raise
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            raise 