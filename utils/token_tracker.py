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


def log_usage(agent_name: str, prompt_tokens: int, response_tokens: int):
    data = _load()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "agent": agent_name,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "total_tokens": prompt_tokens + response_tokens,
    }
    data.append(entry)
    _save(data)
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