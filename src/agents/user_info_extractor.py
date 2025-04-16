# src/agents/user_info_extractor.py
import json
from typing import Dict, Any
from src.utils.logger import logger
from src.utils.prompts import get_user_info_extraction_prompt
from src.core.ticket_management import User

class UserInfoExtractor:
    def __init__(self, llm_handler):
        self.llm_handler = llm_handler

    def extract_info(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract user information from email data."""
        logger.info("Extracting user information from email...")
        
        prompt = get_user_info_extraction_prompt(
            sender=email_data["from"],
            subject=email_data["subject"],
            body=email_data["body"]
        )
        
        try:
            llm_response = self.llm_handler.get_response(prompt)
            result = self._parse_response(llm_response)
            
            # Create User object from extracted information
            user_info = result["user_info"]
            user = User(
                name=user_info["name"],
                email=user_info["email"],
                location=user_info["location"]
            )
            
            return {
                "user": user,
                "description": result["description"]
            }
        except Exception as e:
            logger.error(f"Failed to extract user information: {str(e)}")
            # Fallback to basic information if extraction fails
            return {
                "user": User(
                    name=email_data["from"].split("<")[0].strip(),
                    email=email_data["from"],
                    location=""
                ),
                "description": email_data["body"]
            }

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