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
            # Sort subcategories by confidence in descending order
            sorted_subcategories = sorted(
                [sc for sc in ticket.subcategories if isinstance(sc, dict) and "confidence" in sc],
                key=lambda x: float(x["confidence"]),
                reverse=True
            )
            
            # Only check confidence difference if we have at least 2 subcategories
            if len(sorted_subcategories) >= 2:
                highest_confidence = float(sorted_subcategories[0]["confidence"])
                second_highest_confidence = float(sorted_subcategories[1]["confidence"])
                confidence_diff = highest_confidence - second_highest_confidence
                
                # Only flag as missing if confidence difference is less than 0.2
                if confidence_diff < 0.2:
                    missing_fields.append("Département")
                    logger.info(f"Confidence difference ({confidence_diff:.2f}) is less than 0.2, requesting clarification")
                else:
                    # Update ticket to keep only the highest confidence subcategory
                    try:
                        from src.core.ticket_management import TicketManager
                        ticket_manager = TicketManager()
                        success = ticket_manager.update_ticket_subcategories(
                            ticket.ticket_id,
                            [sorted_subcategories[0]]  # Keep only the highest confidence subcategory
                        )
                        if success:
                            logger.info(f"Updated ticket {ticket.ticket_id} to keep only highest confidence subcategory (diff: {confidence_diff:.2f})")
                        else:
                            logger.error(f"Failed to update ticket {ticket.ticket_id} subcategories")
                    except Exception as e:
                        logger.error(f"Error updating ticket subcategories: {str(e)}")
        
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
            
            # Format the email body
            email_body = f"""Bonjour {ticket.submitted_by.name},

{result['body']}

Pour votre référence :
- Identifiant du ticket : {ticket.ticket_id}
- Catégories identifiées : {', '.join([sc['category'] for sc in ticket.subcategories if isinstance(sc, dict) and 'category' in sc])}

Cordialement,
L'équipe du support technique"""
            
            return {
                "subject": result["subject"],
                "body": email_body
            }
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