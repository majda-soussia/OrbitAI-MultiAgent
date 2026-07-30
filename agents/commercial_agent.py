from agents.base_agent import BaseAgent
from utils.settings import is_debug_enabled
import re
RAG_RELEVANCE_THRESHOLD = 0.68
SPEC_KEYWORDS = [
    "spec", "specs", "specification", "compatib", "integrat", "protocol",
    "capacity", "sensor", "capteur", "meter", "compteur", "combien de",
    "support", "installation", "delay", "délai", "warranty", "garantie",
]
ORBIT_JARGON_TERMS = [
    r"\bEMS\b", r"\bOEE\b", r"\bESG\b", r"\bSCADA\b", r"\bPLC\b", r"\bMES\b",
    r"\bKPI(s)?\b", r"\bIoT\b", r"\bROI\b", r"\bTHD\b", r"\bISO\s?50001\b",
    r"\bIEC\s?62443\b", r"\bModbus\b", r"\bOPC-?UA\b", r"\bMQTT\b", r"\bBACnet\b",
    r"\bOrbit\b",
]
ORBIT_JARGON_REGEX = re.compile("|".join(ORBIT_JARGON_TERMS), re.IGNORECASE)

HARD_OFF_TOPIC_PATTERNS = [
    r"\bexam(e|s|en)?\b",
    r"\bhomework\b",
    r"\bdevoir(s)?\b",
    r"\bweather\b|\bmétéo\b|\bmeteo\b",
    r"\brecipe\b|\bcuisine\b|\bcook(ing)?\b|\bpizza\b",
    r"\bjoke\b|\bblague\b",
    r"\btaylor series\b|\byoung'?s modulus\b",
    r"\bfootball\b|\bmovie\b|\bfilm\b|\bmusic\b|\bsong\b",
]
HARD_OFF_TOPIC_REGEX = re.compile("|".join(HARD_OFF_TOPIC_PATTERNS), re.IGNORECASE)

OFF_TOPIC_REFUSAL = (
    "Sorry, I am the Orbit AI Assistant and I can only answer questions related to "
    "Orbit products, Industry 4.0, Energy Management and Industrial IoT."
)
NO_SPECIFIC_INFO_FALLBACK = (
    "That's a great question, but I don't have the precise details on hand to answer "
    "it accurately right now. Let me connect you with a member of our team who can give "
    "you exact information — could you share your email or preferred contact method?"
)

TOPIC_CLASSIFIER_PROMPT = """You are a strict topic classifier for a B2B industrial sales assistant.

The assistant (Orbit AI) may ONLY discuss: Energy Management, Industry 4.0, Industrial IoT,
Predictive Maintenance, ESG/Carbon reporting, Manufacturing KPIs/SCADA, or commercial questions
about Orbit Engineering Solutions (products, pricing, demos, sectors, capabilities).

It must NOT discuss: school/exam/homework help (even with technical vocabulary like
"Young's modulus" or "Taylor series"), general trivia (weather, recipes, etc.), personal
advice, politics, religion, or anything unrelated to an industrial customer's business need.

IMPORTANT: Judge ONLY the latest user message on its own merit. Do not let the tone or
topic of earlier messages in the conversation bias your judgment of this new message —
each message must be classified independently, even if previous messages were off-topic.

IMPORTANT: Generic-sounding commercial questions are IN_SCOPE by default, even without the
word "Orbit" in them, since this is a conversation with Orbit's sales assistant. Examples of
messages that MUST be classified in_scope: true:
- "What is the product you offer?" (in_scope: true — asking about Orbit's offering)
- "How much does it cost?" / "How much does Orbit cost?" (in_scope: true — pricing question)
- "What do you offer in your industry?" (in_scope: true)
- "Can you tell me more?" (in_scope: true — follow-up, assume it continues the commercial topic)

IMPORTANT: If the latest message looks like a natural follow-up to an ongoing
Orbit conversation (asking to clarify an acronym, asking "how does that work",
asking what tools/technology are used, asking for more detail, even with typos
or broken English/French grammar), classify it as in_scope: true. Only classify
as off-topic when the message clearly introduces a NEW unrelated subject
(school, cooking, weather, entertainment, personal life) with no plausible link
to the conversation.

When genuinely uncertain, prefer in_scope: true — it is worse to block a real customer than
to let one borderline message through.

Recent user-only conversation context (for detecting topic drift across turns):
{history}
CRITICAL: If the assistant's last message asked a qualification question (e.g. about sites,
sensors, sector, protocols, needs), a short factual answer like a number, a protocol name, or
a brief data point (e.g. "8 factories", "500 sensors", "MQTT") is a legitimate in-scope reply
to that question — classify it in_scope: true, even though it has no keywords on its own.
Latest user message: "{message}"

Respond with ONLY this JSON, nothing else:
{{"in_scope": true or false, "reason": "one short sentence"}}
"""
PRICING_KEYWORDS = [
    "prix", "coût", "cout", "tarif", "tarifs", "devis", "budget",
    "combien", "price", "cost", "quotation", "pricing"
]

