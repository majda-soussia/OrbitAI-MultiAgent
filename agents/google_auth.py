from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from utils.settings import is_debug_enabled
import os
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

TOKENS_DIR = "config/tokens"
CLIENT_SECRET = "config/client_secret.json"


def _token_path(email: str) -> str:
    safe = email.replace("/", "_").replace("\\", "_")
    return os.path.join(TOKENS_DIR, f"{safe}.json")


def _debug_print(message: str):
    if is_debug_enabled():
        print(f"[DEBUG] {message}")


def get_google_credentials(force_login: bool = False, email: str = None):
    """
    Retourne les credentials Google pour un email donné.
    Si email=None, utilise le token par défaut (config/tokens/default.json)
    pour la compatibilité avec les agents qui ne connaissent pas encore
    l'email de l'utilisateur (ex: appel CLI direct).
    """
    os.makedirs(TOKENS_DIR, exist_ok=True)

    token_file = _token_path(email) if email else os.path.join(TOKENS_DIR, "default.json")

    # Migration : si l'ancien token.json existe encore, on le déplace
    # vers le nouveau dossier comme token par défaut.
    legacy_token = "config/token.json"
    if os.path.exists(legacy_token) and not os.path.exists(token_file):
        import shutil
        shutil.copy(legacy_token, token_file)
        _debug_print(f"Migrated legacy token to {token_file}")

    creds = None

    _debug_print(f"cwd = {os.getcwd()}")
    _debug_print(f"TOKEN_FILE resolved path = {os.path.abspath(token_file)}")
    _debug_print(f"CLIENT_SECRET resolved path = {os.path.abspath(CLIENT_SECRET)}")
    _debug_print(f"force_login = {force_login}, email = {email}")
    _debug_print(f"TOKEN_FILE exists before = {os.path.exists(token_file)}")

    if force_login and os.path.exists(token_file):
        os.remove(token_file)
        _debug_print(f"TOKEN_FILE removed")

    if not force_login and os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)
        _debug_print("Loaded creds from existing token file")

    if creds and creds.expired and creds.refresh_token:
        _debug_print("Refreshing expired token")
        try:
            creds.refresh(Request())
            with open(token_file, "w") as f:
                f.write(creds.to_json())
        except RefreshError:
            _debug_print("Refresh token invalide/révoqué — nouvelle auth requise")
            creds = None
            if os.path.exists(token_file):
                os.remove(token_file)

    if not creds or not creds.valid:
        _debug_print("No valid creds → triggering browser login flow")
        if not os.path.exists(CLIENT_SECRET):
            raise FileNotFoundError(
                f"CLIENT_SECRET introuvable à {os.path.abspath(CLIENT_SECRET)}"
            )
        flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET, SCOPES)
        creds = flow.run_local_server(port=0, prompt="select_account consent")
        _debug_print("Browser flow completed, writing new token")
        with open(token_file, "w") as f:
            f.write(creds.to_json())
    else:
        _debug_print("Skipped browser flow — creds already valid")

    return creds