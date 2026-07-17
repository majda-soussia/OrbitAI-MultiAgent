from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import os

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

TOKEN_FILE = "config/token.json"
CLIENT_SECRET = "config/client_secret.json"


def get_google_credentials(force_login: bool = False):
    creds = None

    print(f"[DEBUG] cwd = {os.getcwd()}")
    print(f"[DEBUG] TOKEN_FILE resolved path = {os.path.abspath(TOKEN_FILE)}")
    print(f"[DEBUG] CLIENT_SECRET resolved path = {os.path.abspath(CLIENT_SECRET)}")
    print(f"[DEBUG] force_login = {force_login}")
    print(f"[DEBUG] TOKEN_FILE exists before = {os.path.exists(TOKEN_FILE)}")

    if force_login and os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print(f"[DEBUG] TOKEN_FILE removed = {not os.path.exists(TOKEN_FILE)}")

    if not force_login and os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        print("[DEBUG] Loaded creds from existing token file")

    if creds and creds.expired and creds.refresh_token:
        print("[DEBUG] Refreshing expired token")
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    if not creds or not creds.valid:
        print("[DEBUG] No valid creds in memory -> triggering browser login flow now")
        if not os.path.exists(CLIENT_SECRET):
            raise FileNotFoundError(
                f"CLIENT_SECRET introuvable à {os.path.abspath(CLIENT_SECRET)} "
                f"— vérifiez que vous lancez le script depuis la racine du projet."
            )
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET,
            SCOPES
        )
        creds = flow.run_local_server(port=0, prompt="select_account consent")
        print("[DEBUG] Browser flow completed, writing new token")

        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
    else:
        print("[DEBUG] Skipped browser flow — creds were already valid")

    return creds