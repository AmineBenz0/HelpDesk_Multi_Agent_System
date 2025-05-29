# src/agents/missing_subcategory_follow_up_agent.py
import json
from typing import Dict, Any
from datetime import datetime
from src.utils.logger import logger
from src.utils.prompts import get_missing_subcategory_follow_up_prompt
from src.core.email_service import EmailService

class MissingSubcategoryFollowUpAgent:
    """Agent responsible for sending follow-up emails for missing subcategory."""
    
    def __init__(self, email_service: EmailService, llm_handler):
        self.email_service = email_service
        self.llm_handler = llm_handler

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to send follow-up email for missing subcategory."""
        logger.info("Sending follow-up email for missing subcategory...")
        
        # Get email data and subcategories
        email_data = state["email_data"]
        subcategories = state.get("subcategories", [])
        
        # Log thread ID for persistence tracking
        thread_id = email_data.get("persistent_thread_id")
        if thread_id:
            logger.debug(f"Processing thread_id: {thread_id}")
        else:
            logger.warning("No persistent_thread_id found in email_data")
        
        # If thread, use first message for sender/thread info
        if "messages" in email_data:
            sender = email_data["messages"][0].get("from", "Unknown")
            message_id = email_data["messages"][0].get("message_id", None)
        else:
            sender = email_data.get("from", "Unknown")
            message_id = email_data.get("message_id", None)
        
        # Generate follow-up questions using LLM
        prompt = get_missing_subcategory_follow_up_prompt(subcategories)
        llm_response = self.llm_handler.get_response(prompt)
        result = self._parse_response(llm_response)
        
        # Send follow-up email
        success = self.email_service.send_message(
            to=sender,
            subject=result["subject"],
            body=result["body"],
            thread_id=thread_id,
            message_id=message_id
        )
        
        if not success:
            logger.error("Failed to send missing subcategory follow-up email")
            return state
            
        logger.info("Missing subcategory follow-up email sent successfully")
        return {
            **state,
            "follow_up_sent_at": datetime.now().isoformat(),
            "status": "waiting_for_missing_subcategory"
        }

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {"subject": "Précision requise", "body": "Veuillez préciser la sous-catégorie appropriée."} 