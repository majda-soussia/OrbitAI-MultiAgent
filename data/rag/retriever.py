import os
import json
import faiss
import numpy as np

from data.rag.embeddings import embed_text
from data.rag.ingest import normalize, INDEX_PATH, META_PATH
# Cached FAISS index and metadata.
_index = None
_meta = None


def _load():
    """
    Load the FAISS index and metadata into memory.

    The index is loaded only once and reused for all
    subsequent retrieval requests.
    """
    global _index, _meta
    if _index is None:
        if not os.path.exists(INDEX_PATH):
            raise FileNotFoundError(
                "Index FAISS introuvable. Lancez : python rag/ingest.py"
            )
        _index = faiss.read_index(INDEX_PATH)
        with open(META_PATH, "r", encoding="utf-8") as f:
            _meta = json.load(f)
    return _index, _meta


def retrieve(question: str, top_k: int = 4, type_filter: str = None) -> list:
    """Retrieve the most relevant chunks for a user question.

    Parameters:
        question: User query.
        top_k: Maximum number of chunks to return.
        type_filter: Optional metadata filter
                     (e.g. pricing, faq, company).

    Returns:
        A list of matching chunks with their similarity scores.
    """
    index, meta = _load()
    # Convert the user question into an embedding vector.
    q_vector = embed_text(question).reshape(1, -1)
    # Normalize the query vector.
    q_vector = normalize(q_vector)
    # Retrieve extra candidates when filtering by type.
    search_k = index.ntotal if type_filter else top_k
    scores, indices = index.search(q_vector, search_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue
        entry = meta[str(idx)]
        if type_filter and entry["metadata"].get("type") != type_filter:
            continue
        results.append({"text": entry["text"], "metadata": entry["metadata"], "score": float(score)})
        if len(results) >= top_k:
            break
    return results


def build_context_block(results: list) -> str:
    if not results:
        return ""
    lines = ["Relevant Orbit context (use this data, do not invent specs or prices):"]
    for r in results:
        lines.append(f"- {r['text']}")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[1:]) or "price of EMS module for 50 meters"
    print(build_context_block(retrieve(q, top_k=3)))