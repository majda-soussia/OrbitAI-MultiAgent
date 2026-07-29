"""
Centralized PostgreSQL connection. All other modules (auth.py,
token_tracker.py, migrated client_memory.py...) should go through
get_connection() rather than opening their own connection, to keep
a single point of configuration.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "orbit_ai")
DB_USER = os.environ.get("DB_USER", "orbit_app")
DB_PASSWORD = os.environ.get("DB_PASSWORD")

if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is missing. Make sure a .env file exists at the "
        "project root and contains DB_PASSWORD=..."
    )


def get_connection():
    """
    Returns a new psycopg2 connection, using RealDictCursor by default
    (rows are returned as dicts instead of positional tuples — easier
    to read and less fragile if column order changes).
    """
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        cursor_factory=RealDictCursor,
    )


if __name__ == "__main__":
    # Quick connection test: python -m utils.db
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) AS count FROM users;")
        result = cur.fetchone()
        print(f"Connection OK. Current number of users: {result['count']}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Connection error: {e}")