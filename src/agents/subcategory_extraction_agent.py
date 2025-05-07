# src/agents/subcategory_agent.py
import json
from typing import Dict, Any, List
from src.utils.logger import logger
from src.utils.prompts import get_incident_subcategory_prompt
from src.core.ticket_management import TicketManager

class SubcategoryExtractionAgent:
    def __init__(self, llm_handler, ticket_manager: TicketManager = None):
        self.llm_handler = llm_handler
        self.ticket_manager = ticket_manager

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to classify incident subcategories."""
        logger.info("Classifying incident subcategories...")
        
        email_data = state["email_data"]
        user = state.get("user", {})
        description = state.get("description", "")
        
        # Extract thread ID and message ID for persistence tracking
        thread_id = email_data.get("persistent_thread_id")
        if thread_id:
            logger.debug(f"Processing thread_id: {thread_id}")
        else:
            logger.warning("No persistent_thread_id found in email_data")
        
        # If thread, extract message ID and combine all messages for extraction
        if "messages" in email_data:
            message_id = email_data["messages"][0].get("message_id", None)
            thread_text = ""
            for msg in email_data["messages"]:
                from_ = msg.get("from", "Unknown")
                subject = msg.get("subject", "No Subject")
                body = msg.get("body", "")
                thread_text += f"\n--- Message from {from_} ---\nSubject: {subject}\n{body}\n"
            sender = email_data["messages"][0].get("from", "Unknown")
            subject = email_data["messages"][0].get("subject", "No Subject")
            prompt = get_incident_subcategory_prompt(
                sender=sender,
                subject=subject,
                body=thread_text
            )
        else:
            message_id = email_data.get("message_id", None)
            sender = email_data.get("from", "Unknown")
            subject = email_data.get("subject", "No Subject")
            body = email_data.get("body", "")
            prompt = get_incident_subcategory_prompt(
                sender=sender,
                subject=subject,
                body=body
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
            
            # Log the state after processing
            logger.info("State after subcategory_agent:")
            logger.info(f"Subcategories: {subcategories}")
            
            # Create updated state preserving ALL existing fields
            updated_state = {**state, "subcategories": subcategories}
            
            # Create and save temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create temporary ticket with subcategories
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="SUBCATEGORY",
                    user=user,
                    ticket_type="Incident",  # Default type
                    priority="",  # Not determined yet
                    description=description,
                    subcategories=subcategories,
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                
                # Save the temporary ticket to file - will overwrite previous temp file
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved temporary ticket after subcategory extraction: {ticket_path}")
                
                # Add ticket_id to state for tracking
                updated_state["temp_subcategory_ticket_id"] = temp_ticket.ticket_id
            
            return updated_state
            
        except Exception as e:
            logger.error(f"Failed to classify subcategories: {str(e)}")
            output_state = {**state, "subcategories": []}
            
            # Create a fallback temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create fallback temporary ticket
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="SUBCATEGORY_FALLBACK",
                    user=user,
                    ticket_type="Incident",
                    priority="",
                    description=description,
                    subcategories=[],
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved fallback temporary ticket after subcategory extraction: {ticket_path}")
                output_state["temp_subcategory_ticket_id"] = temp_ticket.ticket_id
                
            return output_state

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