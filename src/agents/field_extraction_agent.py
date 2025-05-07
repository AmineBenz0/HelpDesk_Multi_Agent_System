# src/agents/user_info_extractor.py
import json
import base64
from typing import Dict, Any
from src.utils.logger import logger
from src.utils.prompts import get_user_info_extraction_prompt
from src.core.ticket_management import TicketManager

class FieldExtractionAgent:
    def __init__(self, llm_handler, gmail_service, ticket_manager: TicketManager = None):
        self.llm_handler = llm_handler
        self.service = gmail_service
        self.ticket_manager = ticket_manager

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to extract user information."""
        logger.info("Extracting user information from email...")
        email_data = state["email_data"]
        
        # Extract and log thread ID for persistence tracking
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
            prompt = get_user_info_extraction_prompt(
                sender=sender,
                subject=subject,
                body=thread_text
            )
        else:
            message_id = email_data.get("message_id", None)
            sender = email_data.get("from", "Unknown")
            subject = email_data.get("subject", "No Subject")
            body = email_data.get("body", "")
            prompt = get_user_info_extraction_prompt(
                sender=sender,
                subject=subject,
                body=body
            )
        try:
            logger.debug(f"Prompt sent to LLM for user info extraction: {prompt}")
            llm_response = self.llm_handler.get_response(prompt)
            result = self._parse_response(llm_response)
            user_info = result["user_info"]
            logger.debug(f"Extracted user_info from LLM: {user_info}")
            user_dict = {
                "name": user_info["name"],
                "email": user_info["email"],
                "location": user_info["location"]
            }
            description = result["description"]
            logger.debug(f"Final user_dict to be set in state: {user_dict}")
            outgoing_state = {**state, "user": user_dict, "description": description}
            
            # Create and save temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create temporary ticket with fields extracted so far
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="FIELDS",
                    user=user_dict,
                    ticket_type="Incident",  # Default type
                    priority="",  # Not determined yet
                    description=description,
                    subcategories=[],  # Not determined yet
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                
                # Save the temporary ticket to file - will overwrite based on thread_id
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved temporary ticket after field extraction: {ticket_path}")
                
                # Add ticket_id to state for tracking
                outgoing_state["temp_ticket_id"] = temp_ticket.ticket_id
            
            return outgoing_state
            
        except Exception as e:
            logger.error(f"Failed to extract user information: {str(e)}")
            # Fallback to basic information if extraction fails
            if "messages" in email_data:
                fallback_from = email_data["messages"][0].get("from", "Unknown")
                fallback_body = email_data["messages"][0].get("body", "")
            else:
                fallback_from = email_data.get("from", "Unknown")
                fallback_body = email_data.get("body", "")
            fallback_user = {
                "name": fallback_from.split("<")[0].strip(),
                "email": fallback_from,
                "location": ""
            }
            logger.debug(f"Fallback user info: {fallback_user}")
            fallback_state = {**state, "user": fallback_user, "description": fallback_body if fallback_body else state.get("description", "")}
            
            # Create a fallback temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create fallback temporary ticket 
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="FIELDS_FALLBACK",
                    user=fallback_user,
                    ticket_type="Incident",
                    priority="",
                    description=fallback_body if fallback_body else state.get("description", ""),
                    subcategories=[],
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved fallback temporary ticket after field extraction: {ticket_path}")
                fallback_state["temp_ticket_id"] = temp_ticket.ticket_id
                
            return fallback_state

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        logger.debug("Parsing LLM response for user information...")
        
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            
            logger.debug(f"Raw response: {content[:200]}")  # Log first 200 chars
            
            result = json.loads(content)
            
            required_fields = ["user_info", "description"]
            for field in required_fields:
                if field not in result:
                    raise ValueError(f"Missing required field: {field}")
            
            user_info_fields = ["name", "email", "location"]
            for field in user_info_fields:
                if field not in result["user_info"]:
                    raise ValueError(f"Missing required user info field: {field}")
            
            return result
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from LLM")
            raise
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            raise 