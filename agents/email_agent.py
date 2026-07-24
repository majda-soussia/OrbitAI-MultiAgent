import re

from agents.base_agent import BaseAgent
from agents.google_auth import get_google_credentials
from googleapiclient.discovery import build
import json  

import base64
class EmailAgent(BaseAgent):
    """
    AI agent responsible for retrieving emails from Gmail
    and analyzing them using a Large Language Model.
    """
    model_name = "qwen2.5:7b"
    temperature = 0.0
    max_tokens = 500

    system_prompt = """
You are Orbit AI's Email Analysis Agent.

Analyze the email carefully and return ONLY a valid JSON object.

{
    "sender": "<sender>",
    "subject": "<subject>",
    "category": "Academic | Commercial | Recruitment | Meeting | Notification | Newsletter | Personal | Support | Spam | Other",
    "priority": "High | Medium | Low",
    "requires_reply": true,
    "deadline_detected": true,
    "summary": "<short summary>",
    "action_items": [
        "<action 1>"
    ],
    "suggested_action": "<best next action>"
}

Classification rules:

Academic:
- University emails
- Professors
- Research
- Papers
- Deadlines
- ENSI
- SympactAI

Commercial:
- Sales
- Clients
- Quotations
- Products

Meeting:
- Invitations
- Calendar
- Zoom
- Teams

Recruitment:
- Internship offers, job postings, job alerts, interview scheduling from an EMPLOYER
  to a candidate — i.e. the email is about hiring the recipient for a paid position.

Academic:
- University/professor communications: coding challenges, coursework, research
  activities, calls for papers, academic certifications, deadlines — even if the
  activity mentions "competition" or "challenge". A professor inviting students to
  a coding/research challenge is Academic, NOT Recruitment (no job or salary involved).
Notification:
- Delivery reports
- Google notifications
- GitHub notifications, INCLUDING GitHub repository/collaboration invitations
  ("X invited you to repository Y") — this is a platform notification about code
  collaboration, NOT a job offer, even though it uses the word "invited".
- Any automated platform invite (GitHub, Google Drive, Notion, Figma, etc.) to
  collaborate on a document/project/repo belongs here, not in Recruitment.

Newsletter:
- Marketing
- Promotions

Support:
- Technical issues
- Requests for help

Spam:
- Unwanted advertising
- Suspicious emails

Priority:

High:
- Deadline
- IMPORTANT
- Urgent
- Interview
- Paper submission
- Meeting today

Medium:
- Information requiring attention

Low:
- Congratulations
- Newsletters
- Notifications
- Promotions
CRITICAL: The "category" field MUST be exactly one of these 10 values, character for
character: Academic, Commercial, Recruitment, Meeting, Notification, Newsletter, Personal,
Support, Spam, Other. Never invent a new category (e.g. do NOT use "Event" — an event
announcement belongs to Newsletter or Notification, not a new category).

Return ONLY JSON.
CRITICAL: Always respond with valid JSON only, even if the email is a marketing
email full of links, images, tracking pixels, or boilerplate footer text
(unsubscribe links, social media icons, legal notices, addresses). Never
respond with a plain-text description of the email's links or structure —
extract only what is needed for the JSON fields above and ignore irrelevant
boilerplate. If the email is mostly promotional noise, just classify it as
Newsletter or Commercial with a short summary; do not enumerate its links.
"""

    def get_gmail_service(self, force_login: bool = False, email: str = None):
        creds = get_google_credentials(force_login=force_login, email=email)
        return build("gmail", "v1", credentials=creds)

    def run(self, max_results=5, force_login: bool = False, email: str = None):
        service = self.get_gmail_service(force_login=force_login, email=email)
        emails = self.get_recent_emails(service, max_results)
        return [self.analyze_email(email_data) for email_data in emails]

    def get_recent_emails(self, service, max_results=5):
        """
        Retrieve the most recent emails from Gmail.
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
            body = self.extract_body(msg_data["payload"])

            emails.append({
                "id": msg["id"],
                "sender": sender,
                "subject": subject,
                "body": body,
            })

        return emails
    def search_emails(self, service, query, max_results=5):
        """
        Recherche des emails avec la syntaxe de recherche Gmail native
        Utile pour cibler précisément un email de test plutôt que de se
        limiter aux N derniers emails reçus.
        """
        results = service.users().messages().list(
            userId="me", labelIds=["INBOX"], q=query, maxResults=max_results
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
            body = self.extract_body(msg_data["payload"])

            emails.append({
                "id": msg["id"],
                "sender": sender,
                "subject": subject,
                "body": body,
            })

        return emails
    def extract_body(self, payload):
        """
        Extrait le corps texte d'un email. Descend récursivement dans les
        parts imbriquées (un email peut être multipart/mixed contenant un
        multipart/alternative contenant enfin le text/plain réel — un seul
        niveau de recherche ne suffit pas toujours).
        """
        def _search_parts(parts):
            for part in parts:
                mime_type = part.get("mimeType", "")

                if mime_type == "text/plain":
                    data = part.get("body", {}).get("data")
                    if data:
                        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

                # Descend dans les parts imbriquées (multipart/alternative,
                # multipart/related, etc.)
                nested_parts = part.get("parts")
                if nested_parts:
                    result = _search_parts(nested_parts)
                    if result:
                        return result

            return None

        if "parts" in payload:
            found = _search_parts(payload["parts"])
            if found:
                return found

        data = payload.get("body", {}).get("data")
        if data:
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        # Filet de sécurité final : garantit TOUJOURS une chaîne, jamais
        # None, peu importe la structure MIME rencontrée (ex: email sans
        # corps texte, uniquement une pièce jointe).
        return ""
    @staticmethod
    def _clean_email_body(body: str, max_chars: int = 1500) -> str:
        # Filet de sécurité : garantit une chaîne même si `body` arrive
        # à None ou tout autre type inattendu, plutôt que de planter.
        if not isinstance(body, str):
            body = ""

        text = re.sub(r'[ \t]+', ' ', body)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remplace les longues URLs de tracking (souvent 100+ caractères)
        # par un placeholder court — elles n'apportent rien au résumé.
        text = re.sub(r'https?://\S{40,}', '[link]', text)

        text = text.strip()

        # Tronque : au-delà d'un certain volume, c'est presque toujours
        # du pied de page (désabonnement, adresse, mentions légales).
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...[truncated]"

        return text

    ALLOWED_CATEGORIES = {
        "Academic", "Commercial", "Recruitment", "Meeting", "Notification",
        "Newsletter", "Personal", "Support", "Spam", "Other",
    }
    ALLOWED_PRIORITIES = {"High", "Medium", "Low"}

    def analyze_email(self, email: dict) -> dict:
        clean_body = self._clean_email_body(email["body"])

        user_content = f"""
            Analyze this email.

            Sender:
            {email['sender']}

            Subject:
            {email['subject']}

            Body:
            {clean_body}
