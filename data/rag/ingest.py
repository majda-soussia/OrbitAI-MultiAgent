"""
ingest.py
---------
A relancer manuellement (ou via un bouton Admin) a chaque mise a jour
d'un fichier dans data/rag/sources/.

Etapes :
1. Lit tous les JSON de data/rag/sources/ (via chunker.py)
2. Calcule les embeddings (via embeddings.py -> Ollama)
3. Construit l'index FAISS
4. Sauvegarde index + metadata dans data/rag/index/
"""

import os
import json
import faiss #rechercher très rapidement les vecteurs les plus proches.
import numpy as np
from data.rag.chunker import build_all_chunks
from data.rag.embeddings import embed_batch

INDEX_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "rag", "index")
INDEX_PATH = os.path.join(INDEX_DIR, "orbit.faiss")
META_PATH = os.path.join(INDEX_DIR, "orbit_meta.json")


def normalize(vectors: np.ndarray) -> np.ndarray: #calcule le produit scalaire (Inner Product).
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
    vectors = embed_batch([c["text"] for c in chunks]) #appelle :embeddings.py
    vectors = normalize(vectors) #vecteurs sont normalisés avant d'être ajoutés à FAISS.
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