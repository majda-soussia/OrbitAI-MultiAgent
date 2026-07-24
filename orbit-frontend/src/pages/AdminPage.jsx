import { useState, useEffect } from "react";
import { getTokenSummary, getSessions, getDebugStatus, setDebugStatus, getClients, setClientPlan } from "../api";

export default function AdminPage() {
  const [tokens, setTokens] = useState(null);
  const [sessions, setSessions] = useState(null);
  const [debug, setDebug] = useState(false);
  const [clients, setClients] = useState(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    try {
      const [tokenData, sessionData, debugData, clientData] = await Promise.all([
        getTokenSummary(), getSessions(), getDebugStatus(), getClients(),
      ]);
      setTokens(tokenData);
      setSessions(sessionData);
      setDebug(debugData.debug);
      setClients(clientData);
    } catch (err) {
      console.error("Erreur chargement admin:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    (async () => { if (!cancelled) await refresh(); })();
    return () => { cancelled = true; };
  }, []);

  async function handleToggleDebug() {
    const result = await setDebugStatus(!debug);
    setDebug(result.debug);
  }

  async function handleUpgrade(email) {
    await setClientPlan(email, "premium");
    await refresh();
  }

  async function handleDowngrade(email) {
    await setClientPlan(email, "standard");
    await refresh();
  }

  if (loading) return <div style={styles.container}>Chargement...</div>;

  const maxTokens = Math.max(...Object.values(tokens.by_agent), 1);
  const agentColors = ["#2563eb", "#6366f1", "#8b5cf6", "#a78bfa", "#3b82f6"];

  const totalBudget = clients
    ? Object.values(clients).reduce((sum, c) => sum + (c.token_limit ?? 5000), 0)
    : 0;
  const totalUsed = clients
    ? Object.values(clients).reduce((sum, c) => sum + (c.tokens_used ?? 0), 0)
    : 0;

  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <div>
          <h1 style={{ margin: 0 }}>Orbit admin dashboard</h1>
          <p style={{ margin: "4px 0 0", fontSize: 14, color: "#64748b" }}>
            Vue d'ensemble de l'activité des agents en temps réel
          </p>
        </div>
        <button style={styles.refreshBtn} onClick={refresh}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 6 }}><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          Rafraîchir
        </button>
      </div>

      {/* Métriques */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </div>
          <p style={styles.metricLabel}>Appels LLM</p>
          <p style={styles.metricValue}>{tokens.total_calls}</p>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><circle cx="8" cy="8" r="6"/><circle cx="16" cy="16" r="6" opacity="0.5"/></svg>
          </div>
          <p style={styles.metricLabel}>Tokens totaux</p>
          <p style={styles.metricValue}>{tokens.total_tokens.toLocaleString()}</p>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <p style={styles.metricLabel}>Sessions actives</p>
          <p style={styles.metricValue}>{Object.keys(sessions).length}</p>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><rect x="8" y="6" width="8" height="14" rx="4"/><path d="M19 8h2M19 12h3M19 16h2M3 8h2M2 12h3M3 16h2M9 4l1 2M14 4l-1 2"/></svg>
          </div>
          <p style={styles.metricLabel}>Debug mode</p>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <div onClick={handleToggleDebug} style={{ ...styles.toggle, background: debug ? "#2563eb" : "#e2e8f0", cursor: "pointer" }}>
              <div style={{ ...styles.toggleThumb, transform: debug ? "translateX(20px)" : "translateX(2px)" }} />
            </div>
            <span style={{ fontSize: 13, color: debug ? "#2563eb" : "#64748b", fontWeight: 500 }}>
              {debug ? "Activé" : "Désactivé"}
            </span>
          </div>
        </div>
      </div>

      {/* Budget tokens clients */}
      {clients && Object.keys(clients).length > 0 && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Budget de tokens clients</h3>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13, color: "#64748b", marginBottom: 6 }}>
            <span>{totalUsed.toLocaleString()} tokens utilisés</span>
            <span>{totalBudget.toLocaleString()} budget total</span>
          </div>
          <div style={styles.barTrackLarge}>
            <div style={{
              width: `${Math.min(100, (totalUsed / totalBudget) * 100)}%`,
              height: "100%",
              background: totalUsed / totalBudget > 0.9 ? "#ef4444" : "#2563eb",
              borderRadius: 6,
              transition: "width 0.3s ease",
            }} />
          </div>
        </div>
      )}

      {/* Tokens par agent */}
      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={styles.cardTitle}>Tokens par agent</h3>
          <span style={{ fontSize: 13, color: "#94a3b8" }}>{Object.keys(tokens.by_agent).length} agents</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {Object.entries(tokens.by_agent).map(([agent, count], i) => (
            <div key={agent} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: agentColors[i % agentColors.length], flexShrink: 0 }} />
              <span style={styles.agentLabel}>{agent.replace("Agent", "")}</span>
              <div style={styles.barTrack}>
                <div style={{
                  width: `${(count / maxTokens) * 100}%`,
                  height: "100%",
                  background: agentColors[i % agentColors.length],
                  borderRadius: 4,
                }} />
              </div>
              <span style={styles.barValue}>{count.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Sessions actives */}
      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={styles.cardTitle}>Sessions actives</h3>
          <span style={{ fontSize: 13, color: "#94a3b8" }}>{Object.keys(sessions).length} en cours</span>
        </div>
        {Object.entries(sessions).map(([sid, data]) => (
          <div key={sid} style={styles.sessionRow}>
            <div>
              <p style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>
                {data.email || "Anonyme"}
              </p>
              <p style={{ margin: 0, fontSize: 12, color: "#94a3b8", fontFamily: "monospace" }}>
                {sid.slice(0, 13)}...
              </p>
            </div>
            <span style={{ fontSize: 13, color: "#64748b" }}>
              {data.messages} message{data.messages !== 1 ? "s" : ""}
            </span>
          </div>
        ))}
      </div>

      {/* Clients connus */}
      {clients && Object.keys(clients).length > 0 && (
        <div style={styles.card}>
          <h3 style={styles.cardTitle}>Clients</h3>
          {Object.entries(clients).map(([email, profile]) => (
            <div key={email} style={styles.clientRow}>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <span style={{ fontSize: 14, fontWeight: 500 }}>{email}</span>
                  <span style={profile.plan === "premium" ? styles.badgePremium : styles.badgeStandard}>
                    {profile.plan}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ ...styles.barTrack, flex: 1 }}>
                    <div style={{
                      width: `${Math.min(100, ((profile.tokens_used ?? 0) / (profile.token_limit ?? 5000)) * 100)}%`,
                      height: "100%",
                      background: (profile.remaining ?? 1) === 0 ? "#ef4444" : "#2563eb",
                      borderRadius: 4,
                    }} />
                  </div>
                  <span style={{ fontSize: 12, color: "#64748b", whiteSpace: "nowrap" }}>
                    {(profile.tokens_used ?? 0).toLocaleString()} / {(profile.token_limit ?? 5000).toLocaleString()}
                  </span>
                </div>
              </div>
              <div style={{ display: "flex", gap: 6, marginLeft: 12 }}>
                {profile.plan === "standard" ? (
                  <button style={styles.upgradeBtn} onClick={() => handleUpgrade(email)}>
                    → Premium
                  </button>
                ) : (
                  <button style={styles.downgradeBtn} onClick={() => handleDowngrade(email)}>
                    → Standard
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  container: { padding: 30, fontFamily: "system-ui, sans-serif", maxWidth: 900, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 },
  headerRow: { display: "flex", justifyContent: "space-between", alignItems: "flex-start" },
  metricsGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12 },
  metricCard: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 10, padding: "16px 20px" },
  metricIconWrap: { width: 32, height: 32, borderRadius: 8, background: "#eff6ff", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 10 },
  metricLabel: { fontSize: 13, color: "#64748b", margin: "0 0 4px" },
  metricValue: { fontSize: 24, fontWeight: 600, margin: 0, color: "#0f172a" },
  toggle: { width: 44, height: 24, borderRadius: 12, position: "relative", transition: "background 0.2s" },
  toggleThumb: { position: "absolute", top: 2, width: 20, height: 20, borderRadius: "50%", background: "#fff", transition: "transform 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" },
  refreshBtn: { display: "flex", alignItems: "center", padding: "8px 16px", borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", fontWeight: 600, cursor: "pointer" },
  card: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "16px 20px" },
  cardTitle: { margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: "#0f172a" },
  barTrackLarge: { height: 12, background: "#eff6ff", borderRadius: 6, overflow: "hidden" },
  agentLabel: { width: 110, fontSize: 13, color: "#64748b" },
  barTrack: { flex: 1, height: 8, background: "#eff6ff", borderRadius: 4, overflow: "hidden" },
  barValue: { fontSize: 13, width: 70, textAlign: "right", color: "#0f172a" },
  sessionRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid #f1f5f9" },
  clientRow: { display: "flex", alignItems: "center", padding: "12px 0", borderBottom: "1px solid #f1f5f9" },
  badgePremium: { background: "#eff6ff", color: "#2563eb", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
  badgeStandard: { background: "#f1f5f9", color: "#64748b", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
  upgradeBtn: { fontSize: 12, padding: "4px 10px", borderRadius: 6, border: "1px solid #2563eb", background: "#eff6ff", color: "#2563eb", cursor: "pointer", fontWeight: 500 },
  downgradeBtn: { fontSize: 12, padding: "4px 10px", borderRadius: 6, border: "1px solid #cbd5e1", background: "#f8fafc", color: "#64748b", cursor: "pointer" },
};