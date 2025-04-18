
from sentence_transformers import SentenceTransformer

# Fonction pour découper le texte en morceaux avec une garde d'intersection par mots
def chunk_text_with_overlap(text, chunk_size=512, overlap_words=2):
    words = text.split()  # Découper le texte en mots
    chunks = []
    
    # Déterminer combien de morceaux de texte on peut créer
    for i in range(0, len(words), chunk_size - overlap_words):
        chunk = " ".join(words[i:i + chunk_size])  # Rassembler les mots dans un morceau
        chunks.append(chunk)
    
    # Appliquer l'overlap en ajustant chaque morceau suivant
    for i in range(1, len(chunks)):
        # Ajouter l'overlap (les derniers mots du morceau précédent) au début du morceau suivant
        overlap = chunks[i-1].split()[-overlap_words:]
        chunks[i] = " ".join(overlap + chunks[i].split()[overlap_words:])
    
    return chunks

# Fonction pour générer des embeddings
def embed_text(text, chunk_size=512, overlap=2):
    # Charger le modèle d'embedding (exemple avec SentenceTransformer)
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')  # Exemple de modèle, vous pouvez en utiliser un autre
    
    # Découper le texte en morceaux avec overlap
    chunks = chunk_text_with_overlap(text, chunk_size, overlap)

    # Embedding pour chaque morceau
    embeddings = embedding_model.encode(chunks)

    return embeddings
