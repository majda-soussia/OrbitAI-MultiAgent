import { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import {
  getGoogleAuthorizationUrl,
  getGoogleStatus,
  disconnectGoogle,
} from "../api";
import { useAuth } from "../context/AuthContext";

const API_BASE = "http://localhost:8000";

export default function IntegrationsPage() {
  const { accessToken } = useAuth();
 
  const [connected, setConnected] = useState(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [error, setError] = useState(null);
 
  const [emailResults, setEmailResults] = useState(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailError, setEmailError] = useState(null);
 
  const [planningResult, setPlanningResult] = useState(null);
  const [planningLoading, setPlanningLoading] = useState(false);
  const [planningError, setPlanningError] = useState(null);
  const [searchParams, setSearchParams] = useSearchParams();

  async function checkGoogleStatus() {
    if (!accessToken) {
      setLoadingStatus(false);
      return;
    }
    setLoadingStatus(true);
    try {
      const data = await getGoogleStatus(accessToken);
      setConnected(data.connected);
    } catch (err) {
      setError(err.message || "Unable to verify Google status.");
    } finally {
      setLoadingStatus(false);
    }
  }

  useEffect(() => {
    const googleStatus = searchParams.get("google");
    if (googleStatus === "connected") {
      checkGoogleStatus();
      setSearchParams({});
    } else if (googleStatus === "error") {
      setError(searchParams.get("detail") || "Google connection failed.");
      setSearchParams({});
    }
  }, [searchParams]);

  useEffect(() => {
    checkGoogleStatus();
  }, [accessToken]);

  async function handleConnect() {
    setError(null);
    try {
      const { authorization_url } = await getGoogleAuthorizationUrl(accessToken);
      window.location.href = authorization_url;
    } catch (err) {
      setError(err.message || "Unable to start Google authentication.");
    }
  }

  async function handleDisconnect() {
    try {
      await disconnectGoogle(accessToken);
      setConnected(false);
      setEmailResults(null);
      setPlanningResult(null);
    } catch (err) {
      setError(err.message ||"Unable to disconnect your Google account.");
    }
  }

  async function handleRunEmailAgent() {
    setEmailLoading(true);
    setEmailError(null);
    setEmailResults(null);
    try {
      const res = await fetch(`${API_BASE}/api/agents/email/run?max_results=5`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `API Error: ${res.status}`);
      }
      setEmailResults(await res.json());
    } catch (err) {
      setEmailError(err.message);
    } finally {
      setEmailLoading(false);
    }
  }

  async function handleRunPlanningAgent() {
    setPlanningLoading(true);
    setPlanningError(null);
    setPlanningResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/agents/planning/run`, {
        headers: { Authorization: `Bearer ${accessToken}` },
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Erreur API: ${res.status}`);
      }
      setPlanningResult(await res.json());
    } catch (err) {
      setPlanningError(err.message);
    } finally {
      setPlanningLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <h1 style={{ margin: 0 }}>Integrations</h1>
      <p style={{ margin: "4px 0 24px", fontSize: 14, color: "#64748b" }}>
        Connect your Google account to use the Email and Planning agents.
      </p>

      {/* Connexion Google */}
      <div style={styles.card}>
        <h3 style={styles.cardTitle}>Google (Gmail & Calendar)</h3>

        {loadingStatus ? (
          <p style={{ color: "#64748b", fontSize: 14 }}>Checking connection status...</p>
        ) : error ? (
          <p style={{ color: "#dc2626", fontSize: 14 }}>{error}</p>
        ) : connected ? (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={styles.badgeConnected}>✓ Connected</span>
            <button style={styles.secondaryButton} onClick={handleDisconnect}>
              Disconnect
            </button>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={styles.badgeDisconnected}>Not connected</span>
            <button style={styles.button} onClick={handleConnect}>
              Connecter Google
            </button>
          </div>
        )}
      </div>

      {/* Email Agent */}
      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={styles.cardTitle}>Email Agent</h3>
          <button
            style={styles.button}
            onClick={handleRunEmailAgent}
            disabled={!connected || emailLoading}
          >
            {emailLoading ? "Analyzing..." : "Analyze my emails"}
          </button>
        </div>

        {!connected && (
          <p style={{ fontSize: 13, color: "#94a3b8" }}>Connect your Google account to use this agent.</p>
        )}
        {emailError && <p style={{ color: "#dc2626", fontSize: 14 }}>{emailError}</p>}

        {emailResults && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {emailResults.map((mail, i) => (
              <div key={i} style={styles.emailRow}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{mail.subject}</span>
                  <span style={priorityBadgeStyle(mail.priority)}>{mail.priority}</span>
                </div>
                <p style={{ margin: "0 0 4px", fontSize: 12, color: "#64748b" }}>{mail.sender}</p>
                <p style={{ margin: 0, fontSize: 13 }}>{mail.summary}</p>
                <span style={styles.categoryTag}>{mail.category}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Planning Agent */}
      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={styles.cardTitle}>Planning Agent</h3>
          <button
            style={styles.button}
            onClick={handleRunPlanningAgent}
            disabled={!connected || planningLoading}
          >
            {planningLoading ? "Generating..." : "Generate my briefing"}
          </button>
        </div>

        {!connected && (
          <p style={{ fontSize: 13, color: "#94a3b8" }}>Connect your Google account to use this agent.</p>
        )}
        {planningError && <p style={{ color: "#dc2626", fontSize: 14 }}>{planningError}</p>}

        {planningResult && (
          <div>
            <p style={{ whiteSpace: "pre-wrap", fontSize: 14, marginBottom: 12 }}>
              {planningResult.briefing}
            </p>
            {planningResult.conflicts?.length > 0 && (
              <div style={styles.conflictBox}>
                {planningResult.conflicts.map((c, i) => (
                  <p key={i} style={{ margin: "4px 0", fontSize: 13 }}>
                    ⚠ {c.event_a} ({c.time_a})overlaps with {c.event_b} ({c.time_b})
                  </p>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function priorityBadgeStyle(priority) {
  const colors = {
    High: { background: "#fef2f2", color: "#dc2626" },
    Medium: { background: "#fffbeb", color: "#d97706" },
    Low: { background: "#f1f5f9", color: "#64748b" },
  };
  return {
    ...(colors[priority] || colors.Low),
    fontSize: 11,
    fontWeight: 600,
    padding: "2px 8px",
    borderRadius: 6,
  };
}

const styles = {
  container: { padding: 30, fontFamily: "system-ui, sans-serif", maxWidth: 700, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 },
  card: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "16px 20px" },
  cardTitle: { margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: "#0f172a" },
  button: { padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", fontWeight: 600, cursor: "pointer", fontSize: 13 },
  secondaryButton: { padding: "8px 16px", borderRadius: 8, border: "1px solid #cbd5e1", background: "#fff", color: "#64748b", cursor: "pointer", fontSize: 13 },
  badgeConnected: { background: "#f0fdf4", color: "#16a34a", fontSize: 13, fontWeight: 600, padding: "4px 10px", borderRadius: 6 },
  badgeDisconnected: { background: "#f1f5f9", color: "#64748b", fontSize: 13, fontWeight: 600, padding: "4px 10px", borderRadius: 6 },
  emailRow: { border: "1px solid #f1f5f9", borderRadius: 8, padding: 12 },
  categoryTag: { display: "inline-block", marginTop: 6, fontSize: 11, background: "#eff6ff", color: "#2563eb", padding: "2px 8px", borderRadius: 6 },
  conflictBox: { background: "#fef2f2", borderRadius: 8, padding: 10, marginTop: 8 },
};