from agents.base_agent import BaseAgent
from utils.settings import is_debug_enabled
import re

ORBIT_JARGON_TERMS = [
    r"\bEMS\b", r"\bOEE\b", r"\bESG\b", r"\bSCADA\b", r"\bPLC\b", r"\bMES\b",
    r"\bKPI(s)?\b", r"\bIoT\b", r"\bROI\b", r"\bTHD\b", r"\bISO\s?50001\b",
    r"\bIEC\s?62443\b", r"\bModbus\b", r"\bOPC-?UA\b", r"\bMQTT\b", r"\bBACnet\b",
    r"\bOrbit\b",
    r"\bSiemens\b", r"\bWinCC\b", r"\bSchneider(\s?Electric)?\b", r"\bABB\b",
    r"\bJanitza\b", r"\bHuawei\b", r"\bAtlas\s?Copco\b", r"\bCircutor\b",
    r"\bCarlo\s?Gavazzi\b",
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
PROFILE_EXTRACTION_PROMPT = """Extract structured facts from this customer message, if present.
Only extract what is EXPLICITLY stated — never guess or infer a number/sector that isn't
clearly mentioned.

Customer message: "{message}"

Respond with ONLY this JSON, nothing else:
{{"industry_type": "<sector name or null>", "machine_count": <integer or null>}}
"""
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
- "Are you compatible with [any industrial hardware/software brand, e.g. a specific PLC,
  SCADA system, or sensor manufacturer]?" (in_scope: true — compatibility/integration
  questions are core B2B sales questions, even naming a competitor's or a third-party
  vendor's product, and even with no other Orbit-specific keyword in the sentence)
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

# Score cosinus minimal (vecteurs normalisés, IndexFlatIP) pour qu'un
# chunk soit considéré comme réellement pertinent — retrieve() renvoie
# toujours ses top_k voisins les plus proches, pertinents ou non, donc
# sans ce seuil on ne peut jamais détecter un cas de "aucune info trouvée".
# Calibré empiriquement le 2026-07-30 avec check_rag_scores.py :
# questions pertinentes ~0.69-0.72, hors-sujet ~0.59-0.66. Valeur choisie
# au milieu de cet écart. À revalider si le corpus data/rag/sources/
# change significativement, ou si tu observes des faux positifs/négatifs
# en usage réel (fallback qui se déclenche trop souvent, ou jamais).
RAG_RELEVANCE_THRESHOLD = 0.45

SPEC_KEYWORDS = [
    "spec", "specs", "specification", "compatib", "integrat", "protocol",
    "capacity", "sensor", "capteur", "meter", "compteur", "combien de",
    "support", "installation", "delay", "délai", "warranty", "garantie",
    "latence", "vitesse", "précision", "precision", "consommation",
    "fréquence", "frequence", "bande passante", "portée", "portee",
    "résolution", "resolution", "autonomie", "durée de vie", "duree de vie",
    "poids", "dimension", "tension", "voltage", "courant", "ampérage",
    "débit", "debit", "throughput", "disponibilité", "disponibilite",
    "uptime", "sla",
]
SPEC_UNIT_PATTERN = re.compile(
    r"\bms\b|milliseconde|\bwatt|\bvolt|\bampère|\bampere|\bghz\b|\bmhz\b|"
    r"\bkg\b|\bmm\b|\bcm\b|\bmaximal|\bminimal|\bexact|\bpr[ée]cis|\bspécifiqu|\bspecifiqu",
    re.IGNORECASE,
)
NO_SPECIFIC_INFO_FALLBACK = (
    "That's a great question, but I don't have the precise details on hand to answer "
    "it accurately right now. Let me connect you with a member of our team who can give "
    "you exact information — could you share your email or preferred contact method?"
)

# Nombre max de messages (user+assistant confondus) de l'historique
# renvoyés au modèle à chaque appel. Sans plafond, prompt_tokens grandit
# indéfiniment au fil d'une session longue, même si le nouveau message
# est court — voir la mesure faite avec utils/token_estimator.py.
# 12 messages = 6 échanges complets ; compromis entre continuité de la
# conversation (le modèle garde le fil des questions/réponses récentes)
# et coût (au-delà, les tours les plus anciens apportent rarement plus
# d'info utile que ce qu'ils coûtent en tokens à chaque appel suivant).
# L'historique COMPLET reste conservé côté orchestrateur/PostgreSQL pour
# la mémorisation persistante — seul ce qu'on ENVOIE au modèle est réduit.
MAX_HISTORY_MESSAGES = 12


def needs_pricing_context(question: str) -> bool:
    q_lower = question.lower()
    return any(kw in q_lower for kw in PRICING_KEYWORDS)


def needs_specific_data(question: str) -> bool:
    """Question factuelle précise (prix ou specs techniques) — c'est
    seulement pour ce type de question qu'un manque de contexte RAG doit
    déclencher le message explicite de transfert, pas pour une question
    générale ou une salutation où le prompt système suffit."""
    q_lower = question.lower()
    return (
        needs_pricing_context(question)
        or any(kw in q_lower for kw in SPEC_KEYWORDS)
        or bool(SPEC_UNIT_PATTERN.search(question))
    )

