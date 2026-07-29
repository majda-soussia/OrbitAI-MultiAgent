"""
reset_password.py

Dev utility: manually resets a user's password directly in the
database. Not exposed via the API — this is a command-line helper
only, useful for local testing when you forget your test account's
password.

Usage:
    python reset_password.py test@example.com NewPassword123!
"""
import sys
from utils.db import get_connection
from utils.auth import hash_password


def reset_password(email: str, new_password: str):
    password_hash = hash_password(new_password)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s RETURNING id;",
            (password_hash, email),
        )
        result = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    if result:
        print(f"Password updated for {email} (user_id={result['id']}).")
    else:
        print(f"No user found with email {email}.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python reset_password.py <email> <new_password>")
        sys.exit(1)

    reset_password(sys.argv[1], sys.argv[2])