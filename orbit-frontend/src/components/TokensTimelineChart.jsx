import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { getTokensTimeseries } from "../api";

const AGENT_COLORS = {
  OrchestratorAgent: "#0ea5e9",
  CommercialAgent: "#2563eb",
  EmailAgent: "#f59e0b",
  PlanningAgent: "#10b981",
  ReplyAgent: "#ec4899",
};
const FALLBACK_COLOR = "#94a3b8";

const RANGE_OPTIONS = [
  { label: "7d", days: 7 },
  { label: "14d", days: 14 },
  { label: "30d", days: 30 },
];

function formatShortDate(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { day: "2-digit", month: "2-digit" });
}

export default function TokensTimelineChart() {
  const { accessToken } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [days, setDays] = useState(14);
  const [series, setSeries] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTokensTimeseries(days, accessToken);
      setSeries(data.series || []);
    } catch (err) {
      setError(err.message || "Failed to load token usage history.");
    } finally {
      setLoading(false);
    }
  }, [days, accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const agents = series
    ? Array.from(new Set(series.flatMap((d) => Object.keys(d.by_agent)))).sort()
    : [];
  const maxTotal = series ? Math.max(...series.map((d) => d.total_tokens), 1) : 1;

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <h3 style={styles.cardTitle}>Token Usage Over Time</h3>
        <div style={{ display: "flex", gap: 6 }}>
          {RANGE_OPTIONS.map((opt) => (
            <button
              key={opt.days}
              onClick={() => setDays(opt.days)}
              style={{ ...styles.rangeBtn, ...(days === opt.days ? styles.rangeBtnActive : {}) }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <div style={styles.info}>Loading...</div>}
      {error && <div style={styles.errorBox}>{error}</div>}

      {!loading && series && series.length > 0 && (
        <>
          <div style={styles.chartArea}>
            {series.map((day) => (
              <div key={day.date} style={styles.barCol} title={`${day.date} — ${day.total_tokens.toLocaleString()} tokens`}>
                <div style={styles.barStack}>
                  {agents.map((agent) => {
                    const value = day.by_agent[agent] || 0;
                    if (value === 0) return null;
                    const heightPct = (value / maxTotal) * 100;
                    return (
                      <div
                        key={agent}
                        style={{
                          height: `${heightPct}%`,
                          background: AGENT_COLORS[agent] || FALLBACK_COLOR,
                          width: "100%",
                        }}
                      />
                    );
                  })}
                </div>
                {(series.length <= 14 || day === series[series.length - 1] || day === series[0]) && (
                  <span style={styles.barLabel}>{formatShortDate(day.date)}</span>
                )}
              </div>
            ))}
          </div>

          <div style={styles.legend}>
            {agents.map((agent) => (
              <div key={agent} style={styles.legendItem}>
                <span style={{ ...styles.legendDot, background: AGENT_COLORS[agent] || FALLBACK_COLOR }} />
                {agent}
              </div>
            ))}
          </div>
        </>
      )}

      {!loading && series && series.length > 0 && series.every((d) => d.total_tokens === 0) && (
        <p style={{ fontSize: 13, color: styles.mutedText, margin: "8px 0 0" }}>
          No calls recorded for this period.
        </p>
      )}
    </div>
  );
}

function baseStyles({ cardBg, cardBorder, titleColor, mutedText, chartBg, rangeBg, rangeBorder, rangeColor, rangeActiveBg, rangeActiveColor }) {
  return {
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
    cardTitle: { margin: 0, fontSize: 16, fontWeight: 600, color: titleColor },
    mutedText,
    info: { fontSize: 14, color: mutedText },
    errorBox: { fontSize: 13, color: "#b91c1c", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "8px 12px" },
    rangeBtn: { fontSize: 12, padding: "5px 12px", borderRadius: 6, border: `1px solid ${rangeBorder}`, background: rangeBg, color: rangeColor, cursor: "pointer", fontWeight: 500 },
    rangeBtnActive: { background: rangeActiveBg, color: rangeActiveColor, borderColor: rangeActiveBg },
    chartArea: { display: "flex", alignItems: "flex-end", gap: 4, height: 140, padding: "0 2px", background: chartBg, borderRadius: 8 },
    barCol: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "flex-end", height: "100%", minWidth: 6, position: "relative" },
    barStack: { width: "70%", maxWidth: 20, height: "100%", display: "flex", flexDirection: "column-reverse", borderRadius: 3, overflow: "hidden" },
    barLabel: { fontSize: 9, color: mutedText, marginTop: 4, whiteSpace: "nowrap" },
    legend: { display: "flex", flexWrap: "wrap", gap: 12, marginTop: 14 },
    legendItem: { display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: mutedText },
    legendDot: { width: 8, height: 8, borderRadius: "50%", flexShrink: 0 },
  };
}

const lightStyles = baseStyles({
  cardBg: "#fff", cardBorder: "#e2e8f0", titleColor: "#0f172a", mutedText: "#64748b", chartBg: "#f8fafc",
  rangeBg: "#f8fafc", rangeBorder: "#cbd5e1", rangeColor: "#64748b", rangeActiveBg: "#2563eb", rangeActiveColor: "#fff",
});

const darkStyles = baseStyles({
  cardBg: "#0d1119", cardBorder: "#232b40", titleColor: "#e8eaf0", mutedText: "#8b93a7", chartBg: "#0a0e17",
  rangeBg: "#151b2b", rangeBorder: "#232b40", rangeColor: "#c3c9d6", rangeActiveBg: "#2563eb", rangeActiveColor: "#fff",
});