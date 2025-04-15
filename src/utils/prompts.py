# src/utils/prompts.py
from dataclasses import dataclass
from typing import Dict

@dataclass
class PromptTemplate:
    name: str
    template: str
    description: str

EMAIL_PROMPTS = {
    "classification": PromptTemplate(
        name="email_classification",
        template="""**Instruction**: Classify this email into either "Demande" or "Incident".
            
### Email Details:
**From**: {sender}
**Subject**: "{subject}"
**Body**:
{body}

### Response Format (JSON only):
{{
    "category": "Demande|Incident",
}}""",
        description="Prompt for classifying emails into categories"
    )
}

def get_email_classification_prompt(sender: str, subject: str, body: str) -> str:
    """Get formatted classification prompt."""
    return EMAIL_PROMPTS["classification"].template.format(
        sender=sender,
        subject=subject,
        body=body
    )

def get_prompt(name: str, **kwargs) -> str:
    """General prompt retrieval function."""
    if name not in EMAIL_PROMPTS:
        raise ValueError(f"Prompt {name} not found")
    return EMAIL_PROMPTS[name].template.format(**kwargs)