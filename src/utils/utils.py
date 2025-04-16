# === PROMPT POUR CLASSIFICATION EMAIL ===
MEILLEUR_PROMPT = """
Analysez cet email et classifiez-le comme:
- "demande": Email demandant un service, une assistance ou une action
- "incident": Email signalant un problème technique, une panne ou un incident
Objet: {subject}
Corps: {body}
IMPORTANT: Vous devez répondre UNIQUEMENT avec l'objet JSON suivant sans aucun texte d'introduction ni commentaire. N'utilisez pas de délimiteurs comme ```json ou ```. Fournissez simplement le JSON brut:
{{"resultat": "demande ou incident", "explication": "votre justification en 1-2 phrases", "confiance": 85}}
Où:
- "resultat" est soit "demande" soit "incident"
- "explication" est votre justification en 1-2 phrases
- "confiance" est un pourcentage entre 0-100 (sans le symbole %)
"""

# === CLASSIFICATION D'UN EMAIL ===
def classifier_email(objet: str, corps: str) -> Dict[str, Any]:
    prompt = PromptTemplate(input_variables=["subject", "body"], template=MEILLEUR_PROMPT)
    chaine = LLMChain(llm=llm_principal, prompt=prompt)

    try:
        resultat = chaine.invoke({"subject": objet, "body": corps})
        texte_reponse = resultat.get("text", "").strip()

        try:
            data = json.loads(texte_reponse)
        except json.JSONDecodeError:
            json_match = re.search(r'{.*}', texte_reponse, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
                except:
                    data = {}
            else:
                data = {}

        if data:
            return {
                "classification": data.get("resultat", "indéterminé").lower(),
                "explication": data.get("explication", "explication manquante"),
                "confiance": int(data.get("confiance", 50)),
                "reponse_complete": texte_reponse,
                "json_brut": data
            }
