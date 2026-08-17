TOKENIZER_MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"

_tokenizer = None


def _get_tokenizer():
    global _tokenizer
    if _tokenizer is None:
        from tokenizers import Tokenizer
        _tokenizer = Tokenizer.from_pretrained(TOKENIZER_MODEL_ID)
    return _tokenizer


def inspect_tokens(text: str) -> dict:
    """
    Découpe `text` avec le vrai tokenizer Qwen2.5 et retourne le détail
    complet — nombre de tokens, IDs numériques, et les fragments de texte
    correspondants (ce qu'Ollama ne montre jamais).
    """
    if not text:
        return {"token_count": 0, "token_ids": [], "token_pieces": [], "model": TOKENIZER_MODEL_ID}

    tokenizer = _get_tokenizer()
    encoding = tokenizer.encode(text)

    return {
        "token_count": len(encoding.ids),
        "token_ids": encoding.ids,
        "token_pieces": encoding.tokens,
        "model": TOKENIZER_MODEL_ID,
    }


def compare_with_ollama_count(text: str, ollama_reported_count: int) -> dict:
    """
    Compare notre comptage indépendant à un nombre déjà renvoyé par Ollama
    pour le même texte (ex: prompt_eval_count d'un appel réel), pour
    vérifier qu'ils concordent.
    """
    result = inspect_tokens(text)
    result["ollama_reported_count"] = ollama_reported_count
    result["matches"] = result["token_count"] == ollama_reported_count
    return result