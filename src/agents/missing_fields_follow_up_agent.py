# src/agents/missing_fields_follow_up_agent.py
import json
from typing import Dict, Any
from datetime import datetime
from src.utils.logger import logger
from src.utils.prompts import get_follow_up_questions_prompt
from src.core.gmail_service import GmailService

class MissingFieldsFollowUpAgent:
    """Agent responsible for sending follow-up emails for missing fields."""
    
    def __init__(self, gmail_service: GmailService, llm_handler):
        self.gmail_service = gmail_service
        self.llm_handler = llm_handler

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to send follow-up email for missing fields."""
        logger.info("Sending follow-up email for missing fields...")
        
        # Get email data and user info
        email_data = state["email_data"]
        user = state["user"]
        
        # Log thread ID for persistence tracking
        thread_id = email_data.get("persistent_thread_id")
        if thread_id:
            logger.debug(f"Processing thread_id: {thread_id}")
        else:
            logger.warning("No persistent_thread_id found in email_data")
        
        # If thread, use first message for thread info
        if "messages" in email_data:
            message_id = email_data["messages"][0].get("message_id", None)
        else:
            message_id = email_data.get("message_id", None)
        
        # Generate follow-up questions using LLM
        prompt = get_follow_up_questions_prompt(missing_fields=["location"])
        llm_response = self.llm_handler.get_response(prompt)
        result = self._parse_response(llm_response)
        
        # Send follow-up email
        success = self.gmail_service.send_message(
            to=user["email"],
            subject=result["subject"],
            body=result["body"],
            thread_id=thread_id,
            message_id=message_id
        )
        
        if not success:
            logger.error("Failed to send missing fields follow-up email")
            return state
            
        logger.info("Missing fields follow-up email sent successfully")
        return {
            **state,
            "follow_up_sent_at": datetime.now().isoformat(),
            "status": "waiting_for_location"
        }

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        logger.debug("Parsing LLM response for follow-up questions...")
        
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