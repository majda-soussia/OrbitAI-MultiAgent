"""
ingest.py

Workflow:
1. Load all JSON files from data/rag/sources/ using chunker.py.
2. Generate embeddings for each chunk using embeddings.py and Ollama.
3. Build a FAISS vector index.
4. Save the FAISS index and chunk metadata into data/rag/index/.
"""
import os
import json
import faiss  # Library for fast similarity search on embedding vectors.
import numpy as np
from data.rag.chunker import build_all_chunks
from data.rag.embeddings import embed_batch
# Output directory for the FAISS index and metadata.
INDEX_DIR = os.path.join(os.path.dirname(__file__), "index")
INDEX_PATH = os.path.join(INDEX_DIR, "orbit.faiss") # Path to the FAISS index file.
# Path to the metadata file associated with the index.
META_PATH = os.path.join(INDEX_DIR, "orbit_meta.json")


def normalize(vectors: np.ndarray) -> np.ndarray: # Normalize embedding vectors to unit length.
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1e-9
    return vectors / norms


def main():
    os.makedirs(INDEX_DIR, exist_ok=True)

    print("1/4 - Lecture de data/rag/sources/ ...")
    chunks = build_all_chunks()
    print(f"      -> {len(chunks)} chunks")

    if not chunks:
        print("Aucun chunk trouve. Verifiez que data/rag/sources/ contient des .json.")
        return

    print("2/4 - Calcul des embeddings via Ollama ...")
     # Convert each chunk into an embedding vector.
    vectors = embed_batch([c["text"] for c in chunks]) 
    # Normalize vectors before inserting them into FAISS
    vectors = normalize(vectors)
    dim = vectors.shape[1]

    print("3/4 - Construction de l'index FAISS ...")
    index = faiss.IndexFlatIP(dim)
    index.add(vectors)

    print("4/4 - Sauvegarde ...")
    faiss.write_index(index, INDEX_PATH)
    meta = {str(i): {"id": c["id"], "text": c["text"], "metadata": c["metadata"]}
            for i, c in enumerate(chunks)}
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"OK. Index: {INDEX_PATH} | Meta: {META_PATH}")


if __name__ == "__main__":
    main()