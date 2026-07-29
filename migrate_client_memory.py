"""
migrate_client_memory.py

One-shot script: imports the existing data/client_memory.json file
into PostgreSQL (users + conversation_history + token_usage).

Run once with: python migrate_client_memory.py

IMPORTANT: existing clients migrated this way have NO usable password
yet (they came from the public chat, never signed up). They are
created with email_verified=false and a random, unknown password hash.
They will not be able to log in until a "forgot password" flow is
added, or until an admin resets their password manually.
"""
import json
import os
import secrets

from utils.db import get_connection
from utils.auth import hash_password

MEMORY_FILE = "data/client_memory.json"
PLANS_FILE = "config/plans.json"


def load_plans():
    try:
        with open(PLANS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError, FileNotFoundError):
        return {"standard": {"token_limit": 5000}, "premium": {"token_limit": 50000}}


def main():
    if not os.path.exists(MEMORY_FILE):
        print(f"No file found at {MEMORY_FILE}. Nothing to migrate.")
        return

    with open(MEMORY_FILE, "r", encoding="utf-8") as f:
        clients = json.load(f)

    plans = load_plans()
    conn = get_connection()
    cur = conn.cursor()

    for email, profile in clients.items():
        plan_name = profile.get("plan", "standard")
        token_limit = plans.get(plan_name, {}).get("token_limit", 5000)

        cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
        existing = cur.fetchone()

        if existing:
            print(f"[skip] {email} already exists (id={existing['id']}).")
            user_id = existing["id"]
        else:
            # Random, unusable password — this account cannot log in
            # until a password-reset flow is used.
            placeholder_password = secrets.token_urlsafe(32)
            password_hash = hash_password(placeholder_password)

            cur.execute(
                """
                INSERT INTO users (email, password_hash, plan, token_limit, email_verified)
                VALUES (%s, %s, %s, %s, false)
                RETURNING id;
                """,
                (email, password_hash, plan_name, token_limit),
            )
            user_id = cur.fetchone()["id"]
            print(f"[created] {email} -> user_id={user_id} (plan={plan_name}, limit={token_limit})")

        # Migrate conversation history
        history = profile.get("history", [])
        cur.execute("SELECT COUNT(*) AS count FROM conversation_history WHERE user_id = %s;", (user_id,))
        already_migrated = cur.fetchone()["count"] > 0

        if already_migrated:
            print(f"  -> conversation_history already populated for {email}, skipping history import.")
        else:
            for turn in history:
                cur.execute(
                    """
                    INSERT INTO conversation_history (user_id, role, content, agent_name)
                    VALUES (%s, %s, %s, 'Commercial');
                    """,
                    (user_id, turn["role"], turn["content"]),
                )
            print(f"  -> imported {len(history)} message(s) into conversation_history.")

        # Migrate tokens_used as a single token_usage row (best effort;
        # the original JSON only stored a running total, not per-call detail)
        tokens_used = profile.get("tokens_used", 0)
        if tokens_used:
            cur.execute(
                "SELECT COALESCE(SUM(total_tokens), 0) AS total FROM token_usage WHERE user_id = %s;",
                (user_id,),
            )
            already_has_tokens = cur.fetchone()["total"] > 0

            if already_has_tokens:
                print(f"  -> token_usage already populated for {email}, skipping.")
            else:
                cur.execute(
                    """
                    INSERT INTO token_usage (user_id, agent_name, prompt_tokens, response_tokens, total_tokens)
                    VALUES (%s, 'Commercial', 0, %s, %s);
                    """,
                    (user_id, tokens_used, tokens_used),
                )
                print(f"  -> imported {tokens_used} tokens_used as a single token_usage row.")

    conn.commit()
    cur.close()
    conn.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    main()