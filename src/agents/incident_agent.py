# src/agents/incident_agent.py
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta
from src.utils.logger import logger
from src.utils.prompts import get_incident_subcategory_prompt
from src.core.ticket_management import (
    TicketManager, TicketType, Priority, Status,
    User, SupportAgent, Ticket
)
from src.core.subcategory_rules import SubcategoryRules
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
        self.follow_up_manager = FollowUpManager(llm_handler, gmail_sender, ticket_manager)
        self.response_timeout = timedelta(hours=24)  # 24-hour timeout for responses
        self.reminder_interval = timedelta(hours=6)  # Send reminder every 6 hours

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incident email."""
        logger.info("Incident agent processing...")
        
        # Extract user information and description
        extracted_info = self.user_info_extractor.extract_info(state["email_data"])
        user = extracted_info["user"]
        description = extracted_info["description"]
        
        # Get subcategory classification
        subcategories = self._classify_subcategories(state["email_data"])
        
        # Create ticket with initial priority based on subcategory rules
        initial_priority = self._determine_initial_priority(subcategories, state["email_data"])
        ticket = self.ticket_manager.create_ticket(
            user=user,
            ticket_type=TicketType.INCIDENT,
            priority=initial_priority,
            description=description,
            subcategories=subcategories
        )
        
        # Check for missing information and send follow-up if needed
        missing_fields = self.follow_up_manager.check_missing_info(ticket)
        if missing_fields:
            logger.info(f"Missing information for ticket {ticket.ticket_id}: {missing_fields}")
            follow_up_email = self.follow_up_manager.generate_follow_up_email(
                ticket, 
                missing_fields,
                email_thread=[{
                    "subject": state["email_data"]["subject"],
                    "body": state["email_data"]["body"]
                }]
            )
            
            # Send follow-up email in the same thread
            if self.follow_up_manager.send_follow_up_email(
                ticket, 
                follow_up_email,
                thread_id=state["email_data"].get("threadId"),
                message_id=state["email_data"].get("messageId")
            ):
                # Set follow-up timestamp and timeout
                ticket.set_follow_up_sent()
                ticket.set_response_timeout()
                self.ticket_manager._save_ticket(ticket)
                
                logger.info(f"Follow-up email sent for ticket {ticket.ticket_id}")
                return {
                    **state,
                    "status": "incident_escalated_with_follow_up",
                    "subcategories": subcategories,
                    "ticket_id": ticket.ticket_id,
                    "missing_fields": missing_fields,
                    "follow_up_sent_at": ticket.follow_up_sent_at.isoformat() if ticket.follow_up_sent_at else None
                }
            else:
                logger.error(f"Failed to send follow-up email for ticket {ticket.ticket_id}")
        
        # If no follow-up needed or failed to send
        return {
            **state,
            "status": "incident_escalated",
            "subcategories": subcategories,
            "ticket_id": ticket.ticket_id
        }

    def _determine_initial_priority(self, subcategories: List[Dict[str, Any]], email_data: Dict[str, Any]) -> Priority:
        """Determine initial priority based on subcategory rules and email content."""
        if not subcategories:
            return Priority.ELEVEE
            
        highest_confidence = max(subcategories, key=lambda x: x.get("confidence", 0))
        subcategory = highest_confidence.get("subcategory")
        
        # Use LLM to evaluate priority based on email content
        email_content = f"""
Sujet: {email_data.get('subject', '')}
Contenu: {email_data.get('body', '')}
"""
        
        return SubcategoryRules.evaluate_priority(
            subcategory=subcategory,
            answers={},  # Empty answers since we're using LLM
            llm_handler=self.llm_handler,
            email_content=email_content
        )

    def check_timeout(self, ticket: Ticket) -> bool:
        """Check if ticket has timed out waiting for response."""
        return ticket.has_timed_out()

    def send_reminder(self, ticket: Ticket) -> None:
        """Send reminder email for ticket."""
        if ticket.needs_reminder():
            logger.info(f"Sending reminder for ticket {ticket.ticket_id}")
            reminder_email = self.follow_up_manager.generate_reminder_email(ticket)
            self.follow_up_manager.send_follow_up_email(ticket, reminder_email)
            ticket.set_reminder_sent()
            self.ticket_manager.update_ticket(ticket)

    def handle_timeout(self, ticket: Ticket) -> None:
        """Handle ticket timeout by escalating priority."""
        logger.info(f"Ticket {ticket.ticket_id} timed out, escalating priority")
        ticket.priority = Priority.CRITIQUE
        ticket.status = Status.ESCALATED
        ticket.add_note("Ticket escalated due to no response within timeout period")
        self.ticket_manager.update_ticket(ticket)
        
        # Notify supervisor
        notification = self.follow_up_manager.generate_timeout_notification(ticket)
        self.follow_up_manager.send_follow_up_email(ticket, notification)

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
            subcategories = result.get("subcategories", [])
            
            # Normalize subcategory format and case
            for subcat in subcategories:
                if "category" in subcat and "subcategory" not in subcat:
                    subcat["subcategory"] = subcat.pop("category")
                # Ensure consistent case (uppercase)
                if "subcategory" in subcat:
                    subcat["subcategory"] = subcat["subcategory"].upper()
            
            return subcategories
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
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            return {"subcategories": []}
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {str(e)}")
            return {"subcategories": []}