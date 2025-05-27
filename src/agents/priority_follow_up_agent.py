import json
from typing import Dict, Any
from datetime import datetime
from src.utils.logger import logger
from src.core.subcategory_rules import SubcategoryRules
from src.core.gmail_service import GmailService

class PriorityFollowUpAgent:
    """Agent responsible for sending follow-up emails to clarify incident priority."""
    
    def __init__(self, gmail_service: GmailService, llm_handler):
        self.gmail_service = gmail_service
        self.llm_handler = llm_handler

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to send follow-up email for priority clarification."""
        logger.info("Sending follow-up email for priority clarification...")
        
        # Get email data and subcategory
        email_data = state["email_data"]
        subcategories = state.get("subcategories", [])
        
        # Use final_subcategory if available
        final_subcategory = state.get("final_subcategory", "")
        
        # Handle the case where neither final_subcategory nor subcategories are available
        if not final_subcategory:
            if not subcategories:
                logger.error("Priority follow-up requires at least one subcategory or final_subcategory, none found.")
                return state
                
            # If no final_subcategory but subcategories are available, extract it
            final_subcategory = self._extract_single_subcategory(subcategories)
            if not final_subcategory:
                logger.error(f"Failed to extract a valid subcategory from: {subcategories}")
                return state
            
        logger.info(f"Using subcategory '{final_subcategory}' for priority follow-up")
        
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
        rules = SubcategoryRules.get_rules_for_subcategory(final_subcategory)
        if not rules:
            logger.error(f"No rules found for subcategory: {final_subcategory}")
            return state
        
        # Parse rules into critical (P1) and elevated (P2) rules
        p1_rules = [rule for rule in rules if rule.priority_level == "P1"]
        p2_rules = [rule for rule in rules if rule.priority_level == "P2"]
        
        # Extract user name for personalization
        user_name = state.get("user", {}).get("name", "")
        
        # Generate follow-up questions using LLM
        prompt = self._create_follow_up_prompt(final_subcategory, p1_rules, p2_rules, user_name)
        llm_response = self.llm_handler.get_response(prompt)
        result = self._parse_response(llm_response)
        
        # Send follow-up email
        success = self.gmail_service.send_message(
            to=sender,
            subject=result["subject"],
            body=result["body"],
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

    def _create_follow_up_prompt(self, subcategory: str, p1_rules: list, p2_rules: list, user_name: str) -> str:
        """Create a prompt for LLM to generate follow-up questions based on subcategory rules and user name."""
        # Use only the first name if available
        first_name = user_name.split()[0] if user_name else ""
        greeting = f"Bonjour {first_name}," if first_name else "Bonjour," 
        prompt = f"""Tu es un assistant du service d'assistance technique chargé de demander des informations complémentaires aux utilisateurs.\n\nObjectif: Créer un email de suivi pour clarifier la priorité d'un incident lié à la sous-catégorie \"{subcategory}\".\n\nLes règles de priorité sont les suivantes:\n\nRègles CRITIQUES (P1):\n"""
        # Add P1 rules
        for i, rule in enumerate(p1_rules, 1):
            prompt += f"{i}. {rule.description} [Affectation: {rule.affectation}]\n"

        prompt += "\nRègles ÉLEVÉES (P2):\n"
        # Add P2 rules
        for i, rule in enumerate(p2_rules, 1):
            prompt += f"{i}. {rule.description} [Affectation: {rule.affectation}]\n"

        prompt += f"""
Crée un email de suivi poli et professionnel en français pour demander des précisions qui permettront de déterminer si l'incident correspond à une règle CRITIQUE (P1) ou ÉLEVÉE (P2).

IMPORTANT: Commence l'email par '{greeting}' (utilise le prénom si disponible, sinon écris simplement 'Bonjour,').
IMPORTANT: Pose MAXIMUM 3 questions, en sélectionnant uniquement les questions les plus pertinentes et discriminantes pour déterminer la priorité de l'incident dans la sous-catégorie \"{subcategory}\".

L'email doit :
1. Être adressé au destinataire de manière professionnelle
2. Expliquer brièvement que vous avez besoin d'informations supplémentaires pour traiter efficacement l'incident
3. Poser 1 à 3 questions ciblées et précises qui permettront de distinguer efficacement entre les règles P1 et P2
4. Privilégier les questions qui aident à distinguer entre P1 et P2 pour des situations similaires
5. Remercier l'utilisateur pour sa collaboration
6. Inclure une formule de politesse appropriée

Réponds au format JSON suivant :
{{
    "subject": "Sujet de l'email",
    "body": "Corps complet de l'email"
}}
"""
        return prompt

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