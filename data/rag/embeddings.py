import os
import ollama
import numpy as np

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")

_embed_client = ollama.Client(host=OLLAMA_HOST)


def embed_text(text: str) -> np.ndarray:
    """Transforme un texte en vecteur via le modele d'embedding Ollama.
    Necessite : ollama pull nomic-embed-text (a faire une seule fois sur le serveur)."""
    response = _embed_client.embeddings(model=EMBED_MODEL, prompt=text)
    return np.array(response["embedding"], dtype="float32")


def embed_batch(texts: list) -> np.ndarray:
    """Ollama n'a pas d'endpoint batch natif pour /api/embeddings, donc on
    boucle. Acceptable pour quelques centaines de chunks au niveau JSON."""
    return np.vstack([embed_text(t) for t in texts])