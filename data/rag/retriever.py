"""
retriever.py
------------
Point d'entree unique appele par BaseAgent.get_rag_context().
Charge l'index FAISS une seule fois (cache module-level) puis expose
retrieve() et build_context_block().
"""

import os
import json
import faiss
import numpy as np

from data.rag.embeddings import embed_text
from data.rag.ingest import normalize, INDEX_PATH, META_PATH

_index = None
_meta = None


def _load():
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
    index, meta = _load()

    q_vector = embed_text(question).reshape(1, -1)
    q_vector = normalize(q_vector)

    search_k = top_k * 5 if type_filter else top_k
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