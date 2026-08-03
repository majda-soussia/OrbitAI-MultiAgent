from utils.db import get_connection


def get_or_create_db_session(user_id: int) -> str:
    """
    Retourne l'id (str) d'une session active existante pour cet utilisateur
    si elle existe, sinon en crée une nouvelle. Met à jour last_active_at
    dans les deux cas pour refléter l'activité récente.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id FROM sessions
            WHERE user_id = %s AND ended_at IS NULL
            ORDER BY last_active_at DESC
            LIMIT 1;
            """,
            (user_id,),
        )
        row = cur.fetchone()

        if row:
            cur.execute(
                "UPDATE sessions SET last_active_at = now() WHERE id = %s;",
                (row["id"],),
            )
            conn.commit()
            return str(row["id"])

        cur.execute(
            """
            INSERT INTO sessions (user_id, started_at, last_active_at)
            VALUES (%s, now(), now())
            RETURNING id;
            """,
            (user_id,),
        )
        new_row = cur.fetchone()
        conn.commit()
        return str(new_row["id"])
    finally:
        cur.close()
        conn.close()


def end_session(session_id: str) -> None:
    """Marque une session comme terminée (ex: appelée au logout). Optionnel
    pour l'instant, mais prêt à l'emploi si vous voulez fermer proprement
    une session au lieu de la laisser 'active' indéfiniment."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE sessions SET ended_at = now() WHERE id = %s AND ended_at IS NULL;",
            (session_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()