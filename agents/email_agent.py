import re

from agents.base_agent import BaseAgent
from agents.google_auth import get_google_credentials
from utils.google_oauth import get_credentials_for_user
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
- Emails from or about a specific human prospect/client discussing OUR business
  (quotation requests, sales conversations, contract questions, client meetings).
- NEVER automated marketing/promotional emails, even if they mention products,
  subscriptions, or discounts — those always belong to Newsletter instead.

Newsletter:
- ANY automated marketing or promotional email: platform recommendations
  (Pinterest, Udemy, Canva, etc.), tech/industry newsletters, subscription
  offers, discount campaigns. If the sender is a mass-mailing platform and
  the email pushes content/offers rather than addressing you personally
  about a specific business need, it is Newsletter — even if "product" or
  "offer" appears in the text.

DISAMBIGUATION RULE: if you hesitate between Commercial and Newsletter, ask
"is this a mass-sent automated email, or a personal/business conversation
about our company?" Mass-sent → Newsletter. Personal/business → Commercial.

EXPLICIT EXAMPLES (do not deviate from these):
- Udemy/Coursera/LinkedIn Learning subscription or course promotion email →
  Newsletter (NOT Commercial), even if it mentions "subscription", "discount",
  "save money", or "boost your career". This is a mass marketing email from
  a learning platform, not a business inquiry about Orbit.
- A prospect asking "what's your pricing for 50 meters?" → Commercial.
- A platform (Udemy, Canva, Notion, Adobe, etc.) advertising ITS OWN paid
  plans or features to you → always Newsletter, regardless of pricing
  language in the email.
Meeting:
- Any email containing a specific, attendable event: a date/time AND a
  join link or location (Zoom, Teams, Google Meet, in-person address).
- This applies EVEN IF the email is templated or sent to many recipients
  (e.g. a networking event invite, a webinar you registered for, a workshop
  confirmation). Mass-sent does NOT disqualify Meeting — what matters is
  whether there is a concrete, joinable event with a date/time.
- Only classify as Notification instead if there is NO specific date/time
  or NO way to join/attend (e.g. a generic "check out our events page" link).

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
- Platform activity alerts with NO specific attendable event (e.g. "new post
  from X", "new skill available", "your item shipped"). If a concrete date/
  time + join link/location is present, it belongs to Meeting instead, not
  Notification, even if it's otherwise a platform-style notification.
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
        """
        Legacy path: local single-user desktop OAuth flow (config/tokens/*.json).
        Kept for CLI/dev usage — unchanged.
        """
        creds = get_google_credentials(force_login=force_login, email=email)
        return build("gmail", "v1", credentials=creds)

    def get_gmail_service_for_user(self, user_id: int):
        """
        New path: per-user web OAuth flow, credentials loaded from
        PostgreSQL (oauth_credentials table), refreshed automatically
        if expired. Used when this agent is invoked from the API on
        behalf of a real signed-up user.
        """
        creds = get_credentials_for_user(user_id)
        return build("gmail", "v1", credentials=creds)

    def run(self, max_results=5, force_login: bool = False, email: str = None, query: str = None):
        """Legacy entry point — unchanged, still used for CLI/dev testing."""
        service = self.get_gmail_service(force_login=force_login, email=email)

        if query:
            emails = self.search_emails(service, query, max_results)
        else:
            emails = self.get_recent_emails(service, max_results)

        return [self.analyze_email(email_data) for email_data in emails]

    def run_for_user(self, user_id: int, max_results=5, query: str = None):
        """
        New entry point for the API: analyzes the given user's own
        Gmail inbox, using their own connected Google account.
        """
        service = self.get_gmail_service_for_user(user_id)

        if query:
            emails = self.search_emails(service, query, max_results)
        else:
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
        for msg in messages:
            print(f"[DEBUG] message id: {msg['id']}")
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