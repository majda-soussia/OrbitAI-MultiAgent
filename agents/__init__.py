import re

from agents.base_agent import BaseAgent
from agents.email_agent import EmailAgent
from agents.planning_agent import PlanningAgent
from agents.commercial_agent import CommercialAgent


# ---------------------------------------------------------------------
# Couche 0/1 : mots-clés déterministes
# ---------------------------------------------------------------------
# Comme pour le Commercial Agent (_matches_jargon_allowlist), on essaie
# de router SANS appeler le LLM à chaque fois — plus rapide, plus fiable,
# et le LLM classifier ne sert qu'aux cas ambigus.

EMAIL_PATTERNS = [
    r"\bemail(s)?\b", r"\bmail(s)?\b", r"\bboîte de réception\b", r"\binbox\b",
    r"\bmessages? reçus?\b", r"\blire mes mails\b", r"\bnouveaux? mails?\b",
    r"\bgmail\b",
]
EMAIL_REGEX = re.compile("|".join(EMAIL_PATTERNS), re.IGNORECASE)

PLANNING_PATTERNS = [
    r"\bagenda\b", r"\bcalendrier\b", r"\bcalendar\b", r"\bplanning\b",
    r"\brendez-vous\b", r"\brdv\b", r"\bréunions?\b", r"\bmeetings?\b",
    r"\bemploi du temps\b", r"\bjournée\b", r"\bschedule\b", r"\bbriefing\b",
    r"\bconflits? d'horaire\b",
]
PLANNING_REGEX = re.compile("|".join(PLANNING_PATTERNS), re.IGNORECASE)

# Le Commercial Agent reste le routage par défaut : c'est l'agent
# conversationnel front-facing pour les prospects/clients.

ROUTER_CLASSIFIER_PROMPT = """You are a routing classifier for a multi-agent business assistant
called Orbit AI. There are three specialized agents:

- "email": reads/analyzes/summarizes the user's Gmail inbox
- "planning": reads/analyzes the user's Google Calendar, detects conflicts, gives a daily briefing
- "commercial": talks to customers/prospects about Orbit products, pricing, qualification, demos

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
    system_prompt = ""  # non utilisé : l'orchestrateur ne fait que router

    def __init__(self, config_path="config/llm.yaml"):
        super().__init__(config_path)

        # Les agents enfants sont instanciés une seule fois (paresseux serait
        # possible aussi, mais ici le coût d'init est faible : lecture de
        # fichiers de config/prompts, pas de connexion réseau immédiate).
        self.email_agent = EmailAgent()
        self.planning_agent = PlanningAgent()
        self.commercial_agent = CommercialAgent()

        # Historique de conversation, uniquement utilisé pour le Commercial
        # Agent (les agents Email/Planning n'ont pas de notion de contexte
        # conversationnel — ce sont des actions ponctuelles).
        self.commercial_history = []

    # -------------------------------------------------------------
    # Détection de l'agent cible
    # -------------------------------------------------------------

    @staticmethod
    def _matches_email(message: str) -> bool:
        return bool(EMAIL_REGEX.search(message))

    @staticmethod
    def _matches_planning(message: str) -> bool:
        return bool(PLANNING_REGEX.search(message))

    def _classify_with_llm(self, message: str) -> str:
        prompt = ROUTER_CLASSIFIER_PROMPT.format(message=message)
        raw = self.call_llm_raw(prompt, temperature=0.0, max_tokens=100)
        result = self.parse_json_response(
            raw, fallback={"agent": "commercial", "reason": "parse_error"}
        )
        agent = result.get("agent", "commercial")
        return agent if agent in ("email", "planning", "commercial") else "commercial"

    def route(self, message: str) -> str:
        """
        Retourne le nom de l'agent cible : "email", "planning" ou "commercial".
        """
        # Couche 0/1 : mots-clés déterministes — priorité absolue.
        if self._matches_email(message):
            return "email"
        if self._matches_planning(message):
            return "planning"

        # Cas explicitement commercial ou ambigu court -> pas besoin du LLM,
        # on part directement sur le Commercial Agent (comportement par défaut
        # attendu pour un assistant commercial face à un prospect).
        if len(message.strip()) < 6:
            return "commercial"

        # Couche 2 : classifieur LLM, réservé aux messages plus longs et
        # potentiellement ambigus (aucun mot-clé évident détecté).
        return self._classify_with_llm(message)

    # -------------------------------------------------------------
    # Dispatch
    # -------------------------------------------------------------

    def run(self, message: str) -> dict:
        """
        Route le message vers l'agent approprié et retourne un résultat
        structuré uniforme : {"agent": ..., "response": ...}
        """
        target = self.route(message)

        if target == "email":
            results = self.email_agent.run(max_results=5)
            return {"agent": "email", "response": results}

        if target == "planning":
            result = self.planning_agent.run()
            return {"agent": "planning", "response": result["briefing"], "details": result}

        # Défaut : commercial
        response = self.commercial_agent.run(message, self.commercial_history)
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