# src/agents/follow_up_manager.py
import json
from typing import Dict, Any, List, Optional
from src.utils.logger import logger
from src.utils.prompts import get_follow_up_questions_prompt
from src.core.ticket_management import Ticket, Priority, Status
from src.core.gmail_sender import GmailSender
from src.core.subcategory_rules import SubcategoryRules
from src.core.ticket_management import TicketManager

class FollowUpManager:
    def __init__(self, llm_handler, gmail_sender: GmailSender, ticket_manager: TicketManager):
        """Initialize the FollowUpManager.
        
        Args:
            llm_handler: The language model handler
            gmail_sender: GmailSender instance for sending emails
            ticket_manager: TicketManager instance for managing tickets
        """
        self.llm_handler = llm_handler
        self.gmail_sender = gmail_sender
        self.ticket_manager = ticket_manager

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
                        success = self.ticket_manager.update_ticket_subcategories(
                            ticket.ticket_id,
                            [sorted_subcategories[0]]  # Keep only the highest confidence subcategory
                        )
                        if success:
                            logger.info(f"Updated ticket {ticket.ticket_id} to keep only highest confidence subcategory (diff: {confidence_diff:.2f})")
                        else:
                            logger.error(f"Failed to update ticket {ticket.ticket_id} subcategories")
                    except Exception as e:
                        logger.error(f"Error updating ticket subcategories: {str(e)}")
            
            # For incidents, check subcategory rules
            if ticket.ticket_type == "Incident":
                current_subcategory = max(ticket.subcategories, key=lambda x: x.get("confidence", 0))
                subcategory_name = current_subcategory.get("subcategory")
                
                # Get rules for this subcategory
                rules = SubcategoryRules.get_rules_for_subcategory(subcategory_name)
                if rules:
                    # Add specific questions based on rules
                    for rule in rules:
                        missing_fields.append(rule.description)
                    logger.info(f"Added {len(rules)} specific questions for subcategory {subcategory_name}")
                else:
                    logger.warning(f"No rules found for subcategory {subcategory_name}")
        
        if not ticket.submitted_by.location:
            missing_fields.append("Localisation")
        if not ticket.description:
            missing_fields.append("Description détaillée du problème")
        
        return missing_fields

    def generate_follow_up_email(self, ticket: Ticket, missing_fields: List[str], email_thread: List[Dict[str, str]] = None) -> str:
        """Generate a follow-up email with specific questions based on subcategory rules."""
        logger.info(f"Generating follow-up email for ticket {ticket.ticket_id}")
        
        # Get the current subcategory with highest confidence
        current_subcategory = max(ticket.subcategories, key=lambda x: x.get("confidence", 0))
        subcategory_name = current_subcategory.get("subcategory")
        
        # Get prompt for the subcategory
        prompt = SubcategoryRules.get_prompt_for_subcategory(subcategory_name, email_thread)
        if not prompt:
            logger.warning(f"No specific rules found for subcategory {subcategory_name}, using general questions")
            return self._generate_general_follow_up(ticket, missing_fields)
        
        try:
            # Get questions from LLM
            response = self.llm_handler.get_response(prompt)
            questions_data = self._parse_llm_response(response)
            
            # Generate email body
            email_body = f"""Bonjour,

Nous avons reçu votre ticket concernant un incident dans la catégorie {subcategory_name}.
Pour mieux traiter votre demande, nous avons besoin des informations suivantes :

"""
            
            for question in questions_data.get("questions", []):
                email_body += f"- {question['question']}\n"
            
            email_body += f"""
Ticket ID: {ticket.ticket_id}
Priorité actuelle: {ticket.priority.value}

Merci de nous fournir ces informations pour que nous puissions traiter votre demande efficacement.

Cordialement,
Service d'assistance
"""
            return email_body
            
        except Exception as e:
            logger.error(f"Failed to generate subcategory-specific questions: {str(e)}")
            return self._generate_general_follow_up(ticket, missing_fields)

    def generate_reminder_email(self, ticket: Ticket) -> str:
        """Generate a reminder email for the ticket."""
        logger.info(f"Generating reminder email for ticket {ticket.ticket_id}")
        
        return f"""Bonjour,

Nous n'avons pas encore reçu de réponse concernant votre ticket {ticket.ticket_id}.
Pour nous permettre de vous aider au mieux, merci de bien vouloir répondre à nos questions précédentes.

Priorité actuelle: {ticket.priority.value}

Cordialement,
Service d'assistance
"""

    def generate_timeout_notification(self, ticket: Ticket) -> str:
        """Generate a notification email for ticket timeout."""
        logger.info(f"Generating timeout notification for ticket {ticket.ticket_id}")
        
        return f"""URGENT: Ticket {ticket.ticket_id} - Pas de réponse utilisateur

Le ticket suivant n'a pas reçu de réponse de l'utilisateur dans le délai imparti :

Ticket ID: {ticket.ticket_id}
Catégorie: {ticket.subcategories[0]['subcategory']}
Priorité: {ticket.priority.value}
Statut: {ticket.status.value}

Action requise: Veuillez prendre les mesures nécessaires pour résoudre ce ticket.

Cordialement,
Système de gestion des tickets
"""

    def send_follow_up_email(self, ticket: Ticket, email_body: str, thread_id: Optional[str] = None, message_id: Optional[str] = None) -> bool:
        """Send a follow-up email to the user.
        
        Args:
            ticket: The ticket object
            email_body: The email body content
            thread_id: Optional thread ID to reply to
            message_id: Optional message ID to reply to
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            subject = f"Follow-up: Ticket {ticket.ticket_id} - Additional Information Required"
            success = self.gmail_sender.send_message(
                to=ticket.submitted_by.email,
                subject=subject,
                message_text=email_body,
                thread_id=thread_id,
                message_id=message_id
            )
            
            if success:
                logger.info(f"Follow-up email sent successfully for ticket {ticket.ticket_id}")
                return True
            else:
                logger.error(f"Failed to send follow-up email for ticket {ticket.ticket_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send follow-up email: {str(e)}")
            return False

    def process_user_response(self, ticket: Ticket, answers: Dict[str, str]) -> None:
        """Process user's answers to follow-up questions."""
        logger.info(f"Processing user response for ticket {ticket.ticket_id}")
        
        # Get the current subcategory with highest confidence
        current_subcategory = max(ticket.subcategories, key=lambda x: x.get("confidence", 0))
        subcategory_name = current_subcategory.get("subcategory")
        
        # Evaluate priority based on answers
        new_priority = SubcategoryRules.evaluate_priority(subcategory_name, answers)
        
        # Update ticket priority if changed
        if new_priority != ticket.priority:
            ticket.priority = new_priority
            logger.info(f"Updated priority for ticket {ticket.ticket_id} to {new_priority.value}")
        
        # Assign team based on subcategory
        team = SubcategoryRules.get_team_for_subcategory(subcategory_name)
        if team:
            ticket.assigned_team = team
            logger.info(f"Assigned team {team} to ticket {ticket.ticket_id}")

    def _generate_general_follow_up(self, ticket: Ticket, missing_fields: List[str]) -> str:
        """Generate a general follow-up email when no specific rules are found."""
        email_body = f"""Bonjour,

Nous avons reçu votre ticket et avons besoin d'informations supplémentaires pour le traiter :

"""
        
        for field in missing_fields:
            email_body += f"- {field}\n"
        
        email_body += f"""
Ticket ID: {ticket.ticket_id}
Priorité actuelle: {ticket.priority.value}

Merci de nous fournir ces informations pour que nous puissions traiter votre demande efficacement.

Cordialement,
Service d'assistance
"""
        return email_body

    def _parse_llm_response(self, response: Any) -> Dict[str, Any]:
        """Parse the LLM response for questions, attempting to extract the JSON block."""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.strip()
            
            # Find the first '{' and the last '}' to extract the JSON block
            start_index = content.find('{')
            end_index = content.rfind('}')
            
            if start_index != -1 and end_index != -1 and end_index > start_index:
                json_content = content[start_index : end_index + 1]
                logger.debug(f"Extracted JSON content: {json_content[:200]}")
                return json.loads(json_content)
            else:
                logger.error(f"Could not find valid JSON block in response: {content[:200]}")
                # Fallback: Try parsing the whole cleaned content as before
                cleaned_content = content.replace('```json', '').replace('```', '').strip()
                return json.loads(cleaned_content)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)} - Content: {content[:200]}")
            return {"questions": []}
        except Exception as e:
            logger.error(f"Unexpected error parsing LLM response: {str(e)}")
            return {"questions": []} 