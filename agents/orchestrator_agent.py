import re

from agents.base_agent import BaseAgent
from agents.email_agent import EmailAgent
from agents.planning_agent import PlanningAgent
from agents.commercial_agent import OFF_TOPIC_REFUSAL, CommercialAgent
from agents.reply_agent import ReplyAgent
from utils.google_oauth import GoogleOAuthError
ORBIT_JARGON_PATTERNS = [
    r"\bEMS\b", r"\bOEE\b", r"\bESG\b", r"\bSCADA\b", r"\bPLC\b", r"\bMES\b",
    r"\bKPI(s)?\b", r"\bIoT\b", r"\bROI\b", r"\bTHD\b", r"\bISO\s?50001\b",
    r"\bIEC\s?62443\b", r"\bModbus\b", r"\bOPC-?UA\b", r"\bMQTT\b", r"\bBACnet\b",
]
ORBIT_JARGON_REGEX = re.compile("|".join(ORBIT_JARGON_PATTERNS), re.IGNORECASE)

# Deux intentions distinctes, jamais confondues par une heuristique de
# longueur de message :
# - REPLY_TO_EXISTING : répondre à un email qui existe déjà dans la boîte
# - REPLY_COMPOSE : rédiger/améliorer un texte fourni ou décrit par
#   l'utilisateur, sans email d'origine à consulter dans Gmail
REPLY_TO_EXISTING_PATTERNS = [
    r"\breply to\b", r"\banswer this email\b", r"\brespond to (this|that|the)\b",
    r"\bgive me (a |the )?repl?y\b", r"\bgive me (a |the )?respon[cs]e\b",
    r"\brépondre à\b", r"\brépondre au dernier\b",
    r"\bdonn\w*\b.{0,20}\br[ée]pon[cs]e\b",
    r"\bla r[ée]pon[cs]e (de|à|a|pour)\b",
]

REPLY_TO_EXISTING_REGEX = re.compile("|".join(REPLY_TO_EXISTING_PATTERNS), re.IGNORECASE)

# ".{0,25}" tolère des mots intercalés ("a formal email", "an urgent
# professional email") sans exiger que "email" suive immédiatement le verbe.
REPLY_COMPOSE_PATTERNS = [
    r"\bwrite\b.{0,25}\bemail\b", r"\bdraft\b.{0,25}\bemail\b",
    r"\bcompose\b.{0,25}\bemail\b", r"\bimprove\b.{0,25}\bemail\b",
    r"\bauto-?reply\b", r"\bdraft a reply\b", r"\bwrite a reply\b",
    r"\bprepare a reply\b", r"\bdraft response\b",
    r"\brédiger (un|le|mon) e?-?mail\b", r"\bécrire (un|le|mon) e?-?mail\b",
    r"\baméliorer (cet?|ce) e?-?mail\b", r"\bbrouillon\b",
]
REPLY_COMPOSE_REGEX = re.compile("|".join(REPLY_COMPOSE_PATTERNS), re.IGNORECASE)

EMAIL_PATTERNS = [
    r"\bemail(s)?\b", r"\bmail(s)?\b", r"\bboîte de réception\b", r"\binbox\b",
    r"\bmessages? reçus?\b", r"\blire mes mails\b", r"\bnouveaux? mails?\b",
    r"\bgmail\b",
]
EMAIL_REGEX = re.compile("|".join(EMAIL_PATTERNS), re.IGNORECASE)

PLANNING_PATTERNS = [
    r"\bagenda\b", r"\bcalendrier\b", r"\bcalendar\b",
    r"\bmon planning\b", r"\bmy schedule\b", r"\bmy calendar\b",
    r"\brendez-vous\b", r"\brdv\b",
    r"\bma journée\b", r"\bmy day\b",
    r"\bbriefing\b", r"\bconflits? d'horaire\b", r"\bschedule conflicts?\b",
]
PLANNING_REGEX = re.compile("|".join(PLANNING_PATTERNS), re.IGNORECASE)
ALL_EMAILS_PATTERNS = [
    r"\ball (of )?(my |the )?emails?\b", r"\beach email\b", r"\bevery email\b",
    r"\btous les emails?\b", r"\btous mes emails?\b", r"\bchaque email\b",
    r"\btoutes mes réponses\b",
]
ALL_EMAILS_REGEX = re.compile("|".join(ALL_EMAILS_PATTERNS), re.IGNORECASE)

