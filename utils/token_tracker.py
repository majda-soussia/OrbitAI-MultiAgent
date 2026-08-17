import json
import os
from datetime import datetime

USAGE_FILE = "data/token_usage.json"
PRICE_CONFIG_FILE = "data/token_price_config.json"


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

# ---------------------------------------------------------------------
# CONFIGURATION DU PRIX — modifiable depuis l'interface admin (prioritaire
# sur la variable d'environnement TOKEN_PRICE_PER_1K, qui sert de valeur
# par défaut tant qu'aucun réglage manuel n'a été enregistré).
# ---------------------------------------------------------------------

def get_price_config() -> dict:
    """Retourne {"price_per_1k_tokens": float, "currency": str, "source": "manual"|"env"|"default"}."""
    if os.path.exists(PRICE_CONFIG_FILE):
        try:
            with open(PRICE_CONFIG_FILE, "r") as f:
                saved = json.load(f)
            return {
                "price_per_1k_tokens": float(saved.get("price_per_1k_tokens", 0.0)),
                "currency": saved.get("currency", "€"),
                "source": "manual",
            }
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    env_price = os.environ.get("TOKEN_PRICE_PER_1K")
    if env_price is not None:
        try:
            return {"price_per_1k_tokens": float(env_price), "currency": "€", "source": "env"}
        except ValueError:
            pass

    return {"price_per_1k_tokens": 0.0, "currency": "€", "source": "default"}


def set_price_config(price_per_1k_tokens: float, currency: str = "€") -> dict:
    """Enregistre le prix manuellement depuis l'interface admin. Prend le
    pas sur TOKEN_PRICE_PER_1K tant que ce fichier existe."""
    os.makedirs(os.path.dirname(PRICE_CONFIG_FILE), exist_ok=True)
    config = {"price_per_1k_tokens": price_per_1k_tokens, "currency": currency}
    with open(PRICE_CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    return get_price_config()


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


# ---------------------------------------------------------------------
# ÉVOLUTION DANS LE TEMPS — agrégation journalière pour graphiques.
# ---------------------------------------------------------------------

def get_usage_over_time(days: int = 30) -> list:
    """
    Agrège la consommation de tokens par jour sur les `days` derniers jours.

    Retourne une liste triée chronologiquement :
    [
      {"date": "2026-08-01", "total_tokens": 4512, "by_agent": {"Commercial": 3000, "Orchestrator": 1512, ...}},
      ...
    ]
    Les jours sans aucun appel apparaissent quand même, avec total_tokens=0,
    pour que le graphique n'ait pas de trou dans l'axe des dates.
    """
    from datetime import timedelta

    data = _load()
    today = datetime.now().date()
    start_date = today - timedelta(days=days - 1)

    # Bucket initialisé jour par jour pour garantir un axe continu.
    buckets = {}
    d = start_date
    while d <= today:
        buckets[d.isoformat()] = {"date": d.isoformat(), "total_tokens": 0, "by_agent": {}}
        d += timedelta(days=1)

    for e in data:
        try:
            entry_date = datetime.fromisoformat(e["timestamp"]).date()
        except (ValueError, KeyError):
            continue
        if entry_date < start_date or entry_date > today:
            continue
        key = entry_date.isoformat()
        bucket = buckets[key]
        bucket["total_tokens"] += e["total_tokens"]
        agent = e["agent"]
        bucket["by_agent"][agent] = bucket["by_agent"].get(agent, 0) + e["total_tokens"]

    return [buckets[k] for k in sorted(buckets.keys())]


# ---------------------------------------------------------------------
# COÛT — prix configurable, 0 par défaut (modèle local Qwen = gratuit).
# Passer à un prix > 0 le jour où un modèle payant est utilisé, via la
# variable d'environnement TOKEN_PRICE_PER_1K (en €/$ pour 1000 tokens).
# ---------------------------------------------------------------------

def get_cost_summary(price_per_1k_tokens: float = None) -> dict:
    """
    Convertit l'usage de tokens en coût estimé.

    price_per_1k_tokens: si non fourni, on utilise get_price_config()
    (réglage manuel depuis l'admin, sinon TOKEN_PRICE_PER_1K, sinon 0).
    """
    currency = "€"
    if price_per_1k_tokens is None:
        config = get_price_config()
        price_per_1k_tokens = config["price_per_1k_tokens"]
        currency = config["currency"]

    data = _load()
    now = datetime.now()
    total_tokens = sum(e["total_tokens"] for e in data)

    tokens_this_month = sum(
        e["total_tokens"] for e in data
        if _same_month(e.get("timestamp"), now)
    )

    by_agent_tokens = {}
    for e in data:
        by_agent_tokens[e["agent"]] = by_agent_tokens.get(e["agent"], 0) + e["total_tokens"]

    def to_cost(tokens):
        return round((tokens / 1000) * price_per_1k_tokens, 4)

    return {
        "price_per_1k_tokens": price_per_1k_tokens,
        "currency": currency,
        "is_free": price_per_1k_tokens == 0.0,
        "total_tokens": total_tokens,
        "tokens_this_month": tokens_this_month,
        "total_cost": to_cost(total_tokens),
        "cost_this_month": to_cost(tokens_this_month),
        "by_agent_cost": {agent: to_cost(tok) for agent, tok in by_agent_tokens.items()},
        "by_agent_tokens": by_agent_tokens,
    }


def _same_month(timestamp_str, reference: datetime) -> bool:
    if not timestamp_str:
        return False
    try:
        ts = datetime.fromisoformat(timestamp_str)
    except ValueError:
        return False
    return ts.year == reference.year and ts.month == reference.month