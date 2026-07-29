"""
Quick manual test script for the auth flow.
Run with: python test_auth_flow.py
"""
from utils.db import get_connection
from utils.auth import verify_email, login, AuthError

EMAIL = "test@example.com"
PASSWORD = "MyPassword123!"

conn = get_connection()
cur = conn.cursor()
cur.execute("SELECT verification_token, email_verified FROM users WHERE email = %s;", (EMAIL,))
row = cur.fetchone()
cur.close()
conn.close()

if row is None:
    print(f"No user found with email {EMAIL}. Run the signup command first.")
else:
    print(f"Current state: email_verified={row['email_verified']}, token={row['verification_token']}")

    if not row["email_verified"] and row["verification_token"]:
        result = verify_email(row["verification_token"])
        print("verify_email() result:", result)
    else:
        print("Already verified, skipping verify_email().")

    print("\n--- Testing correct login ---")
    try:
        login_result = login(EMAIL, PASSWORD)
        print("Login OK. Access token (first 40 chars):", login_result["access_token"][:40], "...")
        print("User info:", login_result["user"])
    except AuthError as e:
        print("Login failed:", e)

    print("\n--- Testing wrong password (should fail gracefully) ---")
    try:
        login(EMAIL, "WrongPassword")
        print("UNEXPECTED: login succeeded with wrong password!")
    except AuthError as e:
        print("Correctly rejected:", e)