ROUTER_CLASSIFIER_PROMPT = """You are a routing classifier for a multi-agent business assistant
called Orbit AI. There are four specialized agents:

- "email": reads/analyzes/summarizes the user's Gmail inbox (read-only, no drafting)
- "reply": drafts a reply to an email that needs a response — use this when the user wants
  a WRITTEN reply produced, not just to read/list emails
- "planning": READS the user's OWN Google Calendar — only for checking existing schedule,
  detecting conflicts, or a daily briefing. This agent is READ-ONLY and cannot book, create,
  or schedule anything.
- "commercial": talks to customers/prospects about Orbit products, pricing, qualification,
  demos, AND handles any request from a prospect to schedule/book a meeting or call with the
  sales team — since actually booking a meeting is a sales action, not a calendar lookup.

CRITICAL DISTINCTION (meeting requests): a message like "let's meet today", "can we schedule
a call", "I want to book a meeting with you", "are you available now" is a SALES scheduling
request from a prospect — route this to "commercial", NOT "planning". Only route to "planning"
when the user is asking to check THEIR OWN existing calendar/schedule.

CRITICAL DISTINCTION (email vs reply): "show me my emails" / "what's in my inbox" -> email.
"draft a reply to that email" / "help me answer this" / "write a response" -> reply.

Examples:
- "let's schedule a call to discuss this" -> commercial
- "I'm available now, can we meet?" -> commercial
- "what's my schedule for today?" -> planning
- "do I have any conflicts tomorrow?" -> planning
- "check my inbox" -> email
- "draft a reply to my last email" -> reply

CRITICAL: if the current message is short, ambiguous, or looks like a direct continuation of
the previous exchange (e.g. answering a question, picking an option like "the first one" or
"option 2", agreeing, giving a number/detail without new context), and it does NOT clearly
mention email/inbox/reply or the user's own calendar, KEEP routing to "{last_route}" instead of
guessing a new agent. Only switch agents when the message clearly and explicitly signals a
different topic.

Given the user's message, decide which single agent should handle it.

Respond with ONLY this JSON, nothing else:
{{"agent": "email" | "reply" | "planning" | "commercial", "reason": "one short sentence"}}

User message: "{message}"
"""

VALID_AGENTS = ("email", "reply", "planning", "commercial")


