"""
Estimateur de tokens — outil de DIAGNOSTIC pour l'administrateur.

Ce module n'est PAS un mécanisme de contrôle ou de blocage pour le
client — il ne remplace jamais le compte réel (prompt_eval_count /
eval_count) retourné par Ollama après un appel, qui reste la seule
source fiable utilisée pour la facturation (voir agents/base_agent.py
et utils/token_tracker.py). Il sert uniquement à répondre à des
questions du type "d'où vient le coût de cet agent ?" AVANT d'avoir
fait l'appel réel.

PRÉCISION : approximation par caractères (~4 caractères = 1 token,
la même règle que celle documentée publiquement par Gemini/GPT), pas
le vrai tokenizer BPE de Qwen2.5. Marge d'erreur réaliste : +/- 15-20%.

IMPORTANT : rien ici n'est codé en dur. Les coûts par agent sont
recalculés à chaque appel en lisant les vrais fichiers prompts/*.txt
ou en instanciant les vraies classes d'agents et en lisant leur
self.system_prompt — si un prompt change, ce module reflète le
changement automatiquement, sans qu'on ait besoin de le modifier.
"""

CHARS_PER_TOKEN = 4  # approximation universelle (Gemini/GPT documentent la même règle)


def estimate_tokens(text: str) -> int:
    """
    Estimation rapide, sans appel modèle. À ne PAS utiliser pour
    facturer ou bloquer un client — seulement pour du diagnostic admin.
    """
    if not text:
        return 0
    return max(1, len(text) // CHARS_PER_TOKEN)


def _read_prompt_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except (FileNotFoundError, OSError):
        return ""


def get_system_prompt_cost(system_prompt_text: str = None, prompt_file: str = None) -> int:
    """
    Coût estimé (en tokens) d'un system prompt donné.

    Deux façons de l'appeler :
    - system_prompt_text : le texte déjà chargé — le moyen le plus
      fiable, puisqu'il reflète EXACTEMENT ce que call_llm() enverra
      réellement (ex: agent.system_prompt sur une instance déjà créée).
    - prompt_file : un chemin de fichier, si le texte n'est pas encore
      chargé en mémoire (ex: script de diagnostic autonome qui
      n'instancie pas les agents).
    """
    if system_prompt_text is not None:
        return estimate_tokens(system_prompt_text)
    if prompt_file:
        return estimate_tokens(_read_prompt_file(prompt_file))
    return 0


def get_all_system_prompt_costs() -> dict:
    """
    Mesure le coût fixe de CHAQUE agent en instanciant réellement les
    agents et en lisant leur self.system_prompt — jamais un chiffre en
    dur. Reflète toujours l'état actuel des fichiers prompts/*.txt et du
    code (EmailAgent/PlanningAgent ont leur prompt codé en dur dans leur
    classe, pas dans un fichier séparé — instancier l'agent est donc la
    seule façon fiable de les mesurer aussi).

    Import différé (à l'intérieur de la fonction, pas en haut du fichier)
    pour éviter tout risque de dépendance circulaire avec agents/*, qui
    importe déjà des utilitaires de ce dossier.
    """
    from agents.commercial_agent import CommercialAgent
    from agents.email_agent import EmailAgent
    from agents.planning_agent import PlanningAgent
    from agents.reply_agent import ReplyAgent

    costs = {}

    for label, factory in [
        ("CommercialAgent", lambda: CommercialAgent()),
        ("EmailAgent", lambda: EmailAgent()),
        ("PlanningAgent", lambda: PlanningAgent()),
        ("ReplyAgent (business)", lambda: ReplyAgent(persona="business")),
        ("ReplyAgent (personal)", lambda: ReplyAgent(persona="personal")),
    ]:
        try:
            costs[label] = estimate_tokens(factory().system_prompt)
        except Exception as e:
            # Un prompt manquant/mal formé ne doit pas faire planter tout
            # le diagnostic — on affiche l'erreur pour CET agent et on
            # continue les autres.
            costs[label] = {"error": str(e)}

    # OrchestratorAgent : system_prompt = "" (classification via
    # call_llm_raw, sans system prompt) — vérifié dynamiquement plutôt
    # que supposé, au cas où ça change un jour.
    try:
        from agents.orchestrator_agent import OrchestratorAgent
        costs["OrchestratorAgent"] = estimate_tokens(OrchestratorAgent.system_prompt)
    except Exception as e:
        costs["OrchestratorAgent"] = {"error": str(e)}

    return costs


def estimate_history_cost(history: list) -> int:
    """
    Estime le coût de l'historique de conversation (commercial_history ou
    équivalent) — liste de dicts {"role": ..., "content": ...}.
    """
    if not history:
        return 0
    return sum(estimate_tokens(m.get("content", "")) for m in history)


def estimate_call_breakdown(
    system_prompt_text: str,
    history: list = None,
    rag_context: str = "",
    user_message: str = "",
) -> dict:
    """
    Décompose l'estimation d'un appel à venir en 4 blocs, pour comprendre
    D'OÙ vient le coût avant même de contacter Ollama :
    system prompt / historique / contexte RAG / message utilisateur.

    Outil de diagnostic admin — ne remplace jamais le compte réel
    (prompt_eval_count) retourné après l'appel, qui reste la seule
    source fiable pour la facturation du client.
    """
    system_cost = estimate_tokens(system_prompt_text)
    history_cost = estimate_history_cost(history)
    rag_cost = estimate_tokens(rag_context)
    message_cost = estimate_tokens(user_message)

    return {
        "system_prompt": system_cost,
        "history": history_cost,
        "rag_context": rag_cost,
        "user_message": message_cost,
        "estimated_total": system_cost + history_cost + rag_cost + message_cost,
    }


if __name__ == "__main__":
    # Diagnostic rapide en ligne de commande : python -m utils.token_estimator
    print("Estimation du coût fixe (system prompt) par agent — approximation")
    print("=" * 70)

    costs = get_all_system_prompt_costs()

    def _sort_key(item):
        _, cost = item
        return (isinstance(cost, dict), -cost if isinstance(cost, int) else 0)

    for agent, cost in sorted(costs.items(), key=_sort_key):
        if isinstance(cost, dict):
            print(f"{agent:<30} ERREUR : {cost['error']}")
        else:
            print(f"{agent:<30} ~{cost} tokens (à chaque appel)")

    print("\nRappel : approximation par caractères (chars/4), pas le vrai")
    print("tokenizer Qwen. Marge d'erreur réaliste : +/- 15-20%.")