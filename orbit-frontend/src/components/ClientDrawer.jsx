import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { useClientDetail } from "../hooks/useClientDetail";
import { setClientPlan, resetClientHistory, resetClientQuota, toggleClientMemory } from "../api";

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
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;
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
    try {
      await resetClientHistory(email, accessToken);
      await refresh();
    } catch (err) {
      console.error("Erreur reset history:", err);
      alert(`Échec de la réinitialisation de l'historique : ${err.message}`);
    }
  }

  async function handleResetQuota() {
    if (!window.confirm(`Réinitialiser le compteur de tokens de ${email} ? L'historique de conversation reste intact — seul le compteur repart à 0.`)) {
      return;
    }
    try {
      await resetClientQuota(email, accessToken);
      await refresh();
      onPlanChange?.();
    } catch (err) {
      console.error("Erreur reset quota:", err);
      alert(`Échec de la réinitialisation des tokens : ${err.message}`);
    }
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
            <h2 style={{ margin: 0, fontSize: 18, color: styles.titleColor }}>{email}</h2>
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
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: styles.mutedText, marginBottom: 4 }}>
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

            <section style={styles.section}>
              <h3 style={styles.sectionTitle}>Usage by Agent</h3>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {Object.entries(detail.usage_by_agent).map(([agent, stats]) => (
                  <div key={agent}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: styles.mutedText, marginBottom: 2 }}>
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
                <button style={styles.resetBtn} onClick={handleResetQuota}>
                  Reset Tokens
                </button>
                <button style={styles.dangerBtn} onClick={handleResetHistory}>
                  Reset History
                </button>
              </div>
            </section>
          </div>
        )}
      </div>
    </>
  );
}

function baseStyles({ drawerBg, sectionBg, sectionBorder, titleColor, mutedText, closeBtnColor, barTrackBg, downgradeBg, downgradeBorder, downgradeColor, resetBg, resetBorder, resetColor }) {
  return {
    backdrop: { position: "fixed", inset: 0, background: "rgba(15, 23, 42, 0.4)", zIndex: 40 },
    drawer: {
      position: "fixed", top: 0, right: 0, height: "100vh", width: 380, background: drawerBg,
      boxShadow: "-4px 0 24px rgba(0,0,0,0.25)", padding: 24, overflowY: "auto", zIndex: 50,
      fontFamily: "system-ui, sans-serif",
    },
    header: { display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 20 },
    titleColor,
    closeBtn: { border: "none", background: "transparent", fontSize: 16, cursor: "pointer", color: closeBtnColor },
    info: { fontSize: 14, color: mutedText },
    errorBox: { fontSize: 13, color: "#b91c1c", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "8px 12px" },
    section: { background: sectionBg, border: `1px solid ${sectionBorder}`, borderRadius: 10, padding: 14 },
    sectionTitle: { margin: "0 0 10px", fontSize: 13, fontWeight: 600, color: titleColor },
    mutedText,
    kvGrid: { display: "grid", gridTemplateColumns: "auto 1fr", rowGap: 6, columnGap: 12, fontSize: 13 },
    kvLabel: { color: mutedText },
    kvValue: { color: titleColor, fontWeight: 500, textAlign: "right" },
    barTrack: { height: 6, background: barTrackBg, borderRadius: 3, overflow: "hidden" },
    badgePremium: { background: "#eff6ff", color: "#2563eb", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
    badgeStandard: { background: "#f1f5f9", color: "#64748b", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
    upgradeBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: "1px solid #2563eb", background: "#eff6ff", color: "#2563eb", cursor: "pointer", fontWeight: 500 },
    downgradeBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: `1px solid ${downgradeBorder}`, background: downgradeBg, color: downgradeColor, cursor: "pointer" },
    dangerBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: "1px solid #ef4444", background: "#fef2f2", color: "#ef4444", cursor: "pointer", fontWeight: 500 },
    resetBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: `1px solid ${resetBorder}`, background: resetBg, color: resetColor, cursor: "pointer", fontWeight: 500 },
  };
}

const lightStyles = baseStyles({
  drawerBg: "#fff", sectionBg: "#f8fafc", sectionBorder: "#e2e8f0",
  titleColor: "#0f172a", mutedText: "#64748b", closeBtnColor: "#64748b", barTrackBg: "#e2e8f0",
  downgradeBg: "#f8fafc", downgradeBorder: "#cbd5e1", downgradeColor: "#64748b",
  resetBg: "#f8fafc", resetBorder: "#cbd5e1", resetColor: "#64748b",
});

const darkStyles = baseStyles({
  drawerBg: "#0a0e17", sectionBg: "#0d1119", sectionBorder: "#232b40",
  titleColor: "#e8eaf0", mutedText: "#8b93a7", closeBtnColor: "#8b93a7", barTrackBg: "#232b40",
  downgradeBg: "#151b2b", downgradeBorder: "#232b40", downgradeColor: "#c3c9d6",
  resetBg: "#151b2b", resetBorder: "#232b40", resetColor: "#c3c9d6",
});