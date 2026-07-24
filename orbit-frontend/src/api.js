const API_BASE = "http://localhost:8000";

export async function sendChatMessage(sessionId, message, clientEmail) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, message, client_email: clientEmail }),
  });
  if (!res.ok) throw new Error(`Erreur API: ${res.status}`);
  return res.json();
}

export async function getTokenSummary() {
  const res = await fetch(`${API_BASE}/api/admin/tokens`);
  return res.json();
}

export async function getSessions() {
  const res = await fetch(`${API_BASE}/api/admin/sessions`);
  return res.json();
}

export async function getDebugStatus() {
  const res = await fetch(`${API_BASE}/api/admin/debug`);
  return res.json();
}

export async function setDebugStatus(enabled) {
  const res = await fetch(`${API_BASE}/api/admin/debug`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  return res.json();
}
export async function getClients() {
  const res = await fetch(`${API_BASE}/api/admin/clients`);
  return res.json();
}

export async function setClientPlan(clientEmail, plan) {
  const res = await fetch(`${API_BASE}/api/admin/set_plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ client_email: clientEmail, plan }),
  });
  return res.json();
}