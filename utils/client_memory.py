import json
import os
from utils.db import get_connection

PLANS_FILE = "config/plans.json"


def _load_plans() -> dict:
    try:
        with open(PLANS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return {"standard": {"token_limit": 5000}, "premium": {"token_limit": 50000}}


def _get_user_by_email(cur, email: str):
    cur.execute(
        "SELECT id, plan, token_limit, created_at, memory_enabled, quota_reset_at FROM users WHERE email = %s;",
        (email,),
    )
    return cur.fetchone()


def get_client_memory(client_id: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        user = _get_user_by_email(cur, client_id)

        if not user:
            return {
                "history": [], "plan": "standard", "first_seen": None,
                "last_seen": None, "memory_enabled": True,
            }

        memory_enabled = user["memory_enabled"] if user["memory_enabled"] is not None else True

        # Client a désactivé la mémorisation persistante : chaque nouvelle
        # session repart de zéro, même si d'anciens échanges existent
        # encore en base (ils ne sont juste plus rechargés).
        if not memory_enabled:
            return {
                "history": [], "plan": user["plan"], "first_seen": None,
                "last_seen": None, "memory_enabled": False,
            }

        cur.execute(
            """
            SELECT role, content, created_at
            FROM conversation_history
            WHERE user_id = %s
            ORDER BY created_at ASC
            LIMIT 20;
            """,
            (user["id"],),
        )
        rows = cur.fetchall()
        history = [{"role": r["role"], "content": r["content"]} for r in rows]
        last_seen = rows[-1]["created_at"].isoformat() if rows else None

        return {
            "history": history,
            "plan": user["plan"],
            "first_seen": user["created_at"].isoformat() if user["created_at"] else None,
            "last_seen": last_seen,
            "memory_enabled": True,
        }
    finally:
        cur.close()
        conn.close()

def save_client_turn(client_id: str, user_message: str, assistant_response: str):
    conn = get_connection()
    try:
        cur = conn.cursor()
        user = _get_user_by_email(cur, client_id)

        if not user:
            raise ValueError(
                f"No user found with email {client_id}. "
                f"The user must sign up (and verify their email) before chatting."
            )
        memory_enabled = user["memory_enabled"] if user["memory_enabled"] is not None else True
        if not memory_enabled:
            return

        cur.execute(
            """
            INSERT INTO conversation_history (user_id, role, content, agent_name)
            VALUES (%s, 'user', %s, 'Commercial'), (%s, 'assistant', %s, 'Commercial');
            """,
            (user["id"], user_message, user["id"], assistant_response),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
def clear_client_history(client_id: str) -> None:
    """Efface définitivement l'historique de conversation persistant d'un
    client (bouton 'Nouvelle conversation'). Ne touche ni au plan, ni aux
    tokens consommés, ni au compte lui-même — uniquement conversation_history."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        user = _get_user_by_email(cur, client_id)
        if not user:
            return
        cur.execute("DELETE FROM conversation_history WHERE user_id = %s;", (user["id"],))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_memory_enabled(client_id: str) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT memory_enabled FROM users WHERE email = %s;", (client_id,))
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row or row["memory_enabled"] is None:
        return True
    return bool(row["memory_enabled"])


def set_memory_enabled(client_id: str, enabled: bool) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET memory_enabled = %s WHERE email = %s;",
            (enabled, client_id),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
def set_client_plan(client_id: str, plan: str):
    """Change a client's plan: 'standard' or 'premium'."""
    plans = _load_plans()
    token_limit = plans.get(plan, {}).get("token_limit", 5000)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET plan = %s, token_limit = %s WHERE email = %s;",
            (plan, token_limit, client_id),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_all_clients() -> dict:
    """
    Returns the same shape as before: { email: {plan, tokens_used, ...} }.
    tokens_used est maintenant calculé directement depuis token_usage,
    filtré par quota_reset_at (voir reset_client_quota) — client_token_summary
    n'a aucune notion de reset, donc on ne peut plus s'appuyer dessus ici.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                u.email, u.plan, u.token_limit, u.quota_reset_at,
                COALESCE((
                    SELECT SUM(tu.total_tokens) FROM token_usage tu
                    WHERE tu.user_id = u.id
                      AND tu.created_at > COALESCE(u.quota_reset_at, '-infinity'::timestamptz)
                ), 0) AS tokens_used,
                (
                    SELECT MAX(ch.created_at)
                    FROM conversation_history ch
                    WHERE ch.user_id = u.id
                ) AS last_seen
            FROM users u;
            """
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    result = {}
    for row in rows:
        result[row["email"]] = {
            "plan": row["plan"],
            "tokens_used": row["tokens_used"],
            "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
        }
    return result


def add_client_tokens(client_id: str, tokens_used: int):

    conn = get_connection()
    try:
        cur = conn.cursor()
        user = _get_user_by_email(cur, client_id)

        if not user:
            raise ValueError(f"No user found with email {client_id}.")

        cur.execute(
            """
            INSERT INTO token_usage (user_id, agent_name, prompt_tokens, response_tokens, total_tokens)
            VALUES (%s, 'Commercial', 0, %s, %s);
            """,
            (user["id"], tokens_used, tokens_used),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

def get_usage_by_user_agent() -> dict:
    """
    { "client@example.com": {"Commercial": 1234, "Email": 567, ...}, ... }
    Source unique de vérité maintenant : PostgreSQL token_usage, alimenté
    par TOUS les agents (plus seulement Commercial).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT u.email, tu.agent_name, SUM(tu.total_tokens) AS total_tokens
            FROM token_usage tu
            JOIN users u ON u.id = tu.user_id
            GROUP BY u.email, tu.agent_name
            ORDER BY u.email, tu.agent_name;
            """
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    result: dict[str, dict[str, int]] = {}
    for r in rows:
        result.setdefault(r["email"], {})[r["agent_name"]] = r["total_tokens"]
    return result
def check_quota(client_id: str) -> dict:
    """
    Returns the quota status for this client:
    {
        "allowed": True/False,
        "plan": "standard"/"premium",
        "tokens_used": 1234,
        "token_limit": 5000,
        "remaining": 3766
    }

    Interroge désormais token_usage DIRECTEMENT (plus client_token_summary),
    filtré sur created_at > quota_reset_at — ce qui permet à
    reset_client_quota() de "repartir à zéro" sans effacer l'historique
    réel d'usage, qui reste consultable ailleurs (get_usage_by_user_agent,
    get_client_detail) pour le diagnostic admin.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, plan, token_limit, quota_reset_at FROM users WHERE email = %s;",
            (client_id,),
        )
        user = cur.fetchone()

        if not user:
            # Unknown user: default to standard limits, 0 used (mirrors the
            # old JSON behavior for a client_id never seen before).
            plans = _load_plans()
            token_limit = plans.get("standard", {}).get("token_limit", 5000)
            return {
                "allowed": True,
                "plan": "standard",
                "tokens_used": 0,
                "token_limit": token_limit,
                "remaining": token_limit,
            }

        cur.execute(
            """
            SELECT COALESCE(SUM(total_tokens), 0) AS tokens_used
            FROM token_usage
            WHERE user_id = %s
              AND created_at > COALESCE(%s, '-infinity'::timestamptz);
            """,
            (user["id"], user["quota_reset_at"]),
        )
        usage_row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    token_limit = user["token_limit"]
    tokens_used = usage_row["tokens_used"]
    remaining = max(0, token_limit - tokens_used)

    return {
        "allowed": tokens_used < token_limit,
        "plan": user["plan"],
        "tokens_used": tokens_used,
        "token_limit": token_limit,
        "remaining": remaining,
    }


def reset_client_quota(client_id: str) -> None:
    """
    Réinitialise le compteur de tokens d'un client à partir de MAINTENANT
    — pour un client bloqué qui a dépassé sa limite et doit pouvoir
    continuer à utiliser le service (renouvellement manuel, geste
    commercial, nouveau cycle mensuel...).

    N'efface RIEN dans token_usage : tout l'historique réel d'usage reste
    intact et consultable (get_usage_by_user_agent, get_client_detail)
    pour le diagnostic admin — seul le SEUIL utilisé par check_quota()
    pour calculer "tokens_used" avance à maintenant.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET quota_reset_at = now() WHERE email = %s;",
            (client_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()
def upsert_client_profile(user_id: int, industry_type: str = None, machine_count: int = None) -> None:
    """Met à jour uniquement les champs non-None détectés dans ce tour —
    ne jamais écraser une valeur déjà connue par un None si ce tour-ci
    ne mentionne pas ce détail."""
    if industry_type is None and machine_count is None:
        return

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO client_profile (user_id, industry_type, machine_count, updated_at)
            VALUES (%s, %s, %s, now())
            ON CONFLICT (user_id) DO UPDATE SET
                industry_type = COALESCE(EXCLUDED.industry_type, client_profile.industry_type),
                machine_count = COALESCE(EXCLUDED.machine_count, client_profile.machine_count),
                updated_at = now();
            """,
            (user_id, industry_type, machine_count),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_all_client_profiles() -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT u.email, p.industry_type, p.machine_count, p.updated_at
            FROM client_profile p
            JOIN users u ON u.id = p.user_id;
            """
        )
        rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    return {
        r["email"]: {
            "industry_type": r["industry_type"],
            "machine_count": r["machine_count"],
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        }
        for r in rows
    }
def get_client_detail(email: str) -> dict | None:
    """Agrégation complète pour le ClientDrawer admin : compte, plan/quota,
    profil (industry/machine_count), et usage par agent (calls, total
    tokens, moyenne/appel) — en un seul aller-retour DB pour que le Drawer
    n'ait pas besoin de plusieurs appels séquentiels quand on clique une
    ligne du tableau."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                u.id, u.plan, u.token_limit, u.created_at, u.memory_enabled, u.quota_reset_at,
                p.industry_type, p.machine_count, p.updated_at AS profile_updated_at,
                (SELECT COUNT(*) FROM conversation_history ch WHERE ch.user_id = u.id) AS conversation_count,
                (SELECT MAX(ch.created_at) FROM conversation_history ch WHERE ch.user_id = u.id) AS last_seen,
                COALESCE((
                    SELECT SUM(tu.total_tokens) FROM token_usage tu
                    WHERE tu.user_id = u.id
                      AND tu.created_at > COALESCE(u.quota_reset_at, '-infinity'::timestamptz)
                ), 0) AS tokens_used
            FROM users u
            LEFT JOIN client_profile p ON p.user_id = u.id
            WHERE u.email = %s;
            """,
            (email,),
        )
        row = cur.fetchone()
        if not row:
            return None

        cur.execute(
            """
            SELECT agent_name, COUNT(*) AS calls, SUM(total_tokens) AS total_tokens
            FROM token_usage
            WHERE user_id = %s
            GROUP BY agent_name;
            """,
            (row["id"],),
        )
        usage_rows = cur.fetchall()
    finally:
        cur.close()
        conn.close()

    usage_by_agent = {}
    for u in usage_rows:
        calls = u["calls"]
        total = u["total_tokens"] or 0
        usage_by_agent[u["agent_name"]] = {
            "calls": calls,
            "total_tokens": total,
            "avg_tokens": round(total / calls) if calls else 0,
        }

    token_limit = row["token_limit"]
    tokens_used = row["tokens_used"] or 0

    return {
        "user_id": row["id"],
        "email": email,
        "plan": row["plan"],
        "token_limit": token_limit,
        "tokens_used": tokens_used,
        "remaining": max(0, token_limit - tokens_used),
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None,
        "memory_enabled": row["memory_enabled"] if row["memory_enabled"] is not None else True,
        "quota_reset_at": row["quota_reset_at"].isoformat() if row["quota_reset_at"] else None,
        "profile": {
            "industry_type": row["industry_type"],
            "machine_count": row["machine_count"],
            "updated_at": row["profile_updated_at"].isoformat() if row["profile_updated_at"] else None,
        },
        "conversation_count": row["conversation_count"] or 0,
        "usage_by_agent": usage_by_agent,
    }