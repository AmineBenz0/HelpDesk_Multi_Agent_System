# src/agents/subcategory_response_monitor.py
import json
from typing import Dict, Any
from datetime import datetime
from src.utils.logger import logger
from src.utils.email_utils import ensure_thread_persistence
from src.core.email_service import EmailService

class SubcategoryResponseMonitor:
    """Agent responsible for monitoring user responses to subcategory confirmation."""
    
    def __init__(self, email_service: EmailService, llm_handler: Any, poll_interval: int = 10):
        self.email_service = email_service
        self.poll_interval = poll_interval
        self.thread_id = None
        self.last_checked_message_id = None
        self.should_monitor = True
        self.llm_handler = llm_handler

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to check for user response to subcategory confirmation."""
        logger.info("Checking for subcategory confirmation response...")
        
        # Get email data and thread info
        email_data = state["email_data"]
        thread_id = email_data.get("persistent_thread_id")
        if not thread_id:
            logger.error("No thread ID found in state")
            return {**state, "user_responded": False}
        
        logger.debug(f"Processing thread_id: {thread_id}")
        
        if self.thread_id != thread_id:
            self.thread_id = thread_id
            self.last_checked_message_id = None
            logger.info(f"Updated monitoring thread ID to {thread_id}")
        
        # Fetch the thread and check for new messages
        messages = self.email_service.get_thread_messages(thread_id)
        if not messages:
            logger.debug(f"No messages found in thread {thread_id}")
            return {**state, "user_responded": False, "last_checked_at": datetime.now().isoformat()}
        latest_msg = messages[-1]
        latest_msg_id = latest_msg['message_id']
        # If this is the first check, just store the message ID
        if not self.last_checked_message_id:
            self.last_checked_message_id = latest_msg_id
            logger.debug(f"Initial message ID stored: {latest_msg_id}")
            return {**state, "user_responded": False, "last_checked_at": datetime.now().isoformat()}
        # Check if there's a new message
        if latest_msg_id != self.last_checked_message_id:
            logger.info(f"New response found in thread {thread_id}")
            self.last_checked_message_id = latest_msg_id
            # Update messages for persistence
            filtered_messages = []
            for msg in messages:
                filtered_messages.append({
                    'message_id': msg['message_id'],
                    'subject': msg['subject'],
                    'from': msg['from'],
                    'date': msg['date'],
                    'body': msg['body']
                })
            updated_email_data = ensure_thread_persistence(state["email_data"], filtered_messages)
            
            # Extract latest response body for analysis
            latest_body = latest_msg['body']
            
            # Analyze the response to determine selected subcategory
            final_subcategory = self._analyze_subcategory_response(latest_body, state.get("subcategories", []))
            logger.info(f"Detected final subcategory from response: {final_subcategory}")
            
            return {
                **state,
                "user_responded": True,
                "last_checked_at": datetime.now().isoformat(),
                "email_data": updated_email_data,
                "final_subcategory": final_subcategory
            }
        logger.debug(f"No new responses in thread {thread_id}")
        return {**state, "user_responded": False, "last_checked_at": datetime.now().isoformat()}

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {str(e)}")
            return {"subcategories": []} 

    def _analyze_subcategory_response(self, response_text: str, subcategories: list) -> str:
        """
        Analyze user response to determine which subcategory they confirmed.
        
        Args:
            response_text: Text of the user's response message
            subcategories: List of available subcategories 
            
        Returns:
            str: The selected subcategory or empty string if can't determine
        """
        logger.debug("Analyzing subcategory response...")
        
        # If no subcategories to compare against, return empty
        if not subcategories:
            return ""
            
        # Prepare prompt for LLM
        subcategory_options = []
        for subcat in subcategories:
            if isinstance(subcat, dict):
                if 'subcategory' in subcat:
                    subcategory_options.append(subcat['subcategory'])
                elif 'category' in subcat:
                    subcategory_options.append(subcat['category'])
            elif isinstance(subcat, str):
                subcategory_options.append(subcat)
                
        prompt = f"""
        Analyse la réponse de l'utilisateur pour déterminer quelle sous-catégorie a été confirmée.
        
        Options de sous-catégories:
        {', '.join(subcategory_options)}
        
        Réponse de l'utilisateur:
        {response_text}
        
        Réponds au format JSON suivant:
        ```json
        {{
            "selected_subcategory": "NOM_DE_LA_SOUSCATEGORIE"
        }}
        ```
        Si aucune sous-catégorie n'est clairement indiquée, utilise la première de la liste comme valeur par défaut.
        """
        
        try:
            # Get LLM response
            llm_response = self.llm_handler.get_response(prompt)
            result = self._parse_response(llm_response)
            selected = result.get("selected_subcategory", "")
            
            # If no selection was made, use the first subcategory as default
            if not selected and subcategory_options:
                selected = subcategory_options[0]
                logger.info(f"No clear selection from response, using first subcategory: {selected}")
                
            return selected
        except Exception as e:
            logger.error(f"Error analyzing subcategory response: {str(e)}")
            # Fallback to the first subcategory if available
            if subcategory_options:
                return subcategory_options[0]
            return "" 