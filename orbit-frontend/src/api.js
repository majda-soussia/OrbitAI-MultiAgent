const API_BASE = "http://localhost:8000";

// ---------------------------------------------------------------------
// Low-level helper: attaches the Authorization header automatically
// when a token is provided. All protected routes (admin/*, chat when
// logged in, oauth/*) go through this instead of raw fetch().
// ---------------------------------------------------------------------
async function authFetch(path, { method = "GET", token = null, body = null } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    let detail = `Erreur API: ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // response wasn't JSON — keep the generic message
    }
    throw new Error(detail);
  }

  return res.json();
}

// ---------------------------------------------------------------------
// AUTH
// ---------------------------------------------------------------------

export async function signup(email, password, plan = "standard") {
  return authFetch("/api/auth/signup", { method: "POST", body: { email, password, plan } });
}

export async function login(email, password) {
  return authFetch("/api/auth/login", { method: "POST", body: { email, password } });
}

export async function verifyEmail(token) {
  return authFetch(`/api/auth/verify-email?token=${encodeURIComponent(token)}`);
}

export async function getCurrentUser(token) {
  return authFetch("/api/auth/me", { token });
}

// ---------------------------------------------------------------------
// CHAT
// ---------------------------------------------------------------------
// client_email is intentionally not a parameter anymore: the backend
// derives the user solely from the JWT (if provided). Passing no token
// at all uses the guest trial mode handled server-side.
export async function sendChatMessage(sessionId, message, token = null) {
  return authFetch("/api/chat", {
    method: "POST",
    token,
    body: { session_id: sessionId, message },
  });
}

// ---------------------------------------------------------------------
// GOOGLE OAUTH
// ---------------------------------------------------------------------

export async function getGoogleAuthorizationUrl(token) {
  return authFetch("/api/oauth/google/connect", { token });
}

export async function getGoogleStatus(token) {
  return authFetch("/api/oauth/google/status", { token });
}

export async function disconnectGoogle(token) {
  return authFetch("/api/oauth/google/disconnect", { method: "DELETE", token });
}

// ---------------------------------------------------------------------
// ADMIN (all require an admin JWT now)
// ---------------------------------------------------------------------

export async function getTokenSummary(token) {
  return authFetch("/api/admin/tokens", { token });
}

export async function getSessions(token) {
  return authFetch("/api/admin/sessions", { token });
}

export async function getDebugStatus(token) {
  return authFetch("/api/admin/debug", { token });
}

export async function setDebugStatus(enabled, token) {
  return authFetch("/api/admin/debug", { method: "POST", token, body: { enabled } });
}

export async function getClients(token) {
  return authFetch("/api/admin/clients", { token });
}

export async function setClientPlan(clientEmail, plan, token) {
  return authFetch("/api/admin/set_plan", {
    method: "POST",
    token,
    body: { client_email: clientEmail, plan },
  });
}