def _filter_relevant(results: list, threshold: float = RAG_RELEVANCE_THRESHOLD) -> list:
    return [r for r in results if r["score"] >= threshold]


def get_rag_context(question: str) -> str:
    from data.rag.retriever import retrieve, build_context_block

    all_results = _filter_relevant(retrieve(question, top_k=5))

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
        # faq_objections.json et sector_qualification.json sont déjà
        # indexés dans FAISS (data/rag/index/) et accessibles via
        # get_rag_context() — les recharger ici en JSON brut était du
        # code mort (jamais utilisé) et un point de crash inutile au
        # démarrage de l'agent.

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

    @staticmethod
    def _strip_letter_artifacts(text: str) -> str:
        original = text.strip()
        cleaned = original

        # 1. Préambule méta avant le contenu réel
        #    ("Certainly! Here's a concise explanation of X:")
        cleaned = re.sub(
            r'^\s*(certainly|sure|of course|absolutely|great question)!?\s*,?\s*'
            r"here'?s?\s+(a|an|the)?\s*.*?:\s*\n+",
            '',
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # 2. Guillemet ouvrant détecté : la citation peut se refermer au
        #    MILIEU du texte (suivie d'une phrase de sortie du type "Feel
        #    free to adjust..."), pas forcément au tout dernier caractère —
        #    on cherche donc le dernier guillemet fermant du texte et on
        #    garde uniquement ce qu'il y a entre les deux, en jetant tout
        #    ce qui suit la fermeture (c'est presque toujours du remplissage).
        if cleaned[:1] in ('"', '\u201c'):
            closing_idx = max(cleaned.rfind('"', 1), cleaned.rfind('\u201d', 1))
            if closing_idx > 0:
                cleaned = cleaned[1:closing_idx].strip()
            else:
                cleaned = cleaned[1:].strip()

        # 3. Salutation d'ouverture ("Hello,", "Dear X,")
        cleaned = re.sub(r'^\s*(hello|hi|dear)\b[^\n]*\n+', '', cleaned, flags=re.IGNORECASE).strip()

        # 4. Bloc de signature ("Best regards," et tout ce qui suit :
        #    "[Your Name]", "Orbit Engineering Solutions", etc.)
        cleaned = re.sub(
            r'\n+\s*(best regards|kind regards|warm regards|sincerely|cordialement|bien à vous)[,]?\s*[\s\S]*$',
            '',
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        # 5. Phrase de clôture méta résiduelle, même sans guillemets
        #    ("Feel free to adjust the details as needed!").
        cleaned = re.sub(
            r'\n+\s*feel free to (adjust|edit|modify|change|update)[^\n]*[.!]?\s*$',
            '',
            cleaned,
            flags=re.IGNORECASE,
        ).strip()

        cleaned = cleaned.strip('"\u201c\u201d').strip()

        return cleaned if cleaned else original

    @staticmethod
    def _trim_history(history: list) -> list:
        """Ne garde que les MAX_HISTORY_MESSAGES derniers messages — voir
        le commentaire sur la constante pour le raisonnement complet."""
        if not history:
            return []
        return history[-MAX_HISTORY_MESSAGES:]

    def run(self, user_message: str, history: list = None) -> str:
        history = self._trim_history(history)

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
            # chunk suffisamment pertinent trouvé : on ne laisse jamais
            # le LLM improviser une réponse générale ici (risque
            # d'invention de specs/prix) — message explicite + transfert
            # humain à la place.
            return NO_SPECIFIC_INFO_FALLBACK

        augmented_message = (
            f"{rag_context}\n\nCustomer question: {user_message}"
            if rag_context else user_message
        )

        raw_text = self.call_llm(
            augmented_message,
            extra_messages=history
        )

        return self._strip_letter_artifacts(self.clean_text_response(raw_text))
    def extract_profile_info(self, user_message: str) -> dict:
        """Extraction légère et best-effort — ne bloque jamais la
        conversation si le parsing échoue, renvoie juste des valeurs None."""
        prompt = PROFILE_EXTRACTION_PROMPT.format(message=user_message)
        raw = self.call_llm_raw(prompt, temperature=0.0, max_tokens=60)
        result = self.parse_json_response(
            raw, fallback={"industry_type": None, "machine_count": None}
        )
        return {
            "industry_type": result.get("industry_type") or None,
            "machine_count": result.get("machine_count") if isinstance(result.get("machine_count"), int) else None,
        }
if __name__ == "__main__":

    print("Orbit AI Assistant — Commercial Agent")
    print("=" * 50)

    agent = CommercialAgent()  # Create the agent

    history = []  # Store the conversation history

    while True:
        user_input = input("\nYou: ")  # Read user input

        if user_input.lower() in ["exit", "quit"]:  # Exit the conversation
            break

        response = agent.run(user_input, history)  # Generate the assistant's response

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