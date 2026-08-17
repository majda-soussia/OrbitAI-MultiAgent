import { useMemo } from "react";
import { useTheme } from "../context/ThemeContext";

export default function PlansSplitChart({ clients }) {
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const { standard, premium, total } = useMemo(() => {
    let standardCount = 0;
    let premiumCount = 0;
    Object.values(clients || {}).forEach((c) => {
      if (c.plan === "premium") premiumCount += 1;
      else standardCount += 1;
    });
    return { standard: standardCount, premium: premiumCount, total: standardCount + premiumCount };
  }, [clients]);

  const premiumPct = total ? Math.round((premium / total) * 100) : 0;
  const standardPct = total ? 100 - premiumPct : 0;

  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Plans</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <div>
          <div style={styles.rowLabel}>
            <span>Premium</span>
            <span>{premium} ({premiumPct}%)</span>
          </div>
          <div style={styles.barTrack}>
            <div style={{ width: `${premiumPct}%`, height: "100%", background: "#2563eb", borderRadius: 4 }} />
          </div>
        </div>
        <div>
          <div style={styles.rowLabel}>
            <span>Standard</span>
            <span>{standard} ({standardPct}%)</span>
          </div>
          <div style={styles.barTrack}>
            <div style={{ width: `${standardPct}%`, height: "100%", background: "#94a3b8", borderRadius: 4 }} />
          </div>
        </div>
      </div>
    </div>
  );
}

function baseStyles({ cardBg, cardBorder, titleColor, mutedText, barTrackBg }) {
  return {
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
    cardTitle: { margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: titleColor },
    rowLabel: { display: "flex", justifyContent: "space-between", fontSize: 13, color: mutedText, marginBottom: 4 },
    barTrack: { height: 8, background: barTrackBg, borderRadius: 4, overflow: "hidden" },
  };
}

const lightStyles = baseStyles({ cardBg: "#fff", cardBorder: "#e2e8f0", titleColor: "#0f172a", mutedText: "#64748b", barTrackBg: "#eff6ff" });
const darkStyles = baseStyles({ cardBg: "#0d1119", cardBorder: "#232b40", titleColor: "#e8eaf0", mutedText: "#8b93a7", barTrackBg: "#151b2b" });