"""

        raw_text = self.call_llm(user_content)

        fallback = {
                "sender": email["sender"],
                "subject": email["subject"],
                "category": "Other",
                "priority": "Medium",
                "requires_reply": False,
                "deadline_detected": False,
                "summary": "Unable to analyze the email.",
                "action_items": [],
                "suggested_action": "Review manually."
            }

        result = self.parse_json_response(raw_text, fallback)

        # Validation post-génération : le LLM peut inventer une catégorie
        # ou priorité hors de la liste autorisée (ex: "Event" au lieu de
        # "Meeting"/"Other"). On ne fait jamais confiance aveuglément à un
        # champ censé être une énumération fermée — on le corrige ici,
        # une seule fois, plutôt que de laisser une valeur invalide se
        # propager dans tout le reste du pipeline (Reply Agent, Orchestrator...).
        if result.get("category") not in self.ALLOWED_CATEGORIES:
            result["category"] = "Other"

        if result.get("priority") not in self.ALLOWED_PRIORITIES:
            result["priority"] = "Medium"

        return result

    def run(self, max_results=5, force_login: bool = False):
        service = self.get_gmail_service(force_login=force_login)
        emails = self.get_recent_emails(service, max_results)
        return [self.analyze_email(email) for email in emails]


if __name__ == "__main__":
    agent = EmailAgent()
    results = agent.run(max_results=10, force_login=True) 

    for result in results:
        # On sépare le debug (_raw_model_output) du résultat propre affiché.
        # Le champ reste dans `result` si vous voulez le logger ailleurs,
        # mais on ne pollue pas l'affichage standard avec.
        display_result = {k: v for k, v in result.items() if not k.startswith("_")}

        print(json.dumps(display_result, indent=2, ensure_ascii=False))

        if "_raw_model_output" in result:
            print("[DEBUG] Parsing JSON a échoué pour cet email — fallback utilisé.")

        print("-" * 50)