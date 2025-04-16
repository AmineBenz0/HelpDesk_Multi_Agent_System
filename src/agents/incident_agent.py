# src/agents/incident_agent.py
import json
from typing import Dict, Any
from src.utils.logger import logger
from src.utils.prompts import get_incident_subcategory_prompt
from src.core.ticket_management import (
    TicketManager, TicketType, Priority, Status,
    User, SupportAgent, Ticket
)
from src.agents.user_info_extractor import UserInfoExtractor
from src.agents.follow_up_manager import FollowUpManager
from src.core.gmail_sender import GmailSender

class IncidentAgent:
    def __init__(self, llm_handler, ticket_manager: TicketManager, gmail_sender: GmailSender):
        """Initialize the IncidentAgent.
        
        Args:
            llm_handler: The language model handler
            ticket_manager: The ticket management system
            gmail_sender: GmailSender instance for sending emails
        """
        logger.debug(f"Initializing IncidentAgent with gmail_sender type: {type(gmail_sender)}")
        self.llm_handler = llm_handler
        self.ticket_manager = ticket_manager
        self.user_info_extractor = UserInfoExtractor(llm_handler)
        self.follow_up_manager = FollowUpManager(llm_handler, gmail_sender)

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incident email."""
        logger.info("Incident agent processing...")
        
        # Extract user information and description
        extracted_info = self.user_info_extractor.extract_info(state["email_data"])
        user = extracted_info["user"]
        description = extracted_info["description"]
        
        # Get subcategory classification
        subcategories = self._classify_subcategories(state["email_data"])
        
        # Create ticket
        ticket = self.ticket_manager.create_ticket(
            user=user,
            ticket_type=TicketType.INCIDENT,
            priority=None,  # Priority will be determined after follow-up
            description=description,
            subcategories=subcategories
        )
        
        # Check for missing information and send follow-up if needed
        missing_fields = self.follow_up_manager.check_missing_info(ticket)
        if missing_fields:
            logger.info(f"Missing information for ticket {ticket.ticket_id}: {missing_fields}")
            follow_up_email = self.follow_up_manager.generate_follow_up_email(ticket, missing_fields)
            self.follow_up_manager.send_follow_up_email(ticket, follow_up_email)
            return {
                **state,
                "status": "incident_escalated_with_follow_up",
                "subcategories": subcategories,
                "ticket_id": ticket.ticket_id,
                "missing_fields": missing_fields
            }
        
        return {
            **state,
            "status": "incident_escalated",
            "subcategories": subcategories,
            "ticket_id": ticket.ticket_id
        }

    def _classify_subcategories(self, email_data: dict) -> list:
        """Classify the incident into subcategories using LLM."""
        logger.info("Classifying incident subcategories...")
        
        prompt = get_incident_subcategory_prompt(
            sender=email_data["from"],
            subject=email_data["subject"],
            body=email_data["body"]
        )
        
        try:
            llm_response = self.llm_handler.get_response(prompt)
            result = self._parse_response(llm_response)
            return result.get("subcategories", [])
        except Exception as e:
            logger.error(f"Failed to classify subcategories: {str(e)}")
            return []

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        logger.debug("Parsing LLM response for subcategories...")
        
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            
            logger.debug(f"Raw response: {content[:200]}")  # Log first 200 chars
            
            result = json.loads(content)
            
            if "subcategories" not in result:
                raise ValueError("Missing required 'subcategories' field")
            
            return result
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from LLM")
            return {"subcategories": []}
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            return {"subcategories": []}