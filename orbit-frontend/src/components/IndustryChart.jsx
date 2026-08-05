import { useMemo } from "react";

const COLORS = ["#2563eb", "#6366f1", "#8b5cf6", "#a78bfa", "#3b82f6", "#0ea5e9", "#14b8a6"];

export default function IndustryChart({ clients }) {
  const data = useMemo(() => {
    const counts = {};
    Object.values(clients || {}).forEach((c) => {
      const key = c.industry_type || "Unknown";
      counts[key] = (counts[key] || 0) + 1;
    });
    return Object.entries(counts).sort(([, a], [, b]) => b - a);
  }, [clients]);

  const max = Math.max(...data.map(([, count]) => count), 1);

  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Industries</h3>
      {data.length === 0 ? (
        <p style={{ fontSize: 13, color: "#94a3b8" }}>No client data yet.</p>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {data.map(([industry, count], i) => (
            <div key={industry} style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={styles.label} title={industry}>{industry}</span>
              <div style={styles.barTrack}>
                <div
                  style={{
                    width: `${(count / max) * 100}%`,
                    height: "100%",
                    background: COLORS[i % COLORS.length],
                    borderRadius: 4,
                  }}
                />
              </div>
              <span style={styles.value}>{count}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

const styles = {
  card: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
  cardTitle: { margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: "#0f172a" },
  label: { width: 110, fontSize: 13, color: "#64748b", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" },
  barTrack: { flex: 1, height: 8, background: "#eff6ff", borderRadius: 4, overflow: "hidden" },
  value: { fontSize: 13, width: 30, textAlign: "right", color: "#0f172a" },
};