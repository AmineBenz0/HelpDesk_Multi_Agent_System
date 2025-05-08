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
    """Rule template for subcategory rules."""
    description: str  # Full rule description
    affectation: str  # Team responsible
    priority_level: str  # P1 or P2
    subcategory: str  # The subcategory this rule belongs to

class SubcategoryRules:
    """Defines rules and questions for each subcategory with the new JSON structure."""
    
    _rules: Dict[str, List[RuleTemplate]] = None

    @classmethod
    def _load_rules(cls) -> None:
        """Load rules from JSON file using the new structure."""
        if cls._rules is not None:
            return

        try:
            rules_path = Path(__file__).parent / "config" / "subcategory_rules.json"
            with open(rules_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            cls._rules = {}
            
            # New structure: data_buisness_rules > subcategory_P1/P2 > [rules]
            business_rules = rules_data.get("data_buisness_rules", {})
            
            # Process each subcategory section
            for section_name, rules_list in business_rules.items():
                # Extract subcategory and priority from section name (format: SUBCATEGORY_P1)
                if "_" in section_name:
                    subcategory, priority_level = section_name.split("_", 1)
                else:
                    subcategory = section_name
                    priority_level = "P1"  # Default if not specified
                
                # Initialize subcategory list if not exists
                if subcategory not in cls._rules:
                    cls._rules[subcategory] = []
                
                # Add rules for this subcategory
                for rule_item in rules_list:
                    rule_template = RuleTemplate(
                        description=rule_item.get("rule", ""),
                        affectation=rule_item.get("affectation", ""),
                        priority_level=priority_level,
                        subcategory=subcategory
                    )
                    cls._rules[subcategory].append(rule_template)
            
            logger.info(f"Subcategory rules loaded successfully. Found {len(cls._rules)} subcategories.")
            
            # Debug log the loaded rules
            for subcategory, rules in cls._rules.items():
                logger.debug(f"Subcategory '{subcategory}': {len(rules)} rules")
                
        except Exception as e:
            logger.error(f"Failed to load subcategory rules: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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
        
        # Handle None case
        if subcategory is None:
            logger.warning("Subcategory is None, returning empty rules list")
            return []
            
        # Ensure subcategory is a string
        if not isinstance(subcategory, str):
            logger.warning(f"Subcategory is not a string (type: {type(subcategory)}), attempting to convert")
            try:
                subcategory = str(subcategory)
            except Exception as e:
                logger.error(f"Failed to convert subcategory to string: {str(e)}")
                return []
        
        # Check if rules exist for this subcategory
        if cls._rules is None:
            logger.error("Rules dictionary is None")
            return []
            
        # Return rules for subcategory or empty list if not found
        rules = cls._rules.get(subcategory, [])
        logger.debug(f"Found {len(rules)} rules for subcategory: {subcategory}")
        return rules

    @classmethod
    def get_prompt_for_subcategory(cls, subcategory: str, email_thread: List[Dict[str, str]] = None) -> Optional[str]:
        """Generate a prompt for the LLM based on subcategory rules and email thread context.
        
        Args:
            subcategory: The subcategory to generate rules for
            email_thread: List of email messages in the thread, each containing 'subject' and 'body'
        """
        cls._load_rules()
        rules = cls._rules.get(subcategory, [])
        if not rules:
            return None

        # Create sections for P1 and P2 rules
        p1_rules = [rule for rule in rules if rule.priority_level == "P1"]
        p2_rules = [rule for rule in rules if rule.priority_level == "P2"]

        prompt = f"""Pour la sous-catégorie '{subcategory}', voici les règles qui déterminent si le ticket est critique (P1) ou élevé (P2) :

"""
        # Add P1 rules (Critical)
        if p1_rules:
            prompt += """
Règles CRITIQUES (P1) :
"""
            for i, rule in enumerate(p1_rules, 1):
                prompt += f"""
Règle {i} [P1]:
Description: {rule.description}
Affectation: {rule.affectation}

"""

        # Add P2 rules (Elevated)
        if p2_rules:
            prompt += """
Règles ÉLEVÉES (P2) :
"""
            for i, rule in enumerate(p2_rules, 1):
                prompt += f"""
Règle {i} [P2]:
Description: {rule.description}
Affectation: {rule.affectation}

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
En tenant compte du contexte de la conversation ci-dessus, génère une question claire et concise qui permettra de déterminer si la condition critique (P1) ou normale (P2) s'applique.
"""
        else:
            prompt += """
Génère une question claire et concise qui permettra de déterminer si la condition critique (P1) ou normale (P2) s'applique.
"""
        
        prompt += """
Les questions doivent être formulées de manière à obtenir des réponses claires qui permettront de classer le ticket comme critique (P1) ou normal (P2).
Format de sortie attendu en JSON:
{
    "questions": [
        {
            "question": "question text",
            "critical_answers": ["liste des réponses indiquant une condition critique (P1)"],
            "elevated_answers": ["liste des réponses indiquant une condition normale (P2)"]
        }
    ]
}
"""
        return prompt

    @classmethod
    def get_team_for_rule(cls, subcategory: str, rule_description: str) -> Optional[str]:
        """Get the assigned team for a specific rule in a subcategory."""
        cls._load_rules()
        rules = cls._rules.get(subcategory, [])
        
        for rule in rules:
            if rule.description == rule_description:
                return rule.affectation
                
        return None

    @classmethod
    def evaluate_priority_with_llm(cls, subcategory: str, email_content: str, llm_handler) -> Priority:
        """Evaluate priority using LLM based on email content and rules."""
        cls._load_rules()
        rules = cls._rules.get(subcategory, [])
        if not rules:
            logger.warning(f"No rules found for subcategory: {subcategory}")
            return Priority.ELEVEE  # Default to elevated if no rules exist

        # Sort rules by priority level
        p1_rules = [rule for rule in rules if rule.priority_level == "P1"]
        p2_rules = [rule for rule in rules if rule.priority_level == "P2"]

        # Create a prompt for the LLM
        prompt = f"""Analysez le contenu de l'email suivant et déterminez si la situation est CRITIQUE (P1) ou ELEVEE (P2) en fonction des règles fournies.

Règles pour la sous-catégorie '{subcategory}':

"""
        # Add P1 (Critical) rules
        if p1_rules:
            prompt += """
Règles CRITIQUES (P1):
"""
            for i, rule in enumerate(p1_rules, 1):
                prompt += f"""
{i}. {rule.description} [Affectation: {rule.affectation}]
"""

        # Add P2 (Elevated) rules
        if p2_rules:
            prompt += """
Règles ELEVÉES (P2):
"""
            for i, rule in enumerate(p2_rules, 1):
                prompt += f"""
{i}. {rule.description} [Affectation: {rule.affectation}]
"""

        prompt += f"""

Contenu de l'email:
{email_content}

Analysez le contenu de l'email et déterminez si la situation correspond à une règle CRITIQUE (P1) ou ELEVEE (P2).
Si une règle CRITIQUE (P1) s'applique, la priorité est CRITIQUE.
Si aucune règle CRITIQUE (P1) ne s'applique mais qu'une règle ELEVEE (P2) s'applique, la priorité est ELEVEE.
Si aucune règle ne s'applique clairement, la priorité par défaut est ELEVEE.

Répondez au format JSON suivant:
{{
    "priority": "CRITIQUE" ou "ELEVEE",
    "reason": "Explication de la décision",
    "matching_rule": "Description de la règle correspondante" 
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
                logger.info(f"Matching rule: {result.get('matching_rule', 'No matching rule specified')}")
                
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