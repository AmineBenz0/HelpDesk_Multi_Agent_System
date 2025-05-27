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
        template="""Tu es un assistant intelligent expert en gestion des incidents dans le système ferroviaire.\n\n
        **Objectif** : Analyser l'incident signalé et le classer dans les sous-catégories appropriées.\n\n
        **IMPORTANT** : Si la conversation contient plusieurs messages, CONCENTRE-TOI sur le DERNIER message de l'utilisateur (le plus récent) comme étant la réponse la plus probable à la demande de sous-catégorie.
                        Si ce dernier message contient explicitement une sous-catégorie, utilise-la en priorité. 
                        Sinon, analyse l'ensemble du fil.\n\n**Sous-catégories disponibles** :\n
                        - Gares : Problèmes liés aux gares\n
                        - Bâtiment/District : Problèmes liés aux bâtiments ou districts\n
                        - ECOM/ONCF.MA/ONCF TRAFIC : Problèmes liés au système ECOM\n
                        - CRC : Problèmes liés au Centre de Régulation et de Contrôle\n
                        - CRC : Problèmes liés au Centre de Régulation et de Contrôle\n
                        - CCR : Problèmes liés au Centre de Contrôle Régional\n\n
        **Étapes à suivre** :\n
                        1. Analyse le DERNIER message de l'utilisateur pour une réponse explicite.\n
                        2. Si une sous-catégorie claire y est mentionnée, utilise-la avec un niveau de confiance élevé.\n
                        3. Sinon, analyse le contenu de l'incident et le contexte global.\n
                        4. Identifie les mots-clés et le contexte.\n
                        5. Détermine la ou les sous-catégories les plus pertinentes.\n
                        6. Si plusieurs sous-catégories sont pertinentes, les classer par ordre de priorité.\n\n---\n\n
        ### Détails de l'incident :\n
            **Expéditeur** : {sender}  \n
            **Objet** : \"{subject}\"  \n
            **Contenu** :  \n{body}\n\n---\n\n
        ### Format attendu (strictement JSON) :\n
        Ne réponds que par un objet JSON valide contenant les sous-catégories identifiées. 
        Aucune explication ni texte supplémentaire.\n\n
        ```json\n{{\n    
        \"subcategories\": [\n        
            {{\n            
                \"category\": \"Nom de la sous-catégorie\",\n            
                \"confidence\": \"Niveau de confiance (0-1)\"\n        
            }}\n    ]\n}}\n""",
        description="Prompt for classifying incidents into subcategories (focus on latest message)"
    ),
    "user_info_extraction": PromptTemplate(
        name="user_info_extraction",
        template="""Tu es un assistant intelligent expert en extraction d'informations à partir d'emails.

                **Objectif** : Extraire les informations utilisateur et la description de l'incident à partir d'un email.

                    **Informations à extraire** :
                    1. Nom complet de l'utilisateur
                    2. Email de l'utilisateur
                    3. Localisation physique de l'utilisateur
                    4. Description détaillée du problème
                    **Format des emails** :
                    1.Les emails sont présentés dans l'ordre chronologique, du plus ancien au plus récent.
                    2. Chaque email est séparé par une ligne de séparation.

                    **Règles importantes** :
                    - N'extrais que les informations explicitement mentionnées dans l'email
                    - Ne fais pas de déductions ou d'inférences
                    - Si une information n'est pas explicitement mentionnée, laisse le champ vide ("")
                    - Pour la localisation, n'accepte QUE :
                      * Noms de gares ferroviaires (ex: "Gare Casa Voyageurs", "Gare Rabat Ville")
                      * Noms de villes (ex: "Rabat", "Casablanca")
                    - Ne crée pas de localisations génériques ou non spécifiques
                    - Si la localisation n'est pas explicitement mentionnée comme une gare ou une ville, laisse le champ vide

                    ---
                    **Détails de la conversation** :
                    {body}
                    ---
                    **Instructions** :
                    1. Analyser tous les emails de la conversation pour extraire les informations
                    2. Les informations peuvent être présentes dans n'importe quel email de la conversation
                    3. Si une information est mise à jour dans un email plus récent, utiliser la version la plus récente
                    4. Extraire les informations suivantes :
                       - Nom de l'utilisateur
                       - Email de l'utilisateur
                       - Localisation (site, bureau, etc.)
                       - Description détaillée de l'incident

                        **Format attendu (strictement JSON)** :
                        ```json
                    {{
                        "user_info": {{
                            "name": "Nom complet de l'utilisateur",
                            "email": "email@exemple.com (email de l'utilisateur)",
                            "location": "Localisation (site, bureau, etc.)"
                        }},
                        "description": "Description détaillée de l'incident"
                    }}""",
        description="Prompt for extracting user information from emails"
    ),
    "follow_up_questions": PromptTemplate(
        name="follow_up_questions",
        template="""Tu es un assistant intelligent expert en gestion des tickets de support.

                    **Objectif** : Générer des questions de suivi appropriées pour obtenir les informations manquantes.

                    **Contexte** :
                    - Un ticket a été créé avec certaines informations manquantes
                    - Il faut envoyer un email de suivi pour obtenir ces informations
                    - Les questions doivent être claires, professionnelles et spécifiques
                    - Le ton doit être courtois et professionnel

                    **Informations manquantes** :
                    {missing_fields}

                    **Format de l'email** :
                    - Commencer par une salutation professionnelle
                    - Expliquer brièvement pourquoi nous avons besoin de ces informations
                    - Poser les questions de manière claire et structurée
                    - Terminer par une formule de politesse

                    ---

                    ### Format attendu (strictement JSON) :
                    Ne réponds que par un objet JSON valide contenant le sujet et le contenu de l'email de suivi.

                    ```json
                    {{
                        "subject": "Sujet de l'email de suivi",
                        "body": "Contenu de l'email de suivi avec les questions"
                    }}""",
        description="Prompt for generating follow-up questions for missing information"
    ),
    "subcategory_follow_up": PromptTemplate(
        name="subcategory_follow_up",
        template="""Tu es un assistant intelligent expert en gestion des incidents dans le système ferroviaire.

                    **Objectif** : Générer un email de suivi pour clarifier la sous-catégorie de l'incident.

                    **Sous-catégories identifiées** :
                    {subcategories}

                    **Instructions** :
                    1. Créer un email professionnel demandant à l'utilisateur de préciser la sous-catégorie la plus appropriée
                    2. Présenter les sous-catégories identifiées de manière claire
                    3. Demander une confirmation ou une précision
                    4. Maintenir un ton professionnel et courtois

                    **Format de l'email** :
                    - Commencer par une salutation professionnelle
                    - Expliquer brièvement pourquoi nous avons besoin de cette précision
                    - Présenter les sous-catégories identifiées de manière claire
                    - Demander une confirmation ou une précision
                    - Terminer par une formule de politesse

                    ---

                    ### Format attendu (strictement JSON) :
                    Ne réponds que par un objet JSON valide contenant le sujet et le contenu de l'email de suivi.

                    ```json
                    {{
                        "subject": "Sujet de l'email de suivi",
                        "body": "Contenu de l'email de suivi avec les questions"
                    }}""",
        description="Prompt for generating follow-up questions for subcategory clarification"
    ),
    "missing_subcategory_follow_up": PromptTemplate(
        name="missing_subcategory_follow_up",
        template="""Tu es un assistant intelligent expert en gestion des incidents dans le système ferroviaire.
        \n\n**Objectif** : Générer un email de suivi pour demander à l'utilisateur de fournir ou préciser la sous-catégorie de l'incident, car aucune n'a pu être déterminée automatiquement.\n\n
        **Instructions** :\n
        1. Créer un email professionnel demandant à l'utilisateur de préciser la sous-catégorie la plus appropriée pour son incident.\n
        2. Expliquer que cette information est nécessaire pour un traitement efficace.\n
        3. Maintenir un ton professionnel et courtois.\n\n
        **Format de l'email** :\n
        - Commencer par une salutation professionnelle\n
        - Expliquer brièvement pourquoi nous avons besoin de cette précision\n
        - Demander à l'utilisateur de préciser la sous-catégorie\n
        - Terminer par une formule de politesse\n\n---\n\n
        ### Format attendu (strictement JSON) :\n
        Ne réponds que par un objet JSON valide contenant le sujet et le contenu de l'email de suivi.\n\n
        ```json\n
        {{\n    \"subject\": \"Sujet de l'email de suivi\",\n    
                \"body\": \"Contenu de l'email de suivi avec la demande de sous-catégorie\"\n}}""",
        description="Prompt for generating follow-up questions when subcategory is missing"
    ),
    "priority_follow_up": PromptTemplate(
        name="priority_follow_up",
        template="""Tu es un assistant expert en gestion des incidents ferroviaires.

**Objectif** : Générer un email de suivi pour clarifier la priorité de l'incident, en posant uniquement les 1, 2 ou 3 questions les plus pertinentes et discriminantes, choisies selon leur lien direct avec le contenu du mail et les règles de la sous-catégorie.

**Sous-catégorie** : {subcategory}

**Règles de priorité pour cette sous-catégorie** :
{rules}

**Instructions** :
1. Analyse attentivement le contenu du mail et les règles pour identifier les 1, 2 ou 3 questions les plus importantes, permettant de distinguer clairement une situation critique d'une situation normale.
2. Ne pose que des questions directement liées au contexte du mail et aux règles : évite toute question générique, redondante ou qui ne s'applique pas au cas décrit.
3. Ne te contente pas de reformuler les règles : adapte-les au contexte du mail pour obtenir des réponses réellement utiles à la priorisation.
4. Chaque question doit être concise, claire, et permettre une réponse exploitable pour déterminer la priorité.
5. Adopte un ton professionnel et courtois.

**Format de l'email** :
- Salutation professionnelle
- Brève explication du besoin de précision
- Questions sélectionnées (maximum 2 ou 3), formulées de façon claire et structurée
- Formule de politesse

---

### Format attendu (strictement JSON) :
# Ne réponds que par un objet JSON valide contenant le sujet et le contenu de l'email de suivi.

# ```json
{{
    "subject": "Sujet de l'email de suivi",
    "body": "Contenu de l'email de suivi avec les questions sur la priorité"
}}
""",
        description="Prompt pour générer un email de suivi avec uniquement les questions les plus pertinentes pour clarifier la priorité"
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

def get_user_info_extraction_prompt(sender: str, subject: str, body: str) -> str:
    """Get formatted user information extraction prompt."""
    return EMAIL_PROMPTS["user_info_extraction"].template.format(
        body=body
    )

def get_follow_up_questions_prompt(missing_fields: list) -> str:
    """Get formatted follow-up questions prompt."""
    return EMAIL_PROMPTS["follow_up_questions"].template.format(
        missing_fields="\n".join([f"- {field}" for field in missing_fields])
    )

def get_subcategory_follow_up_prompt(subcategories: list) -> str:
    """Get formatted subcategory follow-up prompt."""
    def safe_confidence(conf):
        try:
            return float(conf)
        except Exception:
            return 0.0
    formatted_subcategories = "\n".join([
        f"- {subcat['subcategory']} (confiance: {safe_confidence(subcat.get('confidence', 0)):.2f})"
        for subcat in subcategories
    ])
    return EMAIL_PROMPTS["subcategory_follow_up"].template.format(
        subcategories=formatted_subcategories
    )

def get_missing_subcategory_follow_up_prompt(subcategories: list) -> str:
    """Get formatted missing subcategory follow-up prompt."""
    # subcategories is not used, but kept for interface consistency
    return EMAIL_PROMPTS["missing_subcategory_follow_up"].template

def get_priority_follow_up_prompt(subcategory: str, rules: list) -> str:
    """Get formatted priority follow-up prompt."""
    formatted_rules = "\n".join([
        f"- Description: {rule.description}\n  Condition critique: {rule.critical_condition}\n  Condition normale: {rule.elevated_condition}"
        for rule in rules
    ])
    return EMAIL_PROMPTS["priority_follow_up"].template.format(
        subcategory=subcategory,
        rules=formatted_rules
    )

def get_prompt(name: str, **kwargs) -> str:
    """General prompt retrieval function."""
    if name not in EMAIL_PROMPTS:
        raise ValueError(f"Prompt {name} not found")
    return EMAIL_PROMPTS[name].template.format(**kwargs)