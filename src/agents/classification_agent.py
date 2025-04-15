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
        
        # Access email data from the state
        email_data = state["email_data"]
        sender = email_data["from"]  # Direct access since we know it exists
        subject = email_data["subject"]
        body = email_data["body"]
        
        logger.debug(f"From: {sender}, Subject: {subject[:50]}...")
        
        prompt = get_email_classification_prompt(sender, subject, body)
        llm_response = self.llm_handler.get_response(prompt)
        result = self._parse_response(llm_response)
        
        # Update the state with the classification result
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