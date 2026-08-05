import { useState, useEffect } from "react";
import { getTokenSummary, getSessions, getDebugStatus, setDebugStatus, getClients, getUsageByClient } from "../api";
import { useAuth } from "../context/AuthContext";
import ClientsTable from "../components/ClientsTable";
import ClientDrawer from "../components/ClientDrawer";
import IndustryChart from "../components/IndustryChart";
import MachineDistributionChart from "../components/MachineDistributionChart";
import PlansSplitChart from "../components/PlansSplitChart";

export default function AdminPage() {
  const { accessToken } = useAuth();
  const [tokens, setTokens] = useState(null);
  const [sessions, setSessions] = useState(null);
  const [debug, setDebug] = useState(false);
  const [clients, setClients] = useState(null);
  const [usageByClient, setUsageByClient] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEmail, setSelectedEmail] = useState(null);
  async function refresh() {
    setLoading(true);
    try {
      const [tokenData, sessionData, debugData, clientData, usageData] = await Promise.all([
        getTokenSummary(accessToken), getSessions(accessToken), getDebugStatus(accessToken), getClients(accessToken), getUsageByClient(accessToken),
      ]);
      setTokens(tokenData);
      setSessions(sessionData);
      setDebug(debugData.debug);
      setClients(clientData);
      setUsageByClient(usageData);
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
  }, [accessToken]);

  async function handleToggleDebug() {
    const result = await setDebugStatus(!debug, accessToken);
    setDebug(result.debug);
  }

  if (loading) return <div style={styles.container}>Loading...</div>;

  const maxTokens = tokens
  ? Math.max(...Object.values(tokens.by_agent), 1)
  : 1;
  const agentColors = ["#2563eb", "#6366f1", "#8b5cf6", "#a78bfa", "#3b82f6"];

  const totalBudget = clients
    ? Object.values(clients).reduce((sum, c) => sum + (c.token_limit ?? 5000), 0)
    : 0;
  return (
    <div style={styles.container}>
      <div style={styles.headerRow}>
        <div>
          <h1 style={{ margin: 0 }}>Orbit Admin Dashboard</h1>
          <p style={{ margin: "4px 0 0", fontSize: 14, color: "#64748b" }}>
            Overview of agent activity in real time
          </p>
        </div>
        <button style={styles.refreshBtn} onClick={refresh}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 6 }}><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          Refresh
        </button>
      </div>

      {/* Métriques */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
          </div>
          <p style={styles.metricLabel}>LLM Calls</p>
          <p style={styles.metricValue}>{tokens?.total_calls ?? 0}</p>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><circle cx="8" cy="8" r="6"/><circle cx="16" cy="16" r="6" opacity="0.5"/></svg>
          </div>
          <p style={styles.metricLabel}>Total Tokens</p>
          <p style={styles.metricValue}>{(tokens?.total_tokens ?? 0).toLocaleString()}</p>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
          </div>
          <p style={styles.metricLabel}>Active Sessions</p>
          <p style={styles.metricValue}>{Object.keys(sessions ?? {}).length}</p>
        </div>
        <div style={styles.metricCard}>
          <div style={styles.metricIconWrap}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2"><rect x="8" y="6" width="8" height="14" rx="4"/><path d="M19 8h2M19 12h3M19 16h2M3 8h2M2 12h3M3 16h2M9 4l1 2M14 4l-1 2"/></svg>
          </div>
          <p style={styles.metricLabel}>Debug Mode</p>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 4 }}>
            <div onClick={handleToggleDebug} style={{ ...styles.toggle, background: debug ? "#2563eb" : "#e2e8f0", cursor: "pointer" }}>
              <div style={{ ...styles.toggleThumb, transform: debug ? "translateX(20px)" : "translateX(2px)" }} />
            </div>
            <span style={{ fontSize: 13, color: debug ? "#2563eb" : "#64748b", fontWeight: 500 }}>
              {debug ? "Activé" : "Disabled"}
            </span>
          </div>
        </div>
      </div>
      <ClientsTable clients={clients} onSelectClient={setSelectedEmail} />
      <ClientDrawer
        email={selectedEmail}
        onClose={() => setSelectedEmail(null)}
        onPlanChange={refresh}
      />

      {/* Business Intelligence */}
      <div style={styles.biGrid}>
        <IndustryChart clients={clients} />
        <MachineDistributionChart clients={clients} />
        <PlansSplitChart clients={clients} />
      </div>

      {/* Tokens par agent */}
      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={styles.cardTitle}>Tokens by Agent</h3>
          <span style={{ fontSize: 13, color: "#94a3b8" }}>{Object.keys(tokens.by_agent).length} agents</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {Object.entries(tokens?.by_agent ?? {}).map(([agent, count], i) => (
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

      <div style={styles.card}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <h3 style={styles.cardTitle}>Active Sessions</h3>
          <span style={{ fontSize: 13, color: "#94a3b8" }}>{Object.keys(sessions).length} active</span>
        </div>
        {Object.entries(sessions).map(([sid, data]) => (
          <div key={sid} style={styles.sessionRow}>
            <div>
              <p style={{ margin: 0, fontSize: 14, fontWeight: 500 }}>
                {data.email || "Anonymous"}
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
  biGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 16 },
};