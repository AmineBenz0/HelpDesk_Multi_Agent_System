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
        template="""Tu es un assistant intelligent expert en gestion des tickets dans un service de support.

                    **Objectif** : Analyser l'email ci-dessous et le classer dans l'une des deux catégories suivantes :
                    - "Demande" : une requête d'information, d'assistance ou de service sans impact direct sur le fonctionnement.
                    - "Incident" : un signalement de dysfonctionnement, panne, interruption de service ou anomalie ayant un impact.

                    **Étapes à suivre (raisonnement étape par étape)** :
                    1. Lis attentivement l'objet et le contenu de l'email.
                    2. Identifie les mots-clés ou expressions indiquant un problème, une panne ou une demande de service.
                    3. Analyse le contexte pour déterminer s'il s'agit d'un incident ou d'une simple demande.
                    4. Choisis la catégorie la plus appropriée selon les définitions ci-dessus.

                    ---

                    ### Détails de l'email :
                    **Expéditeur** : {sender}  
                    **Objet** : "{subject}"  
                    **Contenu** :  
                    {body}

                    ---

                    ### Format attendu (strictement JSON) :
                    Ne réponds que par un objet JSON valide contenant la catégorie identifiée. Aucune explication ni texte supplémentaire.

                    ```json
                    {{
                        "category": "Demande" | "Incident"
                    }}""",
                    
        description="Prompt for classifying emails into categories"
    ),
    "incident_subcategory": PromptTemplate(
        name="incident_subcategory",
        template="""Tu es un assistant intelligent expert en gestion des incidents dans le système ferroviaire.

                    **Objectif** : Analyser l'incident signalé et le classer dans les sous-catégories appropriées.

                    **Sous-catégories disponibles** :
                    - Gares : Problèmes liés aux gares
                    - Bâtiment/District : Problèmes liés aux bâtiments ou districts
                    - ECOM : Problèmes liés au système ECOM
                    - ONCF.MA : Problèmes liés au système ONCF.MA
                    - ONCF TRAFIC : Problèmes liés au trafic
                    - CRC : Problèmes liés au Centre de Régulation et de Contrôle
                    - CCR : Problèmes liés au Centre de Contrôle Régional

                    **Étapes à suivre** :
                    1. Analyse le contenu de l'incident
                    2. Identifie les mots-clés et le contexte
                    3. Détermine la ou les sous-catégories les plus pertinentes
                    4. Si plusieurs sous-catégories sont pertinentes, les classer par ordre de priorité

                    ---

                    ### Détails de l'incident :
                    **Expéditeur** : {sender}  
                    **Objet** : "{subject}"  
                    **Contenu** :  
                    {body}

                    ---

                    ### Format attendu (strictement JSON) :
                    Ne réponds que par un objet JSON valide contenant les sous-catégories identifiées. Aucune explication ni texte supplémentaire.

                    ```json
                    {{
                        "subcategories": [
                            {{
                                "category": "Nom de la sous-catégorie",
                                "confidence": "Niveau de confiance (0-1)"
                            }}
                        ]
                    }}""",
        description="Prompt for classifying incidents into subcategories"
    )
}

def get_email_classification_prompt(sender: str, subject: str, body: str) -> str:
    """Get formatted classification prompt."""
    return EMAIL_PROMPTS["classification"].template.format(
        sender=sender,
        subject=subject,
        body=body
    )

def get_incident_subcategory_prompt(sender: str, subject: str, body: str) -> str:
    """Get formatted incident subcategory classification prompt."""
    return EMAIL_PROMPTS["incident_subcategory"].template.format(
        sender=sender,
        subject=subject,
        body=body
    )

def get_prompt(name: str, **kwargs) -> str:
    """General prompt retrieval function."""
    if name not in EMAIL_PROMPTS:
        raise ValueError(f"Prompt {name} not found")
    return EMAIL_PROMPTS[name].template.format(**kwargs)