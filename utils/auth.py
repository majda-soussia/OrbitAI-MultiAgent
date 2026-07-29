"""
Secure authentication for Orbit AI Assistant:
- Password hashing with Argon2 (argon2-cffi)
- Session handling via JWT (short-lived access token + long-lived refresh token)
- Mandatory email verification before account activation
- Verification email sent via SMTP

This module has no dependency on any web framework: main_api.py
(FastAPI) simply calls signup(), login(), verify_email(),
refresh_access_token(), get_current_user() with data received
from the HTTP routes.
"""
import os
import secrets
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import jwt, JWTError
from dotenv import load_dotenv

from utils.db import get_connection

load_dotenv()

JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", 7))

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")

_hasher = PasswordHasher()


# ---------- Business exceptions (lets the API return the right HTTP codes) ----------

class AuthError(Exception):
    """Generic authentication error, with a message safe to return to the client."""
    pass


class EmailAlreadyExists(AuthError):
    pass


class InvalidCredentials(AuthError):
    pass


class EmailNotVerified(AuthError):
    pass


class InvalidToken(AuthError):
    pass


# ---------- Password hashing ----------

def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        _hasher.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


# ---------- JWT ----------

def create_access_token(user_id: int, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "email": email, "type": "access", "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "type": "refresh", "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise InvalidToken("Invalid or expired token.")


# ---------- Verification email ----------

def _send_email(to_email: str, subject: str, body: str) -> None:
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        # In dev without SMTP configured, log instead of failing — useful
        # to test the signup flow without setting up Gmail right away.
        print(f"[DEBUG] SMTP not configured. Email not sent to {to_email}:\n{body}")
        return

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())


def _send_verification_email(email: str, verification_token: str) -> None:
    link = f"{FRONTEND_URL}/verify-email?token={verification_token}"
    body = (
        f"Welcome to Orbit AI Assistant!\n\n"
        f"Click this link to verify your email address:\n{link}\n\n"
        f"This link can only be used once. If you did not request this "
        f"account, you can safely ignore this email."
    )
    _send_email(email, "Verify your email address — Orbit AI Assistant", body)


# ---------- Signup ----------

def signup(email: str, password: str, plan: str = "standard") -> dict:
    """
    Creates a new user. The account is created with email_verified=false;
    the user cannot log in until they click the link received by email
    (see verify_email()).
    """
    email = email.strip().lower()
    if plan not in ("standard", "premium"):
        plan = "standard"

    token_limit = 50000 if plan == "premium" else 5000
    verification_token = secrets.token_urlsafe(32)
    password_hash = hash_password(password)

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s;", (email,))
        if cur.fetchone():
            raise EmailAlreadyExists("An account with this email already exists.")

        cur.execute(
            """
            INSERT INTO users (email, password_hash, plan, token_limit,
                                verification_token, email_verified)
            VALUES (%s, %s, %s, %s, %s, false)
            RETURNING id, email, plan;
            """,
            (email, password_hash, plan, token_limit, verification_token),
        )
        new_user = cur.fetchone()
        conn.commit()
    finally:
        cur.close()
        conn.close()

    _send_verification_email(email, verification_token)

    return {
        "id": new_user["id"],
        "email": new_user["email"],
        "plan": new_user["plan"],
        "message": "Account created. Check your email to activate it.",
    }


def verify_email(token: str) -> dict:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email FROM users WHERE verification_token = %s AND email_verified = false;",
            (token,),
        )
        user = cur.fetchone()
        if not user:
            raise InvalidToken("Invalid, expired, or already used verification link.")

        cur.execute(
            "UPDATE users SET email_verified = true, verification_token = NULL WHERE id = %s;",
            (user["id"],),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {"email": user["email"], "message": "Email verified successfully. You can now log in."}


# ---------- Login ----------

def login(email: str, password: str) -> dict:
    email = email.strip().lower()

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, password_hash, email_verified, plan, is_admin "
            "FROM users WHERE email = %s;",
            (email,),
        )
        user = cur.fetchone()

        # Same error message whether the email exists or not — avoids
        # letting an attacker enumerate which emails are registered.
        if not user or not verify_password(password, user["password_hash"]):
            raise InvalidCredentials("Incorrect email or password.")

        if not user["email_verified"]:
            raise EmailNotVerified("Please verify your email address before logging in.")

        cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s;", (user["id"],))
        conn.commit()
    finally:
        cur.close()
        conn.close()

    access_token = create_access_token(user["id"], user["email"])
    refresh_token = create_refresh_token(user["id"])

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "plan": user["plan"],
            "is_admin": user["is_admin"],
        },
    }


def refresh_access_token(refresh_token: str) -> dict:
    payload = decode_token(refresh_token)
    if payload.get("type") != "refresh":
        raise InvalidToken("This token is not a refresh token.")

    user_id = int(payload["sub"])

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email FROM users WHERE id = %s;", (user_id,))
        user = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not user:
        raise InvalidToken("User not found.")

    new_access_token = create_access_token(user["id"], user["email"])
    return {"access_token": new_access_token, "token_type": "bearer"}


def get_current_user(access_token: str) -> dict:
    """
    Meant to be used in a FastAPI dependency (Depends) to protect
    routes: decodes the token, checks it's actually an access token,
    and returns the current user's info.
    """
    payload = decode_token(access_token)
    if payload.get("type") != "access":
        raise InvalidToken("This token is not an access token.")

    user_id = int(payload["sub"])

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, plan, is_admin FROM users WHERE id = %s;", (user_id,)
        )
        user = cur.fetchone()
    finally:
        cur.close()
        conn.close()

    if not user:
        raise InvalidToken("User not found.")

    return dict(user)


if __name__ == "__main__":
    # Quick manual test: python -m utils.auth
    import sys

    if len(sys.argv) < 2:
        print("Usage: python -m utils.auth signup <email> <password>")
        print("       python -m utils.auth login <email> <password>")
        sys.exit(0)

    action = sys.argv[1]
    if action == "signup":
        print(signup(sys.argv[2], sys.argv[3]))
    elif action == "login":
        try:
            print(login(sys.argv[2], sys.argv[3]))
        except AuthError as e:
            print(f"Error: {e}")