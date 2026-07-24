import json
import os
from datetime import datetime

MEMORY_FILE = "data/client_memory.json"


def _load():
    if not os.path.exists(MEMORY_FILE):
        return {}
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data):
    os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_client_memory(client_id: str) -> dict:
    return _load().get(client_id, {
        "history": [],
        "plan": "standard",
        "first_seen": None,
        "last_seen": None,
    })


def save_client_turn(client_id: str, user_message: str, assistant_response: str):
    data = _load()
    profile = data.get(client_id, {
        "history": [],
        "plan": "standard",
        "first_seen": datetime.now().isoformat(),
        "last_seen": None,
    })

    profile["history"].append({"role": "user", "content": user_message})
    profile["history"].append({"role": "assistant", "content": assistant_response})
    profile["history"] = profile["history"][-20:]
    profile["last_seen"] = datetime.now().isoformat()

    if profile["first_seen"] is None:
        profile["first_seen"] = datetime.now().isoformat()

    data[client_id] = profile
    _save(data)


def set_client_plan(client_id: str, plan: str):
    """Changer le plan d'un client : 'standard' ou 'premium'."""
    data = _load()
    profile = data.get(client_id, {
        "history": [],
        "plan": "standard",
        "first_seen": None,
        "last_seen": None,
    })
    profile["plan"] = plan
    data[client_id] = profile
    _save(data)


def get_all_clients() -> dict:
    return _load()
PLANS_FILE = "config/plans.json"


def _load_plans() -> dict:
    try:
        with open(PLANS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return {"standard": {"token_limit": 5000}, "premium": {"token_limit": 50000}}


def add_client_tokens(client_id: str, tokens_used: int):
    """Incrémente le compteur de tokens consommés par ce client."""
    data = _load()
    profile = data.get(client_id, {
        "history": [],
        "plan": "standard",
        "tokens_used": 0,
        "first_seen": None,
        "last_seen": None,
    })
    profile["tokens_used"] = profile.get("tokens_used", 0) + tokens_used
    data[client_id] = profile
    _save(data)


def check_quota(client_id: str) -> dict:
    """
    Retourne le statut du quota pour ce client.
    {
        "allowed": True/False,
        "plan": "standard"/"premium",
        "tokens_used": 1234,
        "token_limit": 5000,
        "remaining": 3766
    }
    """
    data = _load()
    plans = _load_plans()

    profile = data.get(client_id, {
        "plan": "standard",
        "tokens_used": 0,
    })

    plan_name = profile.get("plan", "standard")
    token_limit = plans.get(plan_name, {}).get("token_limit", 5000)
    tokens_used = profile.get("tokens_used", 0)
    remaining = max(0, token_limit - tokens_used)

    return {
        "allowed": tokens_used < token_limit,
        "plan": plan_name,
        "tokens_used": tokens_used,
        "token_limit": token_limit,
        "remaining": remaining,
    }