class OrchestratorAgent(BaseAgent):
    """
    Routeur central : dirige chaque message utilisateur vers l'agent
    spécialisé approprié (Email / Reply / Planning / Commercial).

    Ne gère pas de logique métier lui-même — délègue toujours à un
    agent enfant.
    """

    model_name = "qwen2.5:7b"
    system_prompt = ""

    def __init__(self, config_path="config/llm.yaml", reply_persona: str = "business"):
        super().__init__(config_path)
        self.last_reply_mode = "existing"
        self.email_agent = EmailAgent()
        self.planning_agent = PlanningAgent()
        self.commercial_agent = CommercialAgent()
        self.reply_agent = ReplyAgent(persona=reply_persona)

        self.commercial_history = []
        self.last_route = "commercial"
        self.client_user_id = None
        # Vrai si le dernier message du Reply Agent était une question de
        # clarification ("qui est concerné ?", "quel est le sujet ?") —
        # dans ce cas, le PROCHAIN message doit rester routé vers "reply"
        # même s'il est long et contient des mots qui ressemblent à du
        # planning ("meeting", "tomorrow at 10 AM"), car il répond
        # simplement à cette question, ce n'est pas un nouveau sujet.
        self.awaiting_clarification = False
    SIGNUP_REQUIRED_MESSAGE = (
        "This feature requires an account. Please sign up or log in to access "
        "your own Gmail and Calendar data."
    )
    NOT_CONNECTED_MESSAGE = (
            "To use this feature, please connect your Google account first "
            "(Gmail and Calendar access) from the Integrations page."
        )
    @staticmethod
    def _matches_reply_existing(message: str) -> bool:
        return bool(REPLY_TO_EXISTING_REGEX.search(message))

    @staticmethod
    def _matches_reply_compose(message: str) -> bool:
        return bool(REPLY_COMPOSE_REGEX.search(message))

    @staticmethod
    def _matches_email(message: str) -> bool:
        return bool(EMAIL_REGEX.search(message))

    @staticmethod
    def _matches_planning(message: str) -> bool:
        return bool(PLANNING_REGEX.search(message))

    def _classify_with_llm(self, message: str) -> str:
        prompt = ROUTER_CLASSIFIER_PROMPT.format(
            message=message, last_route=self.last_route
        )
        raw = self.call_llm_raw(prompt, temperature=0.0, max_tokens=100)
        result = self.parse_json_response(
            raw, fallback={"agent": self.last_route, "reason": "parse_error"}
        )
        agent = result.get("agent", self.last_route)
        return agent if agent in VALID_AGENTS else self.last_route

    def route(self, message: str) -> str:
        if ORBIT_JARGON_REGEX.search(message):
            self.last_route = "commercial"
            self.awaiting_clarification = False
            return "commercial"

        if self._matches_reply_existing(message):
            self.last_route = "reply"
            self.last_reply_mode = "existing"
            self.awaiting_clarification = False
            return "reply"
        if self._matches_reply_compose(message):
            self.last_route = "reply"
            self.last_reply_mode = "compose"
            self.awaiting_clarification = False
            return "reply"

        if self._matches_email(message):
            self.last_route = "email"
            self.awaiting_clarification = False
            return "email"
        if self._matches_planning(message):
            self.last_route = "planning"
            self.awaiting_clarification = False
            return "planning"

        # Priorité haute : si on attendait une clarification pour une
        # tâche "reply" en cours, ce message y répond très probablement —
        # on reste sur "reply" sans même consulter le classifieur LLM,
        # peu importe la longueur ou le contenu du message.
        if self.awaiting_clarification:
            self.last_route = "reply"
            return "reply"

        if len(message.strip()) < 6:
            self.last_route = "commercial"
            return "commercial"

        target = self._classify_with_llm(message)
        self.last_route = target
        self.awaiting_clarification = False
        return target
    def run(self, message: str) -> dict:
        target = self.route(message)
        user_id = getattr(self, "client_user_id", None)

        if target == "email":
            # SECURITY: never fall back to a shared/default Google token.
            # Without a real authenticated user_id, this must refuse —
            # not silently read someone else's inbox (this was a real
            # data-leak bug: guests were able to read the developer's
            # own Gmail through this exact code path).
            if user_id is None:
                return {"agent": "email", "response": self.SIGNUP_REQUIRED_MESSAGE}
            try:
                results = self.email_agent.run_for_user(user_id, max_results=5)
            except GoogleOAuthError:
                return {"agent": "email", "response": self.NOT_CONNECTED_MESSAGE}
            return {"agent": "email", "response": results}

        if target == "reply":
            force_final = getattr(self, "awaiting_clarification", False)

            # Only the "compose from text" mode can work without Gmail
            # access. Any mode that needs to read an existing email
            # requires a real connected account.
            if user_id is None and getattr(self, "last_reply_mode", "existing") != "compose":
                return {"agent": "reply", "response": self.SIGNUP_REQUIRED_MESSAGE}

            try:
                response = self._handle_reply_request(
                    message, user_id=user_id, force_final=force_final
                )
            except GoogleOAuthError:
                return {"agent": "reply", "response": self.NOT_CONNECTED_MESSAGE}

            self.awaiting_clarification = ("?" in response) and not force_final
            return {"agent": "reply", "response": response}

        if target == "planning":
            if user_id is None:
                return {"agent": "planning", "response": self.SIGNUP_REQUIRED_MESSAGE}
            try:
                result = self.planning_agent.run_for_user(user_id)
            except GoogleOAuthError:
                return {"agent": "planning", "response": self.NOT_CONNECTED_MESSAGE}
            return {"agent": "planning", "response": result["briefing"], "details": result}

        response = self.commercial_agent.run(message, self.commercial_history)

        if response != OFF_TOPIC_REFUSAL:
            self.commercial_history.append({"role": "user", "content": message})
            self.commercial_history.append({"role": "assistant", "content": response})

        return {"agent": "commercial", "response": response}
    def _handle_reply_request(self, message: str, user_id: int = None, force_final: bool = False) -> str:
        if getattr(self, "last_reply_mode", "existing") == "compose":
            return self.reply_agent.draft_from_text(message, force_final=force_final)
        emails = self.reply_agent.get_raw_email_list(max_results=5, user_id=user_id)
        if not emails:
            return "I couldn't find any recent emails to reply to."

        if ALL_EMAILS_REGEX.search(message):
            drafts = []
            for email in emails:
                result = self.reply_agent.analyze_and_draft(email)
                if result["draft_reply"]:
                    drafts.append(
                        f"— \"{result['subject']}\" from {result['sender']}:\n{result['draft_reply']}"
                    )

            if not drafts:
                return "None of your 5 most recent emails currently need a reply."

            return (
                "Here are draft replies for the emails that need one:\n\n"
                + "\n\n".join(drafts)
                + "\n\n(Please review each before sending — these are drafts only.)"
            )

        # Cas normal : un seul brouillon, le premier email qui en a besoin.
        for email in emails:
            result = self.reply_agent.analyze_and_draft(email)
            if result["draft_reply"]:
                return (
                    f"Here's a draft reply to \"{result['subject']}\" "
                    f"from {result['sender']}:\n\n{result['draft_reply']}\n\n"
                    f"(Please review before sending — this is a draft only.)"
                )

        return "None of your 5 most recent emails currently need a reply."
    
if __name__ == "__main__":
    print("Orbit AI Assistant — Orchestrator")
    print("=" * 50)

    orchestrator = OrchestratorAgent()

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        if not user_input.strip():
            continue

        result = orchestrator.run(user_input)
        print(f"\n[routed to: {result['agent']}]")
        print(result["response"])