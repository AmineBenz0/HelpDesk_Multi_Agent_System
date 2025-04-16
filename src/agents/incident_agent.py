# src/agents/incident_agent.py
import json
from typing import Dict, Any
from src.utils.logger import logger
from src.utils.prompts import get_incident_subcategory_prompt

class IncidentAgent:
    def __init__(self, llm_handler):
        self.llm_handler = llm_handler

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process an incident email."""
        logger.info("Incident agent processing...")
        
        # Get subcategory classification
        subcategories = self._classify_subcategories(state["email_data"])
        
        return {
            **state,
            "status": "incident_escalated",
            "subcategories": subcategories
        }

    def _classify_subcategories(self, email_data: dict) -> list:
        """Classify the incident into subcategories using LLM."""
        logger.info("Classifying incident subcategories...")
        
        prompt = get_incident_subcategory_prompt(
            sender=email_data["from"],
            subject=email_data["subject"],
            body=email_data["body"]
        )
        
        try:
            llm_response = self.llm_handler.get_response(prompt)
            result = self._parse_response(llm_response)
            return result.get("subcategories", [])
        except Exception as e:
            logger.error(f"Failed to classify subcategories: {str(e)}")
            return []

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        logger.debug("Parsing LLM response for subcategories...")
        
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            
            logger.debug(f"Raw response: {content[:200]}")  # Log first 200 chars
            
            result = json.loads(content)
            
            if "subcategories" not in result:
                raise ValueError("Missing required 'subcategories' field")
            
            return result
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from LLM")
            return {"subcategories": []}
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            return {"subcategories": []}