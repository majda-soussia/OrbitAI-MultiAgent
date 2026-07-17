import re

from agents.base_agent import BaseAgent
from agents.email_agent import EmailAgent
from agents.planning_agent import PlanningAgent
from agents.commercial_agent import OFF_TOPIC_REFUSAL, CommercialAgent
# En haut de orchestrator_agent.py, à côté des autres patterns
ORBIT_JARGON_PATTERNS = [
    r"\bEMS\b", r"\bOEE\b", r"\bESG\b", r"\bSCADA\b", r"\bPLC\b", r"\bMES\b",
    r"\bKPI(s)?\b", r"\bIoT\b", r"\bROI\b", r"\bTHD\b", r"\bISO\s?50001\b",
    r"\bIEC\s?62443\b", r"\bModbus\b", r"\bOPC-?UA\b", r"\bMQTT\b", r"\bBACnet\b",
]
ORBIT_JARGON_REGEX = re.compile("|".join(ORBIT_JARGON_PATTERNS), re.IGNORECASE)
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

# Le Commercial Agent reste le routage par défaut : c'est l'agent
# conversationnel front-facing pour les prospects/clients.

ROUTER_CLASSIFIER_PROMPT = """You are a routing classifier for a multi-agent business assistant
called Orbit AI. There are three specialized agents:

- "email": reads/analyzes/summarizes the user's Gmail inbox
- "planning": READS the user's OWN Google Calendar — only for checking existing schedule,
  detecting conflicts, or a daily briefing. This agent is READ-ONLY and cannot book, create,
  or schedule anything.
- "commercial": talks to customers/prospects about Orbit products, pricing, qualification,
  demos, AND handles any request from a prospect to schedule/book a meeting or call with the
  sales team — since actually booking a meeting is a sales action, not a calendar lookup.

CRITICAL DISTINCTION: a message like "let's meet today", "can we schedule a call", "I want to
book a meeting with you", "are you available now" is a SALES scheduling request from a
prospect — route this to "commercial", NOT "planning". Only route to "planning" when the user
is asking to check THEIR OWN existing calendar/schedule (e.g. "what's on my calendar today",
"do I have any conflicts tomorrow", "give me my daily briefing").

Examples:
- "let's schedule a call to discuss this" -> commercial
- "I'm available now, can we meet?" -> commercial
- "what's my schedule for today?" -> planning
- "do I have any conflicts tomorrow?" -> planning

CRITICAL: if the current message is short, ambiguous, or looks like a direct continuation of
the previous exchange (e.g. answering a question, picking an option like "the first one" or
"option 2", agreeing, giving a number/detail without new context), and it does NOT clearly
mention email/inbox or the user's own calendar, KEEP routing to "{last_route}" instead of
guessing a new agent. Only switch agents when the message clearly and explicitly signals a
different topic (e.g. "check my email now", "what's on my calendar").

Given the user's message, decide which single agent should handle it.

Respond with ONLY this JSON, nothing else:
{{"agent": "email" | "planning" | "commercial", "reason": "one short sentence"}}

User message: "{message}"
""" 
class OrchestratorAgent(BaseAgent):
    """
    Routeur central : dirige chaque message utilisateur vers l'agent
    spécialisé approprié (Email / Planning / Commercial).

    Ne gère pas de logique métier lui-même — délègue toujours à un
    agent enfant. Utilise call_llm_raw() de BaseAgent uniquement pour
    la classification de secours (couche 2), sans polluer le contexte
    avec un system_prompt métier.
    """

    model_name = "qwen2.5:7b"
    system_prompt = "" 

    def __init__(self, config_path="config/llm.yaml"):
        super().__init__(config_path)

        self.email_agent = EmailAgent()
        self.planning_agent = PlanningAgent()
        self.commercial_agent = CommercialAgent()

        self.commercial_history = []
        self.last_route = "commercial"

    # Détection de l'agent cible
  
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
        return agent if agent in ("email", "planning", "commercial") else self.last_route
    def route(self, message: str) -> str:
        if ORBIT_JARGON_REGEX.search(message):
            self.last_route = "commercial"
            return "commercial"

        if self._matches_email(message):
            self.last_route = "email"
            return "email"
        if self._matches_planning(message):
            self.last_route = "planning"
            return "planning"

        if len(message.strip()) < 6:
            self.last_route = "commercial"
            return "commercial"

        target = self._classify_with_llm(message)
        self.last_route = target
        return target
    
    def run(self, message: str) -> dict:
        target = self.route(message)

        if target == "email":
            results = self.email_agent.run(max_results=5)
            return {"agent": "email", "response": results}

        if target == "planning":
            result = self.planning_agent.run()
            return {"agent": "planning", "response": result["briefing"], "details": result}

        response = self.commercial_agent.run(message, self.commercial_history)

        # Ne pas garder les refus off-topic dans l'historique — ils ne sont
        # pas de vrais échanges commerciaux et polluent le contexte des tours
        # suivants sans apporter d'info utile au modèle.
        if response != OFF_TOPIC_REFUSAL:
            self.commercial_history.append({"role": "user", "content": message})
            self.commercial_history.append({"role": "assistant", "content": response})

        return {"agent": "commercial", "response": response}

if __name__ == "__main__":
    print("Orbit AI Assistant — Orchestrator")
    print("=" * 50)

    orchestrator = OrchestratorAgent()

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        result = orchestrator.run(user_input)
        print(f"\n[routed to: {result['agent']}]")
        print(result["response"])