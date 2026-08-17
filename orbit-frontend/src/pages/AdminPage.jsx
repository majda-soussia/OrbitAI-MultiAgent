import { useState, useEffect, useCallback } from "react";
import { getTokenSummary, getSessions, getDebugStatus, setDebugStatus, getClients, getUsageByClient } from "../api";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import ClientsTable from "../components/ClientsTable";
import ClientDrawer from "../components/ClientDrawer";
import IndustryChart from "../components/IndustryChart";
import MachineDistributionChart from "../components/MachineDistributionChart";
import PlansSplitChart from "../components/PlansSplitChart";
import RagSourcesPanel from "../components/RagSourcesPanel";
import TokensTimelineChart from "../components/TokensTimelineChart";
import TokenInspectorPanel from "../components/TokenInspectorPanel";
// import CostSummaryCard from "../components/CostSummaryCard"; // retiré du dashboard pour le moment

export default function AdminPage() {
  const { accessToken } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [tokens, setTokens] = useState(null);
  const [sessions, setSessions] = useState(null);
  const [debug, setDebug] = useState(false);
  const [clients, setClients] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [showTokenFormula, setShowTokenFormula] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [tokenData, sessionData, debugData, clientData] = await Promise.all([
        getTokenSummary(accessToken), getSessions(accessToken), getDebugStatus(accessToken), getClients(accessToken),
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
  }, [accessToken]);

  useEffect(() => {
    let cancelled = false;
    (async () => { if (!cancelled) await refresh(); })();
    return () => { cancelled = true; };
  }, [refresh]);

  async function handleToggleDebug() {
    const result = await setDebugStatus(!debug, accessToken);
    setDebug(result.debug);
  }

  if (loading) return <div style={styles.page}><div style={styles.loadingState}>Loading...</div></div>;

  const maxTokens = tokens
    ? Math.max(...Object.values(tokens.by_agent), 1)
    : 1;
  const AGENT_COLOR_MAP = {
    OrchestratorAgent: "#0ea5e9",
    CommercialAgent: "#2563eb",
    EmailAgent: "#f59e0b",
    PlanningAgent: "#10b981",
    ReplyAgent: "#ec4899",
  };

  return (
    <div style={styles.page}>
      <style>{`
        .admin-grid {
          display: grid;
          grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
          gap: 24px;
          align-items: start;
        }
        @media (max-width: 1100px) {
          .admin-grid { grid-template-columns: 1fr; }
        }
      `}</style>

      <div style={styles.container}>
        <div style={styles.headerRow}>
          <div>
            <h1 style={{ margin: 0, color: styles.titleColor }}>Orbit Admin Dashboard</h1>
            <p style={{ margin: "4px 0 0", fontSize: 14, color: styles.subtitleColor }}>
              Overview of agent activity in real time
            </p>
          </div>
          <button style={styles.refreshBtn} onClick={refresh}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ marginRight: 6 }}><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
            Refresh
          </button>
        </div>

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
              <div onClick={handleToggleDebug} style={{ ...styles.toggle, background: debug ? "#2563eb" : styles.toggleOffBg, cursor: "pointer" }}>
                <div style={{ ...styles.toggleThumb, transform: debug ? "translateX(20px)" : "translateX(2px)" }} />
              </div>
              <span style={{ fontSize: 13, color: debug ? "#2563eb" : styles.subtitleColor, fontWeight: 500 }}>
                {debug ? "Activé" : "Disabled"}
              </span>
            </div>
          </div>
        </div>

        <div className="admin-grid">
          <div style={styles.column}>
            <ClientsTable clients={clients} onSelectClient={setSelectedEmail} />
            <TokensTimelineChart />
            <TokenInspectorPanel />
            <RagSourcesPanel />
          </div>

          <div style={styles.column}>
            <IndustryChart clients={clients} />
            <MachineDistributionChart clients={clients} />
            <PlansSplitChart clients={clients} />
            {/* CostSummaryCard retiré pour le moment — pas encore utile tant que
                le modèle tourne en local (gratuit). Réactiver au besoin : <CostSummaryCard /> */}

            <div style={styles.card}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <h3 style={styles.cardTitle}>Tokens by Agent</h3>
                  <button
                    onClick={() => setShowTokenFormula((v) => !v)}
                    title="Comment ce nombre est calculé ?"
                    style={{
                      width: 16, height: 16, borderRadius: "50%", border: `1px solid ${styles.mutedText}`,
                      background: "transparent", color: styles.mutedText, fontSize: 10, lineHeight: "14px",
                      cursor: "pointer", padding: 0,
                    }}
                  >
                    i
                  </button>
                </div>
                <span style={{ fontSize: 12, color: styles.mutedText }}>{Object.keys(tokens.by_agent).length} agents</span>
              </div>

              {showTokenFormula && (
                <div style={{
                  fontSize: 11, color: styles.mutedText, background: styles.metricIconBg,
                  border: `1px solid ${styles.cardBorder}`, borderRadius: 8, padding: 10, marginBottom: 12, lineHeight: 1.6,
                }}>
                  <div>
                    <strong style={{ color: styles.titleColor }}>Per LLM call:</strong><br />
                    <code>total_tokens = prompt_tokens + response_tokens</code><br />
                    Both values come straight from Ollama's response to each{" "}
                    <code>chat()</code> call — <code>prompt_eval_count</code> for the prompt side
                    and <code>eval_count</code> for the generated side. Our code never counts
                    tokens itself; it just reads what the model already reports.
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <strong style={{ color: styles.titleColor }}>What "prompt_tokens" includes:</strong><br />
                    The full prompt sent to the model for that call — system prompt, RAG context
                    block (if the agent has <code>use_rag=True</code> and a match was found),
                    conversation history, and the current user message. All of it counted by the
                    model's own tokenizer, not ours.
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <strong style={{ color: styles.titleColor }}>What "response_tokens" includes:</strong><br />
                    Only the tokens the model actually generated for its reply, capped by{" "}
                    <code>max_tokens</code> (<code>num_predict</code> in Ollama's options).
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <strong style={{ color: styles.titleColor }}>Where this is logged:</strong><br />
                    Every call through <code>BaseAgent.call_llm()</code> or{" "}
                    <code>call_llm_raw()</code> logs one entry right after the model responds —
                    tagged with the agent's class name, so a Commercial Agent call and an
                    Orchestrator call are tracked separately even within the same conversation.
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <strong style={{ color: styles.titleColor }}>Per-agent total (shown below):</strong><br />
                    <code>total = sum of total_tokens across every logged call for that agent</code>
                  </div>
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {Object.entries(tokens?.by_agent ?? {}).map(([agent, count]) => (
                  <div key={agent} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: AGENT_COLOR_MAP[agent] || "#94a3b8", flexShrink: 0 }} />
                    <span style={styles.agentLabel}>{agent.replace("Agent", "")}</span>
                    <div style={styles.barTrack}>
                      <div style={{
                        width: `${(count / maxTokens) * 100}%`,
                        height: "100%",
                        background: AGENT_COLOR_MAP[agent] || "#94a3b8",
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
                <span style={{ fontSize: 12, color: styles.mutedText }}>{Object.keys(sessions).length} active</span>
              </div>
              {Object.entries(sessions).map(([sid, data]) => (
                <div key={sid} style={styles.sessionRow}>
                  <div>
                    <p style={{ margin: 0, fontSize: 13, fontWeight: 500, color: styles.titleColor }}>
                      {data.email || "Anonymous"}
                    </p>
                    <p style={{ margin: 0, fontSize: 11, color: styles.mutedText, fontFamily: "monospace" }}>
                      {sid.slice(0, 13)}...
                    </p>
                  </div>
                  <span style={{ fontSize: 12, color: styles.mutedText }}>
                    {data.messages} msg{data.messages !== 1 ? "s" : ""}
                  </span>
                </div>
              ))}
              {Object.keys(sessions).length === 0 && (
                <p style={{ fontSize: 13, color: styles.mutedText, margin: 0 }}>Aucune session active.</p>
              )}
            </div>
          </div>
        </div>
      </div>

      <ClientDrawer
        email={selectedEmail}
        onClose={() => setSelectedEmail(null)}
        onPlanChange={refresh}
      />
    </div>
  );
}

function baseStyles({
  pageBg, cardBg, cardBorder, titleColor, subtitleColor, mutedText,
  metricIconBg, toggleOffBg, refreshBg, sessionBorder,
}) {
  return {
    page: { background: pageBg, minHeight: "100vh" },
    container: {
      padding: "30px 40px 60px", fontFamily: "system-ui, sans-serif",
      maxWidth: 1440, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24,
    },
    loadingState: { padding: 30, fontFamily: "system-ui, sans-serif", color: mutedText },
    headerRow: { display: "flex", justifyContent: "space-between", alignItems: "flex-start" },
    titleColor, subtitleColor, mutedText, cardBorder, metricIconBg,
    metricsGrid: { display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 },
    metricCard: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 10, padding: "16px 20px" },
    metricIconWrap: { width: 32, height: 32, borderRadius: 8, background: metricIconBg, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 10 },
    metricLabel: { fontSize: 13, color: mutedText, margin: "0 0 4px" },
    metricValue: { fontSize: 24, fontWeight: 600, margin: 0, color: titleColor },
    toggle: { width: 44, height: 24, borderRadius: 12, position: "relative", transition: "background 0.2s" },
    toggleOffBg,
    toggleThumb: { position: "absolute", top: 2, width: 20, height: 20, borderRadius: "50%", background: "#fff", transition: "transform 0.2s", boxShadow: "0 1px 3px rgba(0,0,0,0.2)" },
    refreshBtn: { display: "flex", alignItems: "center", padding: "8px 16px", borderRadius: 8, border: "none", background: refreshBg, color: "#fff", fontWeight: 600, cursor: "pointer" },
    column: { display: "flex", flexDirection: "column", gap: 20, minWidth: 0 },
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px" },
    cardTitle: { margin: "0 0 12px", fontSize: 15, fontWeight: 600, color: titleColor },
    agentLabel: { width: 90, fontSize: 12, color: mutedText },
    barTrack: { flex: 1, height: 7, background: metricIconBg, borderRadius: 4, overflow: "hidden" },
    barValue: { fontSize: 12, width: 62, textAlign: "right", color: titleColor },
    sessionRow: { display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 0", borderBottom: `1px solid ${sessionBorder}` },
  };
}

const lightStyles = baseStyles({
  pageBg: "#f8fafc", cardBg: "#fff", cardBorder: "#e2e8f0",
  titleColor: "#0f172a", subtitleColor: "#64748b", mutedText: "#94a3b8",
  metricIconBg: "#eff6ff", toggleOffBg: "#e2e8f0", refreshBg: "#2563eb", sessionBorder: "#f1f5f9",
});

const darkStyles = baseStyles({
  pageBg: "#05070d", cardBg: "#0d1119", cardBorder: "#232b40",
  titleColor: "#e8eaf0", subtitleColor: "#8b93a7", mutedText: "#5b6478",
  metricIconBg: "#151b2b", toggleOffBg: "#232b40", refreshBg: "#2563eb", sessionBorder: "#161c2c",
});