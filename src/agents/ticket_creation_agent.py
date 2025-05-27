from typing import Dict, Any
from datetime import datetime
from pathlib import Path
from src.utils.logger import logger
from src.core.ticket_management import Ticket, TicketManager

class TicketCreationAgent:
    def __init__(self, ticket_manager: TicketManager):
        self.ticket_manager = ticket_manager

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to create a ticket."""
        logger.info("Creating incident ticket...")
        
        user = state["user"]
        description = state["description"]
        subcategories = state["subcategories"]
        final_subcategory = state.get("final_subcategory", "")
        priority = state["priority"]
        affectation_team = state.get("affectation_team", "")
        email_data = state["email_data"]
        ticket_type = state.get("ticket_type", "Incident")
        
        # Log thread ID for persistence tracking
        thread_id = email_data.get("persistent_thread_id")
        if thread_id:
            logger.debug(f"Processing thread_id: {thread_id}")
        else:
            logger.warning("No persistent_thread_id found in email_data")
        
        # If thread, use persistent_thread_id and first message's message_id
        if "messages" in email_data:
            thread_id = email_data.get("persistent_thread_id")
            message_id = email_data["messages"][0].get("message_id", None)
        else:
            thread_id = email_data.get("persistent_thread_id")
            message_id = email_data.get("message_id", None)
        
        # If no final_subcategory but we have subcategories, try to set it
        if not final_subcategory and subcategories:
            # Try to extract from subcategories
            if isinstance(subcategories, list) and subcategories:
                if isinstance(subcategories[0], dict):
                    final_subcategory = subcategories[0].get("subcategory", "")
                elif isinstance(subcategories[0], str):
                    final_subcategory = subcategories[0]
            logger.info(f"Set final_subcategory from subcategories: {final_subcategory}")
            
        # Create the final ticket - will overwrite any existing temporary tickets
        # If we have a temporary priority ticket, finalize it
        # Otherwise create a new ticket
        if "temp_priority_ticket_id" in state:
            try:
                temp_ticket_id = state["temp_priority_ticket_id"]
                logger.info(f"Finalizing temporary ticket {temp_ticket_id}")
                ticket = self.ticket_manager.finalize_temp_ticket(
                    temp_ticket_id,
                    user=user,
                    ticket_type=ticket_type,
                    priority=priority,
                    description=description,
                    subcategories=subcategories,
                    final_subcategory=final_subcategory,
                    affectation_team=affectation_team,
                    thread_id=thread_id,
                    message_id=message_id
                )
                logger.info(f"Finalized temporary ticket to {ticket.ticket_id}")
            except Exception as e:
                logger.error(f"Failed to finalize temporary ticket: {str(e)}")
                logger.info("Creating new ticket instead")
                ticket = self.ticket_manager.create_ticket(
                    user=user,
                    ticket_type=ticket_type,
                    priority=priority,
                    description=description,
                    subcategories=subcategories,
                    final_subcategory=final_subcategory,
                    affectation_team=affectation_team,
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                logger.info(f"Created new ticket {ticket.ticket_id}")
        else:
            ticket = self.ticket_manager.create_ticket(
                user=user,
                ticket_type=ticket_type,
                priority=priority,
                description=description,
                subcategories=subcategories,
                final_subcategory=final_subcategory,
                affectation_team=affectation_team,
                email_data=email_data,
                thread_id=thread_id,
                message_id=message_id
            )
            logger.info(f"Created ticket {ticket.ticket_id}")

        # Save ticket to Elasticsearch only
        ticket.save_to_elasticsearch()
        logger.info(f"Saved ticket {ticket.ticket_id} to Elasticsearch")
        return {
            **state,
            "status": "incident_created",
            "ticket_id": ticket.ticket_id
        } 