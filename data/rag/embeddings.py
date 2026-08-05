import os
import ollama
import numpy as np

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
# Get the embedding model name from the environment.
# Default to "nomic-embed-text".
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
# Create a reusable Ollama client.
_embed_client = ollama.Client(host=OLLAMA_HOST)


def embed_text(text: str) -> np.ndarray:
    """
    Convert a text into a numerical embedding vector using the Ollama
    embedding model.

    The model must be downloaded beforehand:
        ollama pull nomic-embed-text"""
    response = _embed_client.embeddings(model=EMBED_MODEL, prompt=text)
     # Convert the returned embedding into a NumPy array.
    return np.array(response["embedding"], dtype="float32")


def embed_batch(texts: list) -> np.ndarray:
    """
    Generate embeddings for multiple texts.

    Ollama does not provide a native batch embedding endpoint,
    so each text is processed individually and the resulting
    vectors are stacked into a single NumPy matrix.
    """
    return np.vstack([embed_text(t) for t in texts])