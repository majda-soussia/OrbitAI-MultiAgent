import os
import base64
import json
from email.mime.text import MIMEText

import ollama
import yaml
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail nous autorise seulement à LIRE les emails pour l'instant (lecture seule)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CREDENTIALS_PATH = "../config/credentials.json"
TOKEN_PATH = "../config/token.json"


def get_gmail_service():
    """
    Authentifie l'utilisateur avec Gmail via OAuth2.
    La première fois, ouvre une page web pour autoriser l'accès.
    Les fois suivantes, réutilise le token sauvegardé (token.json).
    """
    creds = None

    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Sauvegarder le token pour les prochaines fois
        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


def get_recent_emails(service, max_results=5):
    """
    Récupère les X emails les plus récents de la boîte de réception.
    """
    results = service.users().messages().list(
        userId="me", labelIds=["INBOX"], maxResults=max_results
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for msg in messages:
        msg_data = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()

        headers = msg_data["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(no subject)")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "(unknown sender)")
        snippet = msg_data.get("snippet", "")

        emails.append({
            "id": msg["id"],
            "sender": sender,
            "subject": subject,
            "snippet": snippet,
        })

    return emails


# Charger la config LLM (Qwen)
with open("config/llm.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

EMAIL_SYSTEM_PROMPT = """You are the Orbit Email Analysis Agent.

Your job is to analyze incoming customer/prospect emails and output ONLY a valid JSON object (no markdown, no explanation, no extra text) with this exact structure:

{
  "sender": "<email sender>",
  "priority": "High" | "Medium" | "Low",
  "category": "Prospect" | "Existing Client" | "Support Request" | "Spam/Irrelevant" | "Other",
  "subject": "<original subject>",
  "summary": "<one sentence summary in English>",
  "suggested_action": "<one short sentence recommending next step>"
}

PRIORITY RULES:
- High: urgent language, angry tone, contract/quotation deadline, system down/critical issue, mentions of large deal size (multiple sites/factories)
- Medium: general inquiry, new prospect interested in Orbit, standard support request
- Low: newsletters, spam, irrelevant content, automated notifications

Only output the JSON object. Nothing else.
"""


def analyze_email(email: dict) -> dict:
    """
    Envoie un email à Qwen pour résumé + détection priorité/catégorie.
    """
    user_content = f"""Sender: {email['sender']}
Subject: {email['subject']}
Content: {email['snippet']}"""

    response = ollama.chat(
        model=config["model"]["name"],
        messages=[
            {"role": "system", "content": EMAIL_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        options={
            "temperature": 0.1,  # Très bas pour des réponses JSON cohérentes
            "num_predict": 500,
        }
    )

    raw_text = response["message"]["content"].strip()

    # Nettoyer si le modèle ajoute des balises markdown ```json ... ```
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
        raw_text = raw_text.replace("json\n", "").replace("json", "", 1)

    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        parsed = {
            "sender": email["sender"],
            "priority": "Medium",
            "category": "Other",
            "subject": email["subject"],
            "summary": "Could not parse email automatically — needs manual review.",
            "suggested_action": "Review manually.",
            "_raw_model_output": raw_text,
        }

    return parsed


if __name__ == "__main__":
    print("Orbit AI Assistant — Email Agent")
    print("=" * 50)
    print("Connecting to Gmail...")

    service = get_gmail_service()
    print("Connected successfully.\n")

    emails = get_recent_emails(service, max_results=5)
    print(f"Found {len(emails)} recent emails.\n")

    results = []
    for i, email in enumerate(emails, 1):
        print(f"Analyzing email {i}/{len(emails)}: {email['subject'][:50]}...")
        analysis = analyze_email(email)
        results.append(analysis)

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    for r in results:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        print("-" * 50)