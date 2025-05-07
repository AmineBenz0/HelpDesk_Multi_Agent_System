import json
from typing import Dict, Any
from datetime import datetime
from src.utils.logger import logger
from src.utils.prompts import get_priority_follow_up_prompt
from src.core.gmail_sender import GmailSender
from src.core.subcategory_rules import SubcategoryRules
from src.utils.email_utils import send_follow_up_email

class PriorityFollowUpAgent:
    """Agent responsible for sending follow-up emails to clarify incident priority."""
    
    def __init__(self, gmail_sender: GmailSender, llm_handler):
        self.gmail_sender = gmail_sender
        self.llm_handler = llm_handler

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to send follow-up email for priority clarification."""
        logger.info("Sending follow-up email for priority clarification...")
        
        # Get email data and subcategory
        email_data = state["email_data"]
        subcategories = state.get("subcategories", [])
        
        # Handle empty subcategories case
        if not subcategories:
            logger.error("Priority follow-up requires at least one subcategory, none found.")
            return state
            
        # Extract a single subcategory from the list
        subcategory = self._extract_single_subcategory(subcategories)
        if not subcategory:
            logger.error(f"Failed to extract a valid subcategory from: {subcategories}")
            return state
            
        logger.info(f"Using subcategory '{subcategory}' for priority follow-up")
        
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
        
        # Get rules for the subcategory
        rules = SubcategoryRules.get_rules_for_subcategory(subcategory)
        if not rules:
            logger.error(f"No rules found for subcategory: {subcategory}")
            return state
        
        # Generate follow-up questions using LLM
        prompt = get_priority_follow_up_prompt(subcategory, rules)
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
            logger.error("Failed to send priority follow-up email")
            return state
            
        logger.info("Priority follow-up email sent successfully")
        return {
            **state,
            "follow_up_sent_at": datetime.now().isoformat(),
            "status": "waiting_for_priority_clarification"
        }
        
    def _extract_single_subcategory(self, subcategories):
        """
        Extract a single subcategory string from subcategories in various formats.
        
        Args:
            subcategories: Can be string, list, dict, or list of dicts
            
        Returns:
            A single subcategory string, or None if extraction fails
        """
        try:
            logger.debug(f"Extracting single subcategory from: {subcategories}")
            
            # Case 1: subcategories is a single string
            if isinstance(subcategories, str):
                return subcategories
                
            # Case 2: subcategories is a list
            if isinstance(subcategories, list):
                if not subcategories:
                    return None
                    
                # Get first item
                first_item = subcategories[0]
                
                # Case 2.1: first item is a string
                if isinstance(first_item, str):
                    return first_item
                    
                # Case 2.2: first item is a dict with 'subcategory' key
                if isinstance(first_item, dict) and 'subcategory' in first_item:
                    return first_item['subcategory']
                    
                # Case 2.3: first item is a dict without 'subcategory' key
                if isinstance(first_item, dict):
                    # Try to get first value as fallback
                    values = list(first_item.values())
                    if values:
                        # If value is a string, use it
                        if isinstance(values[0], str):
                            return values[0]
                        # Otherwise convert to string
                        return str(values[0])
                    
                # Case 2.4: try to convert first item to string    
                return str(first_item)
                
            # Case 3: subcategories is a dictionary
            if isinstance(subcategories, dict):
                # Case 3.1: dictionary has 'subcategory' key
                if 'subcategory' in subcategories:
                    return subcategories['subcategory']
                    
                # Case 3.2: try to get the first value
                values = list(subcategories.values())
                if values:
                    if isinstance(values[0], str):
                        return values[0]
                    return str(values[0])
                    
                # Case 3.3: try to get the first key
                keys = list(subcategories.keys())
                if keys:
                    return str(keys[0])
                    
            # Fallback: couldn't extract a subcategory
            return None
            
        except Exception as e:
            logger.error(f"Error extracting subcategory: {str(e)}")
            return None

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {
                "subject": "Précision de priorité requise",
                "body": "Veuillez répondre aux questions pour nous aider à déterminer la priorité de votre incident."
            } 