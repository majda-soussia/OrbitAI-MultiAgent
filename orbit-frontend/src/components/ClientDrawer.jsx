import { useAuth } from "../context/AuthContext";
import { useClientDetail } from "../hooks/useClientDetail";
import { setClientPlan, resetClientHistory, toggleClientMemory } from "../api";

const AGENT_COLORS = {
  Commercial: "#2563eb",
  Email: "#6366f1",
  Planning: "#8b5cf6",
  Reply: "#a78bfa",
  Orchestrator: "#3b82f6",
};

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function ClientDrawer({ email, onClose, onPlanChange }) {
  const { accessToken } = useAuth();
  const { detail, loading, error, refresh } = useClientDetail(email, accessToken);

  if (!email) return null;

  async function handleUpgrade() {
    await setClientPlan(email, "premium", accessToken);
    await refresh();
    onPlanChange?.();
  }

  async function handleDowngrade() {
    await setClientPlan(email, "standard", accessToken);
    await refresh();
    onPlanChange?.();
  }

  async function handleToggleMemory() {
    await toggleClientMemory(email, !detail.memory_enabled, accessToken);
    await refresh();
  }

  async function handleResetHistory() {
    if (!window.confirm(`Delete all conversation history for ${email}? This cannot be undone.`)) {
      return;
    }
    await resetClientHistory(email, accessToken);
    await refresh();
  }

  const maxUsage = detail
    ? Math.max(...Object.values(detail.usage_by_agent).map((a) => a.total_tokens), 1)
    : 1;

  return (
    <>
      <div style={styles.backdrop} onClick={onClose} />
      <div style={styles.drawer}>
        <div style={styles.header}>
          <div>
            <h2 style={{ margin: 0, fontSize: 18 }}>{email}</h2>
            {detail && (
              <span style={detail.plan === "premium" ? styles.badgePremium : styles.badgeStandard}>
                {detail.plan}
              </span>
            )}
          </div>
          <button onClick={onClose} style={styles.closeBtn} aria-label="Close">
            ✕
          </button>
        </div>

        {loading && !detail && <div style={styles.info}>Loading...</div>}
        {error && <div style={styles.errorBox}>{error}</div>}

        {detail && (
          <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
            {/* Profile */}
            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Profile</h3>
              <div style={styles.kvGrid}>
                <span style={styles.kvLabel}>Industry</span>
                <span style={styles.kvValue}>{detail.profile.industry_type || "Unknown"}</span>
                <span style={styles.kvLabel}>Machines</span>
                <span style={styles.kvValue}>{detail.profile.machine_count ?? "Unknown"}</span>
                <span style={styles.kvLabel}>Profile updated</span>
                <span style={styles.kvValue}>{formatDate(detail.profile.updated_at)}</span>
              </div>
            </section>

            {/* Account */}
            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Account</h3>
              <div style={styles.kvGrid}>
                <span style={styles.kvLabel}>Google</span>
                <span style={styles.kvValue}>{detail.google_connected ? "Connected" : "Not connected"}</span>
                <span style={styles.kvLabel}>Memory</span>
                <span style={styles.kvValue}>{detail.memory_enabled ? "Enabled" : "Disabled"}</span>
                <span style={styles.kvLabel}>Member since</span>
                <span style={styles.kvValue}>{formatDate(detail.created_at)}</span>
                <span style={styles.kvLabel}>Last seen</span>
                <span style={styles.kvValue}>{formatDate(detail.last_seen)}</span>
                <span style={styles.kvLabel}>Conversations</span>
                <span style={styles.kvValue}>{detail.conversation_count}</span>
              </div>

              <div style={{ marginTop: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#64748b", marginBottom: 4 }}>
                  <span>{detail.tokens_used.toLocaleString()} tokens used</span>
                  <span>{detail.token_limit.toLocaleString()} limit</span>
                </div>
                <div style={styles.barTrack}>
                  <div
                    style={{
                      width: `${Math.min(100, (detail.tokens_used / detail.token_limit) * 100)}%`,
                      height: "100%",
                      background: detail.remaining === 0 ? "#ef4444" : "#2563eb",
                      borderRadius: 4,
                    }}
                  />
                </div>
              </div>
            </section>

            {/* Usage by agent */}
            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Usage by Agent</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {Object.entries(detail.usage_by_agent).map(([agent, stats]) => (
                  <div key={agent}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#64748b", marginBottom: 2 }}>
                      <span>{agent}</span>
                      <span>
                        {stats.calls} calls · {stats.total_tokens.toLocaleString()} tokens · avg{" "}
                        {stats.avg_tokens.toLocaleString()}/call
                      </span>
                    </div>
                    <div style={styles.barTrack}>
                      <div
                        style={{
                          width: `${(stats.total_tokens / maxUsage) * 100}%`,
                          height: "100%",
                          background: AGENT_COLORS[agent] || "#2563eb",
                          borderRadius: 4,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Actions */}
            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Actions</h3>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {detail.plan === "standard" ? (
                  <button style={styles.upgradeBtn} onClick={handleUpgrade}>
                    → Premium
                  </button>
                ) : (
                  <button style={styles.downgradeBtn} onClick={handleDowngrade}>
                    Downgrade
                  </button>
                )}
                <button style={styles.downgradeBtn} onClick={handleToggleMemory}>
                  {detail.memory_enabled ? "Disable Memory" : "Enable Memory"}
                </button>
                <button style={styles.dangerBtn} onClick={handleResetHistory}>
                  Reset History
                </button>
              </div>
              <p style={{ fontSize: 11, color: "#94a3b8", marginTop: 8 }}>
                Reset quota is not available yet — pending confirmation on how the
                client_token_summary view aggregates usage.
              </p>
            </section>
          </div>
        )}
      </div>
    </>
  );
}

const styles = {
  backdrop: {
    position: "fixed",
    inset: 0,
    background: "rgba(15, 23, 42, 0.4)",
    zIndex: 40,
  },
  drawer: {
    position: "fixed",
    top: 0,
    right: 0,
    height: "100vh",
    width: 380,
    background: "#fff",
    boxShadow: "-4px 0 24px rgba(0,0,0,0.12)",
    padding: 24,
    overflowY: "auto",
    zIndex: 50,
    fontFamily: "system-ui, sans-serif",
  },
  header: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 20,
  },
  closeBtn: {
    border: "none",
    background: "transparent",
    fontSize: 16,
    cursor: "pointer",
    color: "#64748b",
  },
  info: { fontSize: 14, color: "#64748b" },
  errorBox: {
    fontSize: 13,
    color: "#b91c1c",
    background: "#fef2f2",
    border: "1px solid #fecaca",
    borderRadius: 8,
    padding: "8px 12px",
  },
  section: {
    background: "#f8fafc",
    border: "1px solid #e2e8f0",
    borderRadius: 10,
    padding: 14,
  },
  sectionTitle: { margin: "0 0 10px", fontSize: 13, fontWeight: 600, color: "#0f172a" },
  kvGrid: {
    display: "grid",
    gridTemplateColumns: "auto 1fr",
    rowGap: 6,
    columnGap: 12,
    fontSize: 13,
  },
  kvLabel: { color: "#64748b" },
  kvValue: { color: "#0f172a", fontWeight: 500, textAlign: "right" },
  barTrack: { height: 6, background: "#e2e8f0", borderRadius: 3, overflow: "hidden" },
  badgePremium: { background: "#eff6ff", color: "#2563eb", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
  badgeStandard: { background: "#f1f5f9", color: "#64748b", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
  upgradeBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: "1px solid #2563eb", background: "#eff6ff", color: "#2563eb", cursor: "pointer", fontWeight: 500 },
  downgradeBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: "1px solid #cbd5e1", background: "#f8fafc", color: "#64748b", cursor: "pointer" },
  dangerBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: "1px solid #ef4444", background: "#fef2f2", color: "#ef4444", cursor: "pointer", fontWeight: 500 },
};