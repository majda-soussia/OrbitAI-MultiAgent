"""
Politique de tokens PAR PLAN — combien de messages d'historique et
combien de chunks RAG sont envoyés au modèle, selon que le client est
'standard' ou 'premium'. Lu depuis config/token_policy.json, jamais codé
en dur, pour pouvoir ajuster ces curseurs qualité/coût sans redéployer
de code (ex: depuis un futur écran admin).
"""
import json

TOKEN_POLICY_FILE = "config/token_policy.json"

# Filet de sécurité si le fichier est absent/corrompu : l'agent doit
# continuer à fonctionner, avec des valeurs raisonnables par défaut,
# plutôt que de planter.
DEFAULT_POLICY = {
    "standard": {"max_history_messages": 6, "rag_top_k": 3},
    "premium": {"max_history_messages": 20, "rag_top_k": 6},
}


def _load_policy() -> dict:
    try:
        with open(TOKEN_POLICY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return DEFAULT_POLICY


def get_policy_for_plan(plan: str) -> dict:
    """
    Retourne {"max_history_messages": int, "rag_top_k": int} pour le plan
    donné. Un plan inconnu (typo, nouveau plan pas encore configuré)
    retombe sur 'standard' plutôt que de faire planter l'agent.
    """
    policy = _load_policy()
    return policy.get(plan) or policy.get("standard") or DEFAULT_POLICY["standard"]