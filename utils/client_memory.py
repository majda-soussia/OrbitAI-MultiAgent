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
        "SELECT id, plan, token_limit, created_at, memory_enabled FROM users WHERE email = %s;",
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
    Returns the same shape as before: { email: {plan, tokens_used, ...} },
    but sourced from client_token_summary + last activity from
    conversation_history.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                s.email,
                s.plan,
                s.token_limit,
                s.tokens_used,
                (
                    SELECT MAX(ch.created_at)
                    FROM conversation_history ch
                    WHERE ch.user_id = s.id
                ) AS last_seen
            FROM client_token_summary s;
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
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT plan, token_limit, tokens_used FROM client_token_summary WHERE email = %s;",
            (client_id,),
        )
        row = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not row:
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

    token_limit = row["token_limit"]
    tokens_used = row["tokens_used"]
    remaining = max(0, token_limit - tokens_used)

    return {
        "allowed": tokens_used < token_limit,
        "plan": row["plan"],
        "tokens_used": tokens_used,
        "token_limit": token_limit,
        "remaining": remaining,
    }