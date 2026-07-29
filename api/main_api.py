import uuid
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from agents.orchestrator_agent import OrchestratorAgent
from utils.token_tracker import get_summary, get_last_call_tokens
from utils.settings import is_debug_enabled, set_debug
from utils.client_memory import (
    get_client_memory, save_client_turn, check_quota,
    add_client_tokens, set_client_plan, get_all_clients,
)
from utils import auth as auth_module
from utils.auth import AuthError
from utils import google_oauth
from utils.google_oauth import GoogleOAuthError
from agents.email_agent import EmailAgent
from agents.planning_agent import PlanningAgent
app = FastAPI(title="Orbit AI Assistant API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================
# AUTH — signup / login / email verification / token refresh
# =========================================================================

bearer_scheme = HTTPBearer()
# auto_error=False: if no Authorization header is sent, this resolves
# to None instead of raising 401 — used by /api/chat to allow a short
# unauthenticated trial before requiring a real account.
optional_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    """
    FastAPI dependency: extracts and validates the JWT access token from
    the Authorization header, and returns the current user's info.
    Use this to protect any route that requires a logged-in user.
    """
    try:
        return auth_module.get_current_user(credentials.credentials)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_bearer_scheme),
) -> dict | None:
    """
    Same as get_current_user, but returns None if no Authorization
    header was sent at all (guest mode). If a header IS present but
    the token is invalid/expired, this still raises 401 — a bad token
    is treated as an error, not silently downgraded to guest mode.
    """
    if credentials is None:
        return None
    try:
        return auth_module.get_current_user(credentials.credentials)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    FastAPI dependency: same as get_current_user, but additionally
    requires is_admin=True. Use this on every /api/admin/* route.
    """
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


class SignupRequest(BaseModel):
    email: str
    password: str
    plan: str = "standard"


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/api/auth/signup")
def signup(payload: SignupRequest):
    try:
        return auth_module.signup(payload.email, payload.password, payload.plan)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    try:
        return auth_module.login(payload.email, payload.password)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/auth/verify-email")
def verify_email(token: str):
    try:
        return auth_module.verify_email(token)
    except AuthError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/auth/refresh")
def refresh_token(payload: RefreshRequest):
    try:
        return auth_module.refresh_access_token(payload.refresh_token)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e))


@app.get("/api/auth/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user


# =========================================================================
# GOOGLE OAUTH — per-user Gmail/Calendar connection
# =========================================================================

@app.get("/api/oauth/google/connect")
def google_oauth_connect(current_user: dict = Depends(get_current_user)):
    """
    Returns the Google authorization URL for the current logged-in user.
    The frontend should redirect the browser to this URL (or open it in
    a popup) so the user can grant Gmail/Calendar access.
    """
    url = google_oauth.build_authorization_url(current_user["id"])
    return {"authorization_url": url}


@app.get("/api/oauth/google/callback")
def google_oauth_callback(code: str, state: str):
    """
    Called by Google after the user grants (or denies) access. This
    route is intentionally NOT protected by our own JWT — the request
    comes from the user's browser being redirected by Google, not from
    an API client carrying an Authorization header. The `state` value
    itself is what proves which of our users this belongs to.
    """
    try:
        result = google_oauth.exchange_code_for_tokens(code, state)
    except GoogleOAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # In a real deployment, redirect back to a frontend page instead of
    # returning raw JSON (e.g. RedirectResponse to FRONTEND_URL + "/settings?google=connected").
    # Kept as JSON for now since the frontend flow isn't built yet.
    return result


@app.get("/api/oauth/google/status")
def google_oauth_status(current_user: dict = Depends(get_current_user)):
    return {"connected": google_oauth.is_google_connected(current_user["id"])}


@app.delete("/api/oauth/google/disconnect")
def google_oauth_disconnect(current_user: dict = Depends(get_current_user)):
    google_oauth.disconnect_google(current_user["id"])
    return {"message": "Google account disconnected."}


# =========================================================================
# PER-USER AGENTS — Email & Planning, using each user's own connected
# Google account instead of the shared dev token.
# =========================================================================

def _require_google_connected(user_id: int):
    if not google_oauth.is_google_connected(user_id):
        raise HTTPException(
            status_code=400,
            detail="Google account not connected. Call /api/oauth/google/connect first.",
        )


@app.get("/api/agents/email/run")
def run_email_agent(
    max_results: int = 5,
    query: str | None = None,
    current_user: dict = Depends(get_current_user),
):
    _require_google_connected(current_user["id"])
    agent = EmailAgent()
    return agent.run_for_user(current_user["id"], max_results=max_results, query=query)


@app.get("/api/agents/planning/run")
def run_planning_agent(current_user: dict = Depends(get_current_user)):
    _require_google_connected(current_user["id"])
    agent = PlanningAgent()
    return agent.run_for_user(current_user["id"])


# =========================================================================
# ADMIN — all routes below now require a valid admin JWT
# =========================================================================
class PlanUpdate(BaseModel):
    client_email: str
    plan: str  # "standard" or "premium"


@app.post("/api/admin/set_plan")
def admin_set_plan(payload: PlanUpdate, _admin: dict = Depends(require_admin)):
    if payload.plan not in ("standard", "premium"):
        raise HTTPException(status_code=400, detail="Invalid plan.")
    set_client_plan(payload.client_email, payload.plan)
    return {"client": payload.client_email, "plan": payload.plan}


@app.get("/api/admin/clients")
def admin_clients(_admin: dict = Depends(require_admin)):
    """Lists all clients with their plan and token consumption."""
    from utils.client_memory import _load_plans

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


ALL_AGENTS = ["CommercialAgent", "EmailAgent", "PlanningAgent", "ReplyAgent", "OrchestratorAgent"]


@app.get("/api/admin/tokens")
def admin_tokens(_admin: dict = Depends(require_admin)):
    summary = get_summary()
    for agent in ALL_AGENTS:
        if agent not in summary["by_agent"]:
            summary["by_agent"][agent] = 0
    return summary


@app.get("/api/admin/debug")
def admin_get_debug(_admin: dict = Depends(require_admin)):
    return {"debug": is_debug_enabled()}


class DebugToggle(BaseModel):
    enabled: bool


@app.post("/api/admin/debug")
def admin_set_debug(payload: DebugToggle, _admin: dict = Depends(require_admin)):
    set_debug(payload.enabled)
    return {"debug": is_debug_enabled()}


@app.get("/api/admin/sessions")
def admin_sessions(_admin: dict = Depends(require_admin)):
    return {
        sid: {
            "messages": len(orch.commercial_history),
            "email": getattr(orch, "client_email", None),
        }
        for sid, orch in sessions.items()
    }


# =========================================================================
# CHAT — guest trial mode (no account) + authenticated mode (JWT-backed,
# PostgreSQL-backed history/quota via client_memory.py).
# =========================================================================

sessions: dict[str, OrchestratorAgent] = {}


def get_or_create_session(session_id: str) -> OrchestratorAgent:
    if session_id not in sessions:
        sessions[session_id] = OrchestratorAgent()
    return sessions[session_id]


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str
    # client_email is intentionally NOT a field here anymore: trusting a
    # free-text email from the client was a security hole (anyone could
    # impersonate another client's quota/history). The email now comes
    # exclusively from the authenticated JWT, if one is provided.


class ChatResponse(BaseModel):
    session_id: str
    agent: str
    response: str
    quota: dict | None = None


def _format_response_text(agent: str, response) -> str:
    """
    Some agents (e.g. Email Agent) return a list of dicts instead of
    plain text. We normalize here so ChatResponse always receives a
    string, whichever agent was called.
    """
    if isinstance(response, str):
        return response

    if isinstance(response, list):
        if not response:
            return "No results found."
        lines = []
        for item in response:
            if isinstance(item, dict):
                sender = item.get("sender", "?")
                subject = item.get("subject", "(no subject)")
                priority = item.get("priority", "")
                summary = item.get("summary", "")
                lines.append(f"— [{priority}] {subject} (from {sender})\n{summary}")
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

# --- Guest (unauthenticated) trial mode ---
# A visitor can try the chat for a few messages without an account.
# Past that, they must sign up and log in to continue. This counter is
# in-memory only (reset on server restart), which is fine for a trial
# limit — it does not need to survive restarts or scale across workers.
GUEST_MESSAGE_LIMIT = 5
guest_message_counts: dict[str, int] = {}

GUEST_QUOTA_REFUSAL = (
    "Thanks for trying Orbit AI Assistant! You've used your "
    f"{GUEST_MESSAGE_LIMIT} free trial messages. "
    "Please sign up (or log in if you already have an account) to keep chatting "
    "and unlock your full plan."
)


@app.post("/api/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    current_user: dict | None = Depends(get_current_user_optional),
):
    session_id = payload.session_id or str(uuid.uuid4())
    is_new_session = session_id not in sessions
    orchestrator = get_or_create_session(session_id)

    if not payload.message.strip():
        raise HTTPException(status_code=400, detail="Empty message.")

    # ---------------------------------------------------------------
    # GUEST MODE: no valid JWT provided. Allow a short unauthenticated
    # trial, then require signup/login.
    # ---------------------------------------------------------------
    if current_user is None:
        messages_used = guest_message_counts.get(session_id, 0)

        if messages_used >= GUEST_MESSAGE_LIMIT:
            return ChatResponse(
                session_id=session_id,
                agent="guest_quota",
                response=GUEST_QUOTA_REFUSAL,
                quota={
                    "allowed": False,
                    "plan": "guest",
                    "tokens_used": messages_used,
                    "token_limit": GUEST_MESSAGE_LIMIT,
                    "remaining": 0,
                },
            )

        result = orchestrator.run(payload.message)
        response_text = _format_response_text(result["agent"], result["response"])

        guest_message_counts[session_id] = messages_used + 1
        remaining = GUEST_MESSAGE_LIMIT - guest_message_counts[session_id]

        return ChatResponse(
            session_id=session_id,
            agent=result["agent"],
            response=response_text,
            quota={
                "allowed": True,
                "plan": "guest",
                "tokens_used": guest_message_counts[session_id],
                "token_limit": GUEST_MESSAGE_LIMIT,
                "remaining": remaining,
            },
        )

    # ---------------------------------------------------------------
    # AUTHENTICATED MODE: client_email comes ONLY from the verified
    # JWT — never from client-supplied data. This is the fix for the
    # impersonation issue in the previous version of this route.
    # ---------------------------------------------------------------
    client_email = current_user["email"]

    if is_new_session:
        memory = get_client_memory(client_email)
        orchestrator.commercial_history = memory["history"].copy()
        orchestrator.client_email = client_email

    quota_status = check_quota(client_email)
    if not quota_status["allowed"]:
        return ChatResponse(
            session_id=session_id,
            agent="quota",
            response=QUOTA_REFUSAL,
            quota=quota_status,
        )

    result = orchestrator.run(payload.message)
    response_text = _format_response_text(result["agent"], result["response"])

    if result["agent"] == "commercial":
        save_client_turn(client_email, payload.message, response_text)
        # Count tokens actually consumed by this exchange
        tokens_this_call = get_last_call_tokens()
        add_client_tokens(client_email, tokens_this_call)
        quota_status = check_quota(client_email)

    return ChatResponse(
        session_id=session_id,
        agent=result["agent"],
        response=response_text,
        quota=quota_status,
    )