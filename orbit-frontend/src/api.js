const API_BASE = "http://localhost:8000";
const ACCESS_TOKEN_KEY = "orbit_access_token";
const REFRESH_TOKEN_KEY = "orbit_refresh_token";
let onTokenRefreshed = null;
let onAuthExpired = null;
export function setAuthCallbacks({ onRefreshed, onExpired } = {}) {
  onTokenRefreshed = onRefreshed || null;
  onAuthExpired = onExpired || null;
}
export function getStoredAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setStoredTokens(accessToken, refreshToken) {
  if (accessToken) localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
  if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearStoredTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
}
// ---------------------------------------------------------------------
// Low-level helper: attaches the Authorization header automatically
// when a token is provided. All protected routes (admin/*, chat when
// logged in, oauth/*) go through this instead of raw fetch().
// ---------------------------------------------------------------------
async function rawFetch(path, { method, token, body }) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  return fetch(`${API_BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
}

async function tryRefreshAccessToken() {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
  if (!refreshToken) return null;

  try {
    const res = await rawFetch("/api/auth/refresh", {
      method: "POST",
      token: null,
      body: { refresh_token: refreshToken },
    });
    if (!res.ok) return null;

    const data = await res.json();
    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
    onTokenRefreshed?.(data.access_token);
    return data.access_token;
  } catch {
    return null;
  }
}
async function authFetch(path, { method = "GET", token = null, body = null } = {}) {
  let res = await rawFetch(path, { method, token, body });

  if (res.status === 401 && token) {
    const newToken = await tryRefreshAccessToken();

    if (newToken) {
      res = await rawFetch(path, { method, token: newToken, body });
    } else {
      onAuthExpired?.();
    }
  }

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
  const data = await authFetch("/api/auth/login", { method: "POST", body: { email, password } });
  setStoredTokens(data.access_token, data.refresh_token);
  return data;
}

export async function verifyEmail(token) {
  return authFetch(`/api/auth/verify-email?token=${encodeURIComponent(token)}`);
}

export async function getCurrentUser(token) {
  return authFetch("/api/auth/me", { token });
}

export async function forgotPassword(email) {
  return authFetch("/api/auth/forgot-password", { method: "POST", body: { email } });
}

export async function resetPassword(resetToken, newPassword) {
  return authFetch("/api/auth/reset-password", {
    method: "POST",
    body: { token: resetToken, new_password: newPassword },
  });
}


// ---------------------------------------------------------------------
// CHAT
// ---------------------------------------------------------------------
export async function sendChatMessage(sessionId, message, token = null) {
  return authFetch("/api/chat", {
    method: "POST",
    token,
    body: { session_id: sessionId, message },
  });
}
export async function resetConversation(sessionId, token) {
  return authFetch("/api/chat/reset", {
    method: "POST",
    token,
    body: { session_id: sessionId },
  });
}

export async function getMemoryStatus(token) {
  return authFetch("/api/chat/memory", { token });
}

export async function setMemoryEnabled(enabled, token) {
  return authFetch("/api/chat/memory", {
    method: "POST",
    token,
    body: { enabled },
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

export async function getUsageByClient(token) {
  return authFetch("/api/admin/usage_by_client", { token });
}

export async function setClientPlan(clientEmail, plan, token) {
  return authFetch("/api/admin/set_plan", {
    method: "POST",
    token,
    body: { client_email: clientEmail, plan },
  });
}
export async function resetClientQuota(clientEmail, token) {
  return authFetch("/api/admin/reset_quota", {
    method: "POST",
    token,
    body: { client_email: clientEmail },
  });
}

export async function getClientDetail(clientEmail, token) {
  return authFetch(`/api/admin/clients/${encodeURIComponent(clientEmail)}/detail`, { token });
}
export async function resetClientHistory(clientEmail, token) {
  return authFetch(`/api/admin/clients/${encodeURIComponent(clientEmail)}/reset_history`, {
    method: "POST",
    token,
  });
}

export async function toggleClientMemory(clientEmail, enabled, token) {
  return authFetch(`/api/admin/clients/${encodeURIComponent(clientEmail)}/toggle_memory`, {
    method: "POST",
    token,
    body: { enabled },
  });
}
// ---------------------------------------------------------------------
// RAG SOURCES
// ---------------------------------------------------------------------

export async function getRagSources(token) {
  return authFetch("/api/admin/rag/sources", { token });
}

export async function deleteRagSource(filename, token) {
  return authFetch(`/api/admin/rag/sources/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    token,
  });
}

export async function reindexRagSources(token) {
  return authFetch("/api/admin/rag/reindex", { method: "POST", token });
}

// Upload utilise FormData, donc on ne passe pas par authFetch (qui force JSON).
export async function uploadRagSource(file, token) {
  const formData = new FormData();
  formData.append("file", file);

  let res = await fetch(`${API_BASE}/api/admin/rag/sources`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });

  if (res.status === 401) {
    const newToken = await tryRefreshAccessToken();
    if (newToken) {
      res = await fetch(`${API_BASE}/api/admin/rag/sources`, {
        method: "POST",
        headers: { Authorization: `Bearer ${newToken}` },
        body: formData,
      });
    } else {
      onAuthExpired?.();
    }
  }

  if (!res.ok) {
    let detail = `Erreur API: ${res.status}`;
    try {
      const data = await res.json();
      if (data?.detail) detail = data.detail;
    } catch {
      // pas de JSON dans la réponse
    }
    throw new Error(detail);
  }

  return res.json();
}

// ---------------------------------------------------------------------
// TOKENS — évolution dans le temps + coût
// ---------------------------------------------------------------------

export async function getTokensTimeseries(days = 30, token) {
  return authFetch(`/api/admin/tokens/timeseries?days=${days}`, { token });
}

export async function getTokensCost(token) {
  return authFetch("/api/admin/tokens/cost", { token });
}

export async function getTokenPrice(token) {
  return authFetch("/api/admin/tokens/price", { token });
}

export async function setTokenPrice(pricePer1k, currency, token) {
  return authFetch("/api/admin/tokens/price", {
    method: "POST",
    token,
    body: { price_per_1k_tokens: pricePer1k, currency },
  });
}

export async function inspectTokens(text, token) {
  return authFetch("/api/admin/tokens/inspect", {
    method: "POST",
    token,
    body: { text },
  });
}