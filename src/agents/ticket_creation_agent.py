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
            
        # Helper function to delete temporary ticket file if it exists
        def delete_temp_file():
            if not thread_id:
                return
                
            # Get current date for constructing file path
            date = datetime.now()
            year = str(date.year)
            month = f"{date.month:02d}"
            day = f"{date.day:02d}"
            
            # Construct path to potential temporary file
            base_dir = "tickets"
            temp_filename = f"{thread_id}_TEMP.json"
            temp_file_path = Path(base_dir) / year / month / day / temp_filename
            
            # Delete temporary file if it exists
            if temp_file_path.exists():
                try:
                    logger.info(f"Deleting temporary ticket file: {temp_file_path}")
                    temp_file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete temporary ticket file {temp_file_path}: {str(e)}")
        
        # Create the final ticket - will overwrite any existing temporary tickets
        # If we have a temporary priority ticket, finalize it
        # Otherwise create a new ticket
        if "temp_priority_ticket_id" in state:
            try:
                # Try to finalize the temporary priority ticket
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
                # If finalizing fails, create a new ticket
                logger.error(f"Failed to finalize temporary ticket: {str(e)}")
                logger.info("Creating new ticket instead")
                
                # Delete any existing temporary file
                delete_temp_file()
                
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
            # Create a new ticket from scratch
            
            # Delete any existing temporary file
            delete_temp_file()
            
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

        # Save ticket - this will overwrite any previous files with the same thread_id
        ticket_path = ticket.save_to_file()
        logger.info(f"Saved ticket {ticket.ticket_id} to {ticket_path}")
        
        return {
            **state,
            "status": "incident_created",
            "ticket_id": ticket.ticket_id
        } 