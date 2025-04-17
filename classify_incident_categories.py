
# Prompt principal
prompt_intro = """
Ta tâche est de lire attentivement l’email ci-dessous et de déterminer une seule chose :

1. L’**établissement ou gare concernée**, en choisissant parmi les catégories suivantes :

### Explication des établissements / gares :

- **GARES** : Toute infrastructure liée aux gares voyageurs (ex : Gare Rabat Ville, Gare Casa Voyageurs, etc.) ou installations situées sur le réseau ferroviaire accueillant du public.
- **Bâtiment/District** : Bâtiments administratifs régionaux ou locaux techniques situés en dehors des gares (ex : Centre technique du district Nord, Siège local, etc.).
- **ECOM / ONCF.MA / ONCF TRAFIC** : Problèmes liés aux services numériques (site web oncf.ma, e-commerce, billetterie en ligne, application mobile, etc.).
- **CRC** (Centre de Relation Client) : Problèmes rencontrés par les équipes du centre d’appel/plateforme téléphonique (ex : appels non reçus, logiciel CRC en panne...).
- **CCR** (Centre de Commandement et de Régulation) : Incidents liés au centre de supervision du trafic ferroviaire (outils de supervision, communication interne, etc.).

Tu dois **déduire ces éléments depuis le contenu de l’email**.

---

Réponds **exclusivement** sous le format suivant (même si certaines informations sont incertaines, fais une hypothèse raisonnable) :

- Établissement/Gare : <catégorie parmi celles listées ci-dessus>

---
"""

# Fonction pour analyser un email et retourner le résultat formaté
def analyze_email(email_text: str) -> str:
    full_prompt = f"{prompt_intro}\nEmail :\n\"\"\"\n{email_text.strip()}\n\"\"\""

    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": full_prompt}],
        temperature=0.2
    )

    result = response.choices[0].message.content.strip()

    # Extraction et normalisation du résultat
    known_categories = {
        "GARES", "Bâtiment/District", "ECOM / ONCF.MA / ONCF TRAFIC", "CRC", "CCR"
    }
    for category in known_categories:
        if category in result:
            return f"- Établissement/Gare : {category.upper()}" if category.isupper() else f"- Établissement/Gare : {category}"

    return result  # fallback si la réponse est inattendue
