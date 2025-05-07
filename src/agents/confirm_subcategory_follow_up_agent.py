# src/agents/confirm_subcategory_follow_up_agent.py
import json
from typing import Dict, Any
from datetime import datetime
from src.utils.logger import logger
from src.utils.prompts import get_subcategory_follow_up_prompt
from src.core.gmail_sender import GmailSender
from src.utils.email_utils import send_follow_up_email

class ConfirmSubcategoryFollowUpAgent:
    """Agent responsible for sending follow-up emails for subcategory confirmation."""
    
    def __init__(self, gmail_sender: GmailSender, llm_handler):
        self.gmail_sender = gmail_sender
        self.llm_handler = llm_handler

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to send follow-up email for subcategory confirmation."""
        logger.info("Sending follow-up email for subcategory confirmation...")
        
        # Get email data and subcategories
        email_data = state["email_data"]
        subcategories = state["subcategories"]
        
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
        prompt = get_subcategory_follow_up_prompt(subcategories)
        llm_response = self.llm_handler.get_response(prompt)
        result = self._parse_response(llm_response)
        
        # Send follow-up email
        success = send_follow_up_email(
            gmail_sender=self.gmail_sender,
            to=sender,
            subject=result["subject"],
            message_text=result["body"],
            thread_id=thread_id,
            message_id=message_id
        )
        
        if not success:
            logger.error("Failed to send subcategory confirmation follow-up email")
            return state
            
        logger.info("Subcategory confirmation follow-up email sent successfully")
        return {
            **state,
            "follow_up_sent_at": datetime.now().isoformat(),
            "status": "waiting_for_subcategory_confirmation"
        }

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {
                "subject": "Confirmation de sous-catégorie requise",
                "body": "Veuillez confirmer la sous-catégorie appropriée pour votre incident."
            } 