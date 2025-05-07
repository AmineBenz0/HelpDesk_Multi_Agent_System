# src/agents/priority_detection_agent.py
import json
from typing import Dict, Any, List
from src.utils.logger import logger
from src.core.subcategory_rules import SubcategoryRules
from src.core.ticket_management import TicketManager

class PriorityDetectionAgent:
    def __init__(self, llm_handler, ticket_manager: TicketManager = None):
        self.llm_handler = llm_handler
        self.ticket_manager = ticket_manager

    def process(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Process the state to detect incident priority."""
        logger.info("Detecting incident priority...")
        
        email_data = state["email_data"]
        subcategories = state.get("subcategories", [])
        user = state.get("user", {})
        description = state.get("description", "")
        
        # Extract thread ID and message ID for persistence tracking
        thread_id = email_data.get("persistent_thread_id")
        if thread_id:
            logger.debug(f"Processing thread_id: {thread_id}")
        else:
            logger.warning("No persistent_thread_id found in email_data")
            
        # Extract message ID based on email format
        if "messages" in email_data:
            message_id = email_data["messages"][0].get("message_id", None)
        else:
            message_id = email_data.get("message_id", None)
        
        # If no subcategories, can't determine priority
        if not subcategories:
            logger.warning("No subcategories found, can't determine priority")
            output_state = {
                **state,
                "priority": "",
                "reason": "Aucune sous-catégorie trouvée",
            }
            
            # Create a fallback temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create fallback temporary ticket
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="PRIORITY_FALLBACK",
                    user=user,
                    ticket_type="Incident",
                    priority="",
                    description=description,
                    subcategories=subcategories,
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved fallback temporary ticket after priority detection: {ticket_path}")
                output_state["temp_priority_ticket_id"] = temp_ticket.ticket_id
                
            return output_state
        
        # Extract the subcategory string
        # Handle both string and list/dict cases
        subcategory = None
        logger.debug(f"Attempting to extract subcategory from: {subcategories}")
        
        if isinstance(subcategories, str):
            subcategory = subcategories
            logger.debug(f"Extracted subcategory from string: {subcategory}")
        elif isinstance(subcategories, list) and subcategories:
            first_item = subcategories[0]
            if isinstance(first_item, str):
                subcategory = first_item
            elif isinstance(first_item, dict) and 'subcategory' in first_item:
                subcategory = first_item['subcategory']
            # Log the extraction for debugging
            logger.debug(f"Extracted subcategory '{subcategory}' from list item: {first_item}")
        elif isinstance(subcategories, dict) and subcategories:
            # Try to get the subcategory value if it exists
            if 'subcategory' in subcategories:
                subcategory = subcategories['subcategory']
            # Or try first key as fallback
            else:
                try:
                    subcategory = next(iter(subcategories))
                except:
                    subcategory = None
            # Log the extraction for debugging
            logger.debug(f"Extracted subcategory '{subcategory}' from dictionary: {subcategories}")
        if not subcategory:
            logger.warning(f"Could not extract a valid subcategory from: {subcategories}")
            output_state = {**state, "priority": "", "reason": "Impossible d'extraire une sous-catégorie valide"}
            
            # Create a fallback temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create fallback temporary ticket
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="PRIORITY_FALLBACK",
                    user=user,
                    ticket_type="Incident",
                    priority="",
                    description=description,
                    subcategories=subcategories,
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved fallback temporary ticket after priority detection: {ticket_path}")
                output_state["temp_priority_ticket_id"] = temp_ticket.ticket_id
                
            return output_state
            
        # Get rules for the subcategory
        rules = SubcategoryRules.get_rules_for_subcategory(subcategory)
        if not rules:
            logger.warning(f"No rules found for subcategory: {subcategory}")
            output_state = {**state, "priority": "", "reason": f"Aucune règle trouvée pour la sous-catégorie: {subcategory}"}
            
            # Create a fallback temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create fallback temporary ticket
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="PRIORITY_FALLBACK",
                    user=user,
                    ticket_type="Incident",
                    priority="",
                    description=description,
                    subcategories=subcategories,
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved fallback temporary ticket after priority detection: {ticket_path}")
                output_state["temp_priority_ticket_id"] = temp_ticket.ticket_id
                
            return output_state
            
        # Create prompt for LLM
        prompt = self._create_priority_detection_prompt(
            subcategory=subcategory,
            rules=rules,
            email_data=email_data
        )
        
        try:
            # Get LLM response
            llm_response = self.llm_handler.get_response(prompt)
            result = self._parse_response(llm_response)
            
            # Prepare updated state with priority and reason
            output_state = {
                **state, 
                "priority": result.get("priority", ""),
                "reason": result.get("reason", "Non spécifié")
            }
            
            # Create and save temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create temporary ticket with priority
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="PRIORITY",
                    user=user,
                    ticket_type="Incident",
                    priority=result.get("priority", ""),
                    description=description,
                    subcategories=subcategories,
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                
                # Save the temporary ticket to file - will overwrite previous temp files
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved temporary ticket after priority detection: {ticket_path}")
                
                # Add ticket_id to state for tracking
                output_state["temp_priority_ticket_id"] = temp_ticket.ticket_id
            
            return output_state
            
        except Exception as e:
            logger.error(f"Failed to determine priority: {str(e)}")
            output_state = {
                **state, 
                "priority": "",
                "reason": f"Erreur lors de la détermination de la priorité: {str(e)}"
            }
            
            # Create a fallback temporary ticket if ticket_manager is available
            if self.ticket_manager:
                # Create fallback temporary ticket
                temp_ticket = self.ticket_manager.create_temp_ticket(
                    stage="PRIORITY_FALLBACK",
                    user=user,
                    ticket_type="Incident",
                    priority="",
                    description=description,
                    subcategories=subcategories,
                    email_data=email_data,
                    thread_id=thread_id,
                    message_id=message_id
                )
                ticket_path = temp_ticket.save_to_file()
                logger.info(f"Saved fallback temporary ticket after priority detection: {ticket_path}")
                output_state["temp_priority_ticket_id"] = temp_ticket.ticket_id
                
            return output_state

    def _create_priority_detection_prompt(self, subcategory: str, rules: list, email_data: Dict[str, Any]) -> str:
        """Create prompt for LLM to determine priority based on email content."""
        # If thread, combine all messages for the prompt
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
        
        prompt = f"""Tu es un assistant intelligent expert en analyse d'incidents dans le système ferroviaire.

**Objectif** : Déterminer la priorité de l'incident à partir de l'email.

**Sous-catégorie** : {subcategory}

**Règles de priorité pour cette sous-catégorie** :
"""
        for rule in rules:
            prompt += f"""\n- Description: {rule.description}\n  Condition critique: {rule.critical_condition}\n  Condition normale: {rule.elevated_condition}\n"""
        
        prompt += f"""\n**Contenu de l'email** :
Expéditeur: {sender}
Sujet: {subject}
Message: {body}

Analyse le contenu de l'email et détermine la priorité de l'incident selon les règles ci-dessus.
Si les informations sont insuffisantes, indique-le dans la raison et laisse le champ priorité vide.

Réponds au format JSON suivant :
{{
    "priority": "CRITIQUE" ou "ELEVEE" ou "",
    "reason": "Explication détaillée de la décision"
}}
"""
        return prompt

    def _parse_response(self, response: Any) -> Dict[str, Any]:
        """Parse and validate the LLM response."""
        logger.debug("Parsing LLM response for priority detection...")
        
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            content = content.replace('```json', '').replace('```', '').strip()
            
            logger.debug(f"Raw response: {content[:200]}")  # Log first 200 chars
            
            result = json.loads(content)
            
            # Validate response format
            if "reason" not in result:
                logger.warning("Missing 'reason' field in response")
                result["reason"] = "Non spécifié"
                
            if "priority" not in result:
                logger.warning("Missing 'priority' field in response")
                result["priority"] = ""
                
            # Normalize priority values
            if result.get("priority"):
                priority = result["priority"].upper()
                if priority not in ["CRITIQUE", "ELEVEE"]:
                    logger.warning(f"Invalid priority value: {priority}, defaulting to empty")
                    result["priority"] = ""
                else:
                    result["priority"] = priority
            
            logger.info(f"Detected priority: {result.get('priority', '')} - Reason: {result.get('reason', '')}")
            return result
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON response from LLM")
            return {"priority": "", "reason": "Format de réponse invalide"}
        except Exception as e:
            logger.error(f"Response parsing failed: {str(e)}")
            return {"priority": "", "reason": f"Erreur d'analyse: {str(e)}"} 