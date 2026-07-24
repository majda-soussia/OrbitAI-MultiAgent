import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.orchestrator_agent import OrchestratorAgent
from utils.token_tracker import get_summary
from utils.settings import is_debug_enabled, set_debug
from utils.token_tracker import get_summary, get_last_call_tokens
from utils.client_memory import get_client_memory, save_client_turn, check_quota, add_client_tokens, set_client_plan, get_all_clients
app = FastAPI(title="Orbit AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
class PlanUpdate(BaseModel):
    client_email: str
    plan: str  # "standard" ou "premium"

@app.post("/api/admin/set_plan")
def admin_set_plan(payload: PlanUpdate):
    if payload.plan not in ("standard", "premium"):
        raise HTTPException(status_code=400, detail="Plan invalide.")
    set_client_plan(payload.client_email, payload.plan)
    return {"client": payload.client_email, "plan": payload.plan}

@app.get("/api/admin/clients")
def admin_clients():
    """Liste tous les clients avec leur plan et consommation."""
    return get_all_clients()
# --- Sessions client : une instance d'orchestrateur par session ---
sessions: dict[str, OrchestratorAgent] = {}


def get_or_create_session(session_id: str) -> OrchestratorAgent:
    if session_id not in sessions:
        sessions[session_id] = OrchestratorAgent()
    return sessions[session_id]


class ChatRequest(BaseModel):
    session_id: str | None = None
    client_email: str | None = None
    message: str


class ChatResponse(BaseModel):
    session_id: str
    agent: str
    response: str
    quota: dict | None = None

def _format_response_text(agent: str, response) -> str:
    """
    Certains agents (ex: Email Agent) renvoient une liste de dicts
    plutôt qu'un texte brut. On uniformise ici pour que ChatResponse
    reçoive toujours une string, quel que soit l'agent appelé.
    """
    if isinstance(response, str):
        return response

    if isinstance(response, list):
        if not response:
            return "Aucun résultat trouvé."
        lines = []
        for item in response:
            if isinstance(item, dict):
                sender = item.get("sender", "?")
                subject = item.get("subject", "(sans sujet)")
                priority = item.get("priority", "")
                summary = item.get("summary", "")
                lines.append(
                    f"— [{priority}] {subject} (de {sender})\n{summary}"
                )
            else:
                lines.append(str(item))
        return "\n\n".join(lines)

    return str(response)

QUOTA_REFUSAL = (
    "Thank you for your interest in Orbit solutions. "
    "You have reached the message limit for your current plan. "
    "Please contact our team at contact@orbitsolutions.tn to upgrade "
    "to a Premium plan and continue the conversation."
)

@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest):
    session_id = payload.session_id or str(uuid.uuid4())
    is_new_session = session_id not in sessions
    orchestrator = get_or_create_session(session_id)

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Message vide.")

    if is_new_session and payload.client_email:
        memory = get_client_memory(payload.client_email)
        orchestrator.commercial_history = memory["history"].copy()
        orchestrator.client_email = payload.client_email
        
    # --- Vérification du quota AVANT d'appeler le LLM ---
    quota_status = None
    if payload.client_email:
        quota_status = check_quota(payload.client_email)
        if not quota_status["allowed"]:
            return ChatResponse(
                session_id=session_id,
                agent="quota",
                response=QUOTA_REFUSAL,
                quota=quota_status,
            )

    result = orchestrator.run(payload.message)
    response_text = _format_response_text(result["agent"], result["response"])

    if payload.client_email and result["agent"] == "commercial":
        save_client_turn(payload.client_email, payload.message, response_text)
        # Compte les tokens réellement consommés par cet échange
        tokens_this_call = get_last_call_tokens()
        add_client_tokens(payload.client_email, tokens_this_call)
        quota_status = check_quota(payload.client_email)

    return ChatResponse(
        session_id=session_id,
        agent=result["agent"],
        response=response_text,
        quota=quota_status,
    )
ALL_AGENTS = ["CommercialAgent", "EmailAgent", "PlanningAgent", "ReplyAgent", "OrchestratorAgent"]

@app.get("/api/admin/tokens")
def admin_tokens():
    summary = get_summary()
    for agent in ALL_AGENTS:
        if agent not in summary["by_agent"]:
            summary["by_agent"][agent] = 0
    return summary

@app.get("/api/admin/debug")
def admin_get_debug():
    return {"debug": is_debug_enabled()}


class DebugToggle(BaseModel):
    enabled: bool


@app.post("/api/admin/debug")
def admin_set_debug(payload: DebugToggle):
    set_debug(payload.enabled)
    return {"debug": is_debug_enabled()}


@app.get("/api/admin/sessions")
def admin_sessions():
    return {
        sid: {
            "messages": len(orch.commercial_history),
            "email": getattr(orch, "client_email", None),
        }
        for sid, orch in sessions.items()
    }
@app.get("/api/admin/clients")
def admin_clients():
    from utils.client_memory import get_all_clients, _load_plans
    clients = get_all_clients()
    plans = _load_plans()
    result = {}
    for email, profile in clients.items():
        plan_name = profile.get("plan", "standard")
        token_limit = int(plans.get(plan_name, {}).get("token_limit", 5000))
        tokens_used = int(profile.get("tokens_used", 0) or 0)
        result[email] = {
            "plan": plan_name,
            "tokens_used": tokens_used,
            "token_limit": token_limit,
            "remaining": max(0, token_limit - tokens_used),
            "last_seen": profile.get("last_seen") or "—",
        }
    return result