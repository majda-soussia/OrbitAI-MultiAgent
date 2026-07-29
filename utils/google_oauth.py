"""
utils/google_oauth.py

Per-user Google OAuth flow (web application type), separate from the
existing desktop-app flow used by agents/google_auth.py for local
single-user scripts.

Responsibilities:
- Build the Google authorization URL for a given app user_id
- Exchange the authorization code for access/refresh tokens
- Encrypt tokens before storing them in oauth_credentials
- Load and decrypt a user's credentials, refreshing them if expired
"""
import os
import json
import secrets
from datetime import datetime, timezone

from cryptography.fernet import Fernet
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from jose import jwt, JWTError
from dotenv import load_dotenv

from utils.db import get_connection

load_dotenv()

GOOGLE_WEB_CLIENT_ID = os.environ["GOOGLE_WEB_CLIENT_ID"]
GOOGLE_WEB_CLIENT_SECRET = os.environ["GOOGLE_WEB_CLIENT_SECRET"]
GOOGLE_OAUTH_REDIRECT_URI = os.environ["GOOGLE_OAUTH_REDIRECT_URI"]

OAUTH_ENCRYPTION_KEY = os.environ["OAUTH_ENCRYPTION_KEY"]
_fernet = Fernet(OAUTH_ENCRYPTION_KEY.encode())

# Same JWT secret as utils/auth.py — reused here only to sign/verify the
# short-lived OAuth "state" parameter, not to issue login sessions.
STATE_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
STATE_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

_CLIENT_CONFIG = {
    "web": {
        "client_id": GOOGLE_WEB_CLIENT_ID,
        "client_secret": GOOGLE_WEB_CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [GOOGLE_OAUTH_REDIRECT_URI],
    }
}


class GoogleOAuthError(Exception):
    pass


def _encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def _decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode()).decode()


def _make_state(user_id: int, code_verifier: str) -> str:
    """
    Short-lived signed token binding this OAuth flow to a specific
    app user. Prevents an attacker from tricking a victim into linking
    the attacker's Google account to the victim's session (CSRF-style
    attack on the OAuth callback).

    Also carries the PKCE code_verifier: Google enables PKCE on this
    client, which means the code_verifier generated when building the
    authorization URL MUST be presented again when exchanging the code
    for tokens. Since build_authorization_url() and
    exchange_code_for_tokens() run in separate HTTP requests (and
    possibly separate worker processes), the verifier can't just be
    kept as an in-memory attribute on a Flow object — it has to travel
    with the request. The signed state is the natural place for that.
    """
    payload = {
        "user_id": user_id,
        "purpose": "google_oauth_state",
        "code_verifier": code_verifier,
    }
    return jwt.encode(payload, STATE_SECRET_KEY, algorithm=STATE_ALGORITHM)


def _read_state(state: str) -> tuple[int, str]:
    try:
        payload = jwt.decode(state, STATE_SECRET_KEY, algorithms=[STATE_ALGORITHM])
    except JWTError:
        raise GoogleOAuthError("Invalid or expired OAuth state.")

    if payload.get("purpose") != "google_oauth_state":
        raise GoogleOAuthError("Invalid OAuth state payload.")

    return int(payload["user_id"]), payload["code_verifier"]


def build_authorization_url(user_id: int) -> str:
    flow = Flow.from_client_config(
        _CLIENT_CONFIG, scopes=SCOPES, redirect_uri=GOOGLE_OAUTH_REDIRECT_URI
    )

    # Generate our own PKCE verifier explicitly (43-128 chars, url-safe)
    # instead of letting the library auto-generate one we'd have no way
    # to retrieve later from a fresh Flow instance at callback time.
    code_verifier = secrets.token_urlsafe(64)[:128]
    flow.code_verifier = code_verifier

    state = _make_state(user_id, code_verifier)
    auth_url, _ = flow.authorization_url(
        access_type="offline",       # required to receive a refresh_token
        include_granted_scopes="true",
        prompt="consent",            # forces refresh_token on repeat connections too
        state=state,
    )
    return auth_url


def exchange_code_for_tokens(code: str, state: str) -> dict:
    """
    Called from the OAuth callback route. Validates the state, exchanges
    the code for tokens, encrypts them, and upserts them into
    oauth_credentials for the corresponding user.
    """
    user_id, code_verifier = _read_state(state)

    flow = Flow.from_client_config(
        _CLIENT_CONFIG, scopes=SCOPES, redirect_uri=GOOGLE_OAUTH_REDIRECT_URI
    )
    # Must match the verifier used to build the original authorization
    # URL, or Google rejects the exchange with "Missing code verifier"
    # / "invalid_grant".
    flow.code_verifier = code_verifier
    flow.fetch_token(code=code)
    creds = flow.credentials

    if not creds.refresh_token:
        # Google only returns a refresh_token on the FIRST consent, or
        # when prompt=consent forces re-approval (which we do above).
        # If it's still missing, the user likely has a stale grant —
        # ask them to revoke access at myaccount.google.com and retry.
        raise GoogleOAuthError(
            "No refresh token received from Google. Please revoke this "
            "app's access in your Google account settings and try connecting again."
        )

    encrypted_access = _encrypt(creds.token)
    encrypted_refresh = _encrypt(creds.refresh_token)
    expiry = creds.expiry.replace(tzinfo=timezone.utc) if creds.expiry else None

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO oauth_credentials
                (user_id, provider, access_token, refresh_token, token_expiry, scopes)
            VALUES (%s, 'google', %s, %s, %s, %s)
            ON CONFLICT (user_id, provider) DO UPDATE SET
                access_token = EXCLUDED.access_token,
                refresh_token = EXCLUDED.refresh_token,
                token_expiry = EXCLUDED.token_expiry,
                scopes = EXCLUDED.scopes;
            """,
            (user_id, encrypted_access, encrypted_refresh, expiry, SCOPES),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {"user_id": user_id, "message": "Google account connected successfully."}


def get_credentials_for_user(user_id: int) -> Credentials:
    """
    Loads and decrypts this user's Google credentials, refreshing the
    access token if it's expired. The refreshed access token is saved
    back to the database so future calls don't need to hit Google again
    until it expires.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT access_token, refresh_token, token_expiry, scopes "
            "FROM oauth_credentials WHERE user_id = %s AND provider = 'google';",
            (user_id,),
        )
        row = cur.fetchone()

        if not row:
            raise GoogleOAuthError(
                "This user has not connected a Google account yet. "
                "Call /api/oauth/google/connect first."
            )

        creds = Credentials(
            token=_decrypt(row["access_token"]),
            refresh_token=_decrypt(row["refresh_token"]),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_WEB_CLIENT_ID,
            client_secret=GOOGLE_WEB_CLIENT_SECRET,
            scopes=row["scopes"],
        )

        if row["token_expiry"]:
            creds.expiry = row["token_expiry"].replace(tzinfo=None)

        if creds.expired:
            creds.refresh(Request())
            cur.execute(
                "UPDATE oauth_credentials SET access_token = %s, token_expiry = %s "
                "WHERE user_id = %s AND provider = 'google';",
                (_encrypt(creds.token), creds.expiry, user_id),
            )
            conn.commit()
    finally:
        cur.close()
        conn.close()

    return creds


def disconnect_google(user_id: int) -> None:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM oauth_credentials WHERE user_id = %s AND provider = 'google';",
            (user_id,),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def is_google_connected(user_id: int) -> bool:
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM oauth_credentials WHERE user_id = %s AND provider = 'google';",
            (user_id,),
        )
        return cur.fetchone() is not None
    finally:
        cur.close()
        conn.close()