def needs_pricing_context(question: str) -> bool:
    q_lower = question.lower()
    return any(kw in q_lower for kw in PRICING_KEYWORDS)
def needs_specific_data(question: str) -> bool:
    """Question factuelle précise (prix ou specs techniques) — c'est
    seulement pour ce type de question qu'un manque de contexte RAG doit
    déclencher le message explicite de transfert, pas pour une question
    générale ou une salutation où le prompt système suffit."""
    q_lower = question.lower()
    return needs_pricing_context(question) or any(kw in q_lower for kw in SPEC_KEYWORDS)


def _filter_relevant(results: list, threshold: float = RAG_RELEVANCE_THRESHOLD) -> list:
    return [r for r in results if r["score"] >= threshold]

def get_rag_context(question: str) -> str:
    from data.rag.retriever import retrieve, build_context_block

    all_results = _filter_relevant(retrieve(question, top_k=3))

    if needs_pricing_context(question):
        pricing_results = _filter_relevant(retrieve(question, top_k=2, type_filter="pricing"))
        # fusion sans doublons, pricing en priorité
        seen_ids = {r["text"] for r in pricing_results}
        merged = pricing_results + [r for r in all_results if r["text"] not in seen_ids]
        return build_context_block(merged[:4])

    return build_context_block(all_results)
class CommercialAgent(BaseAgent):
    max_tokens = 250
    def __init__(self, config_path="config/llm.yaml"):
        with open("prompts/commercial.txt", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

        super().__init__(config_path)

        with open("data/rag/sources/faq_objections.json", "r", encoding="utf-8") as f:
            self.faq_data = json.load(f)

        with open("data/rag/sources/sector_qualification.json", "r", encoding="utf-8") as f:
            self.sector_data = json.load(f)
    @staticmethod
    def _matches_jargon_allowlist(message: str) -> bool:
        return bool(ORBIT_JARGON_REGEX.search(message))

    @staticmethod
    def _matches_hard_blocklist(message: str) -> bool:
        return bool(HARD_OFF_TOPIC_REGEX.search(message))

    def _is_in_scope(self, user_message: str, history: list) -> bool:
        if self._matches_jargon_allowlist(user_message):
            return True

        if self._matches_hard_blocklist(user_message):
            return False

        # On inclut la DERNIÈRE question de l'assistant, pas seulement
        # l'historique utilisateur : sans elle, une réponse courte comme
        # "8 factories" ou "500 sensors" n'a aucun contexte pour être
        # reconnue comme une réponse légitime à une question de
        # qualification commerciale — elle ressemble à une phrase isolée
        # et absurde vue seule.
        last_assistant_message = next(
            (m["content"] for m in reversed(history or []) if m.get("role") == "assistant"),
            None
        )

        recent_user_messages = [
            m["content"] for m in (history or [])
            if m.get("role") == "user"
        ][-4:]

        history_text = "\n".join(f"- {msg}" for msg in recent_user_messages) or "(no prior messages)"

        assistant_context = (
            f'\nThe assistant\'s last message asked: "{last_assistant_message}"\n'
            if last_assistant_message else ""
        )

        prompt = TOPIC_CLASSIFIER_PROMPT.format(
            history=history_text,
            message=user_message,
        ) + assistant_context

        raw = self.call_llm_raw(prompt, temperature=0.0, max_tokens=100)
        result = self.parse_json_response(raw, fallback={"in_scope": True, "reason": "parse_error"})

        return bool(result.get("in_scope", True))
    def run(self, user_message: str, history: list = None) -> str:
        history = history or []

        if not self._is_in_scope(user_message, history):
            return OFF_TOPIC_REFUSAL

        try:
            rag_context = get_rag_context(user_message)
        except Exception as e:
            print(f"[CommercialAgent] RAG context error: {e}")
            rag_context = ""

        if is_debug_enabled():
            print(f"[DEBUG] RAG context injected:\n{rag_context if rag_context else '(empty)'}")

        if not rag_context and needs_specific_data(user_message):
            # Question factuelle précise (prix, specs...) mais aucun
            # chunk pertinent trouvé : on ne laisse jamais le LLM
            # improviser une réponse générale ici (risque d'invention de
            # specs/prix) — message explicite + transfert humain.
            return NO_SPECIFIC_INFO_FALLBACK

        augmented_message = (
            f"{rag_context}\n\nCustomer question: {user_message}"
            if rag_context else user_message
        )

        raw_text = self.call_llm(
            augmented_message,
            extra_messages=history
        )

        return self.clean_text_response(raw_text)
if __name__ == "__main__":

    print("Orbit AI Assistant — Commercial Agent")
    print("=" * 50)

    agent = CommercialAgent() # Create the agent

    history = [] # Store the conversation history

    while True:
        user_input = input("\nYou: ") # Read user input

        if user_input.lower() in ["exit", "quit"]: # Exit the conversation
            break

        response = agent.run(user_input, history) # Generate the assistant's response

        print(f"\nOrbit AI: {response}")

        # Update the conversation history
        history.append({
            "role": "user",
            "content": user_input
        })

        history.append({
            "role": "assistant",
            "content": response
        })