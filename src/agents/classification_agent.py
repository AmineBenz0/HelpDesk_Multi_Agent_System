# src/core/classification_agent .py
import json
from typing import Dict, Any
from src.utils.logger import logger
from src.utils.prompts import get_email_classification_prompt

class ClassifierAgent:
    """Processes individual emails through classification and handling."""
    
    def __init__(self, llm_handler):
        self.llm_handler = llm_handler

    def classify_email(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Classify an email into predefined categories."""
        logger.info("Classifying email...")
        email_data = state["email_data"]
        
        # Log thread ID for persistence tracking
        thread_id = email_data.get("persistent_thread_id")
        if thread_id:
            logger.debug(f"Processing thread_id: {thread_id}")
        else:
            logger.warning("No persistent_thread_id found in email_data")
        
        # Combine all messages in the thread for classification
        if "messages" in email_data:
            thread_text = ""
            for msg in email_data["messages"]:
                from_ = msg.get("from", "Unknown")
                subject = msg.get("subject", "No Subject")
                body = msg.get("body", "")
                thread_text += f"\n--- Message from {from_} ---\nSubject: {subject}\n{body}\n"
            sender = email_data["messages"][0].get("from", "Unknown")
            subject = email_data["messages"][0].get("subject", "No Subject")
            body = thread_text
        else:
            sender = email_data.get("from", "Unknown")
            subject = email_data.get("subject", "No Subject")
            body = email_data.get("body", "")
        logger.debug(f"From: {sender}, Subject: {subject[:50]}...")
        prompt = get_email_classification_prompt(sender, subject, body)
        llm_response = self.llm_handler.get_response(prompt)
        result = self._parse_response(llm_response)
        return {
            **state,
            "category": result["category"],
        }

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        logger.debug("Parsing LLM response...")
        
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            
            logger.debug(f"Raw response: {content[:200]}")  # Log first 200 chars
            
            result = json.loads(content)
            if "category" not in result:
                raise ValueError("Missing required 'category' field")
            
            return result
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from LLM")
            return {"error": "Invalid JSON response"}
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            return {"error": str(e)}