import json
import re
from agents.base_agent import BaseAgent
from agents.email_agent import EmailAgent


# Configuration par persona : quel prompt charger, et quelles catégories
# n'ont jamais besoin de brouillon pour ce persona précis.
# - business : boîte mail professionnelle Orbit (support@orbitsolutions.tn) —
#   Academic/Personal n'ont pas de sens dans ce contexte, on les exclut.
# - personal : boîte mail personnelle de l'utilisateur — Academic/Personal
#   sont au contraire des cas d'usage légitimes, on les autorise.
PERSONA_CONFIG = {
    "business": {
        "prompt_file": "prompts/reply_business.txt",
        "no_reply_categories": {"Newsletter", "Notification", "Spam", "Academic", "Personal"},
    },
    "personal": {
        "prompt_file": "prompts/reply_personal.txt",
        "no_reply_categories": {"Newsletter", "Notification", "Spam"},
    },
}


class ReplyAgent(BaseAgent):
    """
    Rédige des brouillons de réponse email, en s'appuyant sur l'analyse
    produite par l'EmailAgent (catégorie, résumé, action_items).

    Le persona ("business" ou "personal") détermine le ton, la signature,
    et quelles catégories d'emails méritent un brouillon — une boîte pro
    Orbit et une boîte personnelle n'ont pas les mêmes attentes.

    Ne s'envoie jamais tout seul : produit uniquement un brouillon texte,
    la validation/envoi reste une action humaine.
    """

    model_name = "qwen2.5:7b"
    temperature = 0.3
    max_tokens = 400

    def __init__(self, persona: str = "business", config_path="config/llm.yaml"):
        if persona not in PERSONA_CONFIG:
            raise ValueError(f"Persona inconnu : '{persona}'. Choix possibles : {list(PERSONA_CONFIG)}")

        self.persona = persona
        persona_cfg = PERSONA_CONFIG[persona]
        self.no_reply_categories = persona_cfg["no_reply_categories"]

        with open(persona_cfg["prompt_file"], "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        super().__init__(config_path)

    @staticmethod
    def _preview_body(body: str, max_chars: int = 110) -> str:
        if not isinstance(body, str) or not body.strip():
            return "(pas d'aperçu disponible)"

        text = re.sub(r'\s+', ' ', body).strip()
        text = re.sub(r'https?://\S+', '[lien]', text)

        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "..."

        return text
    @staticmethod
    def _dedupe_signoff(text: str) -> str:
        """Filet de sécurité : le modèle produit parfois une signature
        dupliquée (une fois au début par erreur, une fois à la fin comme
        attendu). On ne garde que la dernière occurrence — c'est presque
        toujours la bonne, puisque le corps de l'email doit précéder la
        signature finale."""
        signoff_markers = {"best regards,", "cordialement,", "bien à vous,"}
        lines = text.split("\n")

        signoff_indices = [
            i for i, line in enumerate(lines)
            if line.strip().lower() in signoff_markers
        ]

        if len(signoff_indices) <= 1:
            return text

        to_remove = set()
        for idx in signoff_indices[:-1]:
            to_remove.add(idx)
            if idx + 1 < len(lines):
                to_remove.add(idx + 1)  # la ligne du nom signataire qui suit

        return "\n".join(line for i, line in enumerate(lines) if i not in to_remove).strip()

    def revise_draft(self, previous_draft: str, instruction: str) -> str:
        """Révise un brouillon déjà généré selon une instruction courte
        (raccourcir, reformuler, changer le ton...), sans redemander le
        contexte d'origine — celui-ci est déjà contenu dans previous_draft."""
        user_content = f"""
        Here is a draft email you previously wrote:

        ---
        {previous_draft}
        ---

        The user now wants you to revise it with this instruction:
        "{instruction}"

        Apply the instruction faithfully (e.g. if asked to shorten it, cut
        it down significantly while keeping the essential facts and any
        commitments already made — such as a proposed time or date). Do
        not invent new facts that weren't in the original draft or the
        instruction. Return ONLY the revised email text, nothing else.
        """
        raw_text = self.call_llm(user_content)
        draft = self.clean_text_response(raw_text)
        return self._dedupe_signoff(draft)

    def draft_from_text(self, instruction_and_content: str, force_final: bool = False) -> str:
        force_instruction = ""
        if force_final:
            force_instruction = """
        CRITICAL: You have already asked one clarifying question and the user has replied.
        Do NOT ask another question, no matter what optional details are still missing.
        Draft the best possible complete email NOW using the information given, and if
        something minor is genuinely still unclear, state a reasonable assumption inline
        (e.g. "assuming this will be a virtual call") rather than asking again.
        """

        user_content = f"""
        The user directly provided the following request/content — there is no
        original inbox email to reference here. Draft or improve the email text
        accordingly, following all your usual rules (no invented facts, no
        fabricated commitments, correct sign-off for your persona).
        {force_instruction}
        If the request is too vague or missing key details (e.g. no recipient,
        no clear topic) to draft a complete, sendable email, do NOT include the
        literal words "NO_REPLY_NEEDED" anywhere in your answer — that sentinel
        is reserved for a different context. Instead, just write the clarifying
        question directly as your answer, in plain sentences.

        User request:
        {instruction_and_content}
        """

        raw_text = self.call_llm(user_content)
        draft = self.clean_text_response(raw_text)

        draft = re.sub(r'^NO_REPLY_NEEDED\s*', '', draft, flags=re.IGNORECASE).strip()
        draft = self._dedupe_signoff(draft)

        return draft
    def draft_reply(self, email: dict, analysis: dict) -> str | None:
        category = analysis.get("category", "Other")

        if category in self.no_reply_categories:
            return None

        if not analysis.get("requires_reply", False):
            return None

        # Nettoyage cohérent avec l'EmailAgent, mais limite plus haute :
        # on veut que le LLM voie le contenu structuré complet (ex: les
        # différentes phases d'un projet de stage) pour rédiger une
        # réponse qui engage vraiment avec le contenu, pas juste le sujet.
        clean_body = EmailAgent._clean_email_body(email['body'], max_chars=3000)

        user_content = f"""
        Draft a reply to this email.

        Category: {category}
        Original sender: {email['sender']}
        Original subject: {email['subject']}

        Original email body:
        {clean_body}

        Context from prior analysis:
        Summary: {analysis.get('summary', '')}
        Action items: {', '.join(analysis.get('action_items', [])) or 'none'}
        """

        raw_text = self.call_llm(user_content)
        draft = self.clean_text_response(raw_text)

        if draft.strip() == "NO_REPLY_NEEDED":
            return None

        return draft

    def get_raw_email_list(self, max_results=5, user_id: int = None, force_login: bool = False) -> list:

        email_agent = EmailAgent()
        email_agent.current_user_id = user_id
        if user_id is not None:
            service = email_agent.get_gmail_service_for_user(user_id)
        else:
            service = email_agent.get_gmail_service(force_login=force_login)
        return email_agent.get_recent_emails(service, max_results)

    def search_raw_email_list(self, query: str, max_results=5, user_id: int = None, force_login: bool = False) -> list:
        email_agent = EmailAgent()
        email_agent.current_user_id = user_id
        if user_id is not None:
            service = email_agent.get_gmail_service_for_user(user_id)
        else:
            service = email_agent.get_gmail_service(force_login=force_login)
        return email_agent.search_emails(service, query, max_results)
    def analyze_and_draft(self, email: dict) -> dict:
        email_agent = EmailAgent()
        email_agent.current_user_id = getattr(self, "current_user_id", None)
        analysis = email_agent.analyze_email(email)
        draft = self.draft_reply(email, analysis)

        return {
            "sender": email["sender"],
            "subject": email["subject"],
            "category": analysis.get("category", "Other"),
            "priority": analysis.get("priority", "Medium"),
            "requires_reply": analysis.get("requires_reply", False),
            "draft_reply": draft,
        }


if __name__ == "__main__":
    print("Orbit AI Assistant — Reply Agent")
    print("=" * 50)

    persona_answer = input(
        "Persona à utiliser : (1) business [Orbit Team]  (2) personal [neutre]  [1/2, défaut=1] : "
    ).strip()
    persona = "personal" if persona_answer == "2" else "business"

    agent = ReplyAgent(persona=persona)
    print(f"[Persona actif : {persona}]")

    force_login_answer = input(
        "Choisir/changer de compte Google avant de continuer ? (o/N) : "
    ).strip().lower()
    force_login = force_login_answer in ("o", "oui", "y", "yes")

    search_query = input(
        "Recherche Gmail (ex: 'from:nom@example.com', 'subject:devis', "
        "ou laisser vide pour les 5 derniers emails reçus) : "
    ).strip()

    if search_query:
        emails = agent.search_raw_email_list(search_query, max_results=5, force_login=force_login)
    else:
        emails = agent.get_raw_email_list(max_results=5, force_login=force_login)

    if not emails:
        print("\n[INFO] Aucun email trouvé.")
    else:
        print(f"\n{len(emails)} email(s) trouvé(s) (non analysés) :\n")

        for i, email in enumerate(emails, start=1):
            preview = agent._preview_body(email.get("body", ""))
            print(f"{i}. {email['subject']}  —  {email['sender']}")
            print(f"   › {preview}")

        while True:
            choice = input(
                "\nTaper le numéro de l'email à analyser et pour lequel "
                "générer un brouillon (ou Entrée / 'q' pour quitter) : "
            ).strip()

            if choice == "" or choice.lower() == "q":
                print("\nFin de la session.")
                break

            if not (choice.isdigit() and 1 <= int(choice) <= len(emails)):
                print("Numéro invalide, réessayez.")
                continue

            selected_email = emails[int(choice) - 1]
            result = agent.analyze_and_draft(selected_email)

            print(f"\nFrom: {result['sender']}")
            print(f"Subject: {result['subject']}  |  Category: {result['category']}  |  Priority: {result['priority']}")

            if result["draft_reply"]:
                print("--- DRAFT REPLY ---")
                print(result["draft_reply"])
            else:
                print("(no reply needed for this email)")