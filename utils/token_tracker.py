import json
import os
from datetime import datetime

USAGE_FILE = "data/token_usage.json"


def _load():
    if not os.path.exists(USAGE_FILE):
        return []
    try:
        with open(USAGE_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save(data):
    os.makedirs(os.path.dirname(USAGE_FILE), exist_ok=True)
    with open(USAGE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _log_usage_to_db(user_id: int, agent_name: str, prompt_tokens: int, response_tokens: int):
    """Écrit dans PostgreSQL (token_usage) — seule source utilisée pour le
    quota client (via la vue client_token_summary) et pour le futur
    breakdown par utilisateur/agent dans /admin. N'échoue jamais bruyamment :
    un souci de connexion DB ne doit pas faire planter un appel LLM."""
    from utils.db import get_connection
    try:
        conn = get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO token_usage (user_id, agent_name, prompt_tokens, response_tokens, total_tokens)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (user_id, agent_name, prompt_tokens, response_tokens, prompt_tokens + response_tokens),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()
    except Exception as e:
        print(f"[token_tracker] DB write failed (non-blocking): {e}")


def log_usage(
    agent_name: str,
    prompt_tokens: int,
    response_tokens: int,
    client_email: str = None,
    user_id: int = None,
):
    # JSON reste la source du dashboard "Tokens by Agent" GLOBAL (image 3),
    # tous utilisateurs et invités confondus — on ne casse rien ici.
    data = _load()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "client_email": client_email,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "total_tokens": prompt_tokens + response_tokens,
    }
    data.append(entry)
    _save(data)
    if user_id is not None:
        _log_usage_to_db(user_id, agent_name, prompt_tokens, response_tokens)

    return entry

def get_summary():
    data = _load()
    total = sum(e["total_tokens"] for e in data)
    by_agent = {}
    for e in data:
        by_agent[e["agent"]] = by_agent.get(e["agent"], 0) + e["total_tokens"]
    return {
        "total_calls": len(data),
        "total_tokens": total,
        "by_agent": by_agent,
    }
def get_last_call_tokens() -> int:
    """Retourne le total de tokens du dernier appel enregistré."""
    data = _load()
    if not data:
        return 0
    last = data[-1]
    return last.get("total_tokens", 0)


def get_usage_by_client() -> dict:
    """
    Retourne, pour chaque client identifié (email non None), sa
    consommation de tokens ventilée par agent :
    { "client@example.com": {"Commercial": 1234, "Email": 567, ...}, ... }

    Les entrées sans client_email (usage CLI/dev, ou appels effectués
    avant ce champ) sont simplement ignorées ici, pas comptées comme
    "None".
    """
    data = _load()
    by_client: dict[str, dict[str, int]] = {}

    for e in data:
        email = e.get("client_email")
        if not email:
            continue
        agent = e["agent"]
        by_client.setdefault(email, {})
        by_client[email][agent] = by_client[email].get(agent, 0) + e["total_tokens"]

    return by_client