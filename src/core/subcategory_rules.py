from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
from src.utils.logger import logger

class Priority(Enum):
    ELEVEE = "Élevée"
    CRITIQUE = "Critique"

@dataclass
class RuleTemplate:
    description: str
    critical_condition: str
    elevated_condition: str
    team: str

class SubcategoryRules:
    """Defines rules and questions for each subcategory."""
    
    _rules: Dict[str, List[RuleTemplate]] = None

    @classmethod
    def _load_rules(cls) -> None:
        """Load rules from JSON file."""
        if cls._rules is not None:
            return

        try:
            rules_path = Path(__file__).parent / "config" / "subcategory_rules.json"
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            cls._rules = {}
            for subcategory, templates in rules_data.items():
                cls._rules[subcategory] = [
                    RuleTemplate(
                        description=template["description"],
                        critical_condition=template["critical_condition"],
                        elevated_condition=template["elevated_condition"],
                        team=template["team"]
                    )
                    for template in templates
                ]
            logger.info("Subcategory rules loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load subcategory rules: {str(e)}")
            cls._rules = {}

    @classmethod
    def get_rules_for_subcategory(cls, subcategory: str) -> List[RuleTemplate]:
        """Get all rules for a specific subcategory.
        
        Args:
            subcategory: The subcategory to get rules for
            
        Returns:
            List of RuleTemplate objects for the subcategory
        """
        cls._load_rules()
        return cls._rules.get(subcategory, [])

    @classmethod
    def get_prompt_for_subcategory(cls, subcategory: str, email_thread: List[Dict[str, str]] = None) -> Optional[str]:
        """Generate a prompt for the LLM based on subcategory rules and email thread context.
        
        Args:
            subcategory: The subcategory to generate rules for
            email_thread: List of email messages in the thread, each containing 'subject' and 'body'
        """
        cls._load_rules()
        templates = cls._rules.get(subcategory)
        if not templates:
            return None

        prompt = f"""Pour la sous-catégorie '{subcategory}', voici les règles qui déterminent si le ticket est critique ou élevé :

"""
        for i, template in enumerate(templates, 1):
            prompt += f"""
Règle {i}:
Description: {template.description}
Condition critique: {template.critical_condition}
Condition normale: {template.elevated_condition}

"""
        
        # Add email thread context if available
        if email_thread:
            prompt += """
Contexte de la conversation :
"""
            for email in email_thread:
                prompt += f"""
Sujet: {email.get('subject', '')}
Message: {email.get('body', '')}
"""
            prompt += """
En tenant compte du contexte de la conversation ci-dessus, génère une question claire et concise qui permettra de déterminer si la condition critique ou normale s'applique.
"""
        else:
            prompt += """
Génère une question claire et concise qui permettra de déterminer si la condition critique ou normale s'applique.
"""
        
        prompt += """
Les questions doivent être formulées de manière à obtenir des réponses claires qui permettront de classer le ticket comme critique ou normal.
Format de sortie attendu en JSON:
{
    "questions": [
        {
            "question": "question text",
            "critical_answers": ["liste des réponses indiquant une condition critique"],
            "elevated_answers": ["liste des réponses indiquant une condition normale"]
        }
    ]
}
"""
        return prompt

    @classmethod
    def get_team_for_subcategory(cls, subcategory: str) -> Optional[str]:
        """Get the assigned team for a subcategory."""
        cls._load_rules()
        templates = cls._rules.get(subcategory)
        if templates and len(templates) > 0:
            return templates[0].team
        return None

    @classmethod
    def evaluate_priority_with_llm(cls, subcategory: str, email_content: str, llm_handler) -> Priority:
        """Evaluate priority using LLM based on email content and rules."""
        cls._load_rules()
        templates = cls._rules.get(subcategory)
        if not templates:
            logger.warning(f"No rules found for subcategory: {subcategory}")
            return Priority.ELEVEE  # Default to elevated if no rules exist

        # Create a prompt for the LLM
        prompt = f"""Analysez le contenu de l'email suivant et déterminez si la situation est critique ou élevée en fonction des règles fournies.

Règles pour la sous-catégorie '{subcategory}':

"""
        for template in templates:
            prompt += f"""
Description: {template.description}
Condition critique: {template.critical_condition}
Condition normale: {template.elevated_condition}
"""

        prompt += f"""

Contenu de l'email:
{email_content}

Analysez le contenu de l'email et déterminez si la situation correspond à une condition critique ou normale.
Répondez au format JSON suivant:
{{
    "priority": "CRITIQUE" ou "ELEVEE",
    "reason": "Explication de la décision"
}}
"""

        try:
            logger.debug(f"Sending priority evaluation prompt for subcategory: {subcategory}")
            response = llm_handler.get_response(prompt)
            response_content = response.content.strip()
            logger.debug(f"LLM priority evaluation response: {response_content}")
            
            # Parse JSON response
            try:
                result = json.loads(response_content)
                priority_text = result.get("priority", "").upper()
                logger.info(f"Priority evaluation reason: {result.get('reason', 'No reason provided')}")
                
                if priority_text == "CRITIQUE":
                    logger.info(f"Priority evaluated as CRITIQUE for subcategory: {subcategory}")
                    return Priority.CRITIQUE
                logger.info(f"Priority evaluated as ELEVEE for subcategory: {subcategory}")
                return Priority.ELEVEE
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
                return Priority.ELEVEE
                
        except Exception as e:
            logger.error(f"Failed to evaluate priority with LLM: {str(e)}")
            return Priority.ELEVEE

    @classmethod
    def evaluate_priority(cls, subcategory: str, answers: Dict[str, str], llm_handler=None, email_content: str = None) -> Priority:
        """Evaluate the priority based on answers to the rules."""
        # If we have email content and LLM handler, use the LLM-based evaluation
        if email_content and llm_handler:
            return cls.evaluate_priority_with_llm(subcategory, email_content, llm_handler)
            
        # Fall back to the original rule-based evaluation
        cls._load_rules()
        templates = cls._rules.get(subcategory)
        if not templates:
            return Priority.ELEVEE  # Default to elevated if no rules exist

        critical_count = 0
        elevated_count = 0

        for template in templates:
            answer = answers.get(template.description, "").lower()
            if answer in [a.lower() for a in template.critical_condition.split(",")]:
                critical_count += 1
            elif answer in [a.lower() for a in template.elevated_condition.split(",")]:
                elevated_count += 1

        # If any answer indicates critical, return critical
        if critical_count > 0:
            return Priority.CRITIQUE
        return Priority.ELEVEE 