import { useMemo } from "react";
import { useTheme } from "../context/ThemeContext";

const BUCKETS = [
  { label: "0-10", min: 0, max: 10 },
  { label: "11-20", min: 11, max: 20 },
  { label: "20+", min: 21, max: Infinity },
];

export default function MachineDistributionChart({ clients }) {
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const { counts, unknown } = useMemo(() => {
    const bucketCounts = BUCKETS.map(() => 0);
    let unknownCount = 0;

    Object.values(clients || {}).forEach((c) => {
      if (c.machine_count == null) {
        unknownCount += 1;
        return;
      }
      const idx = BUCKETS.findIndex((b) => c.machine_count >= b.min && c.machine_count <= b.max);
      if (idx !== -1) bucketCounts[idx] += 1;
    });

    return { counts: bucketCounts, unknown: unknownCount };
  }, [clients]);

  const max = Math.max(...counts, 1);

  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Machine Distribution</h3>
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {BUCKETS.map((b, i) => (
          <div key={b.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={styles.label}>{b.label}</span>
            <div style={styles.barTrack}>
              <div
                style={{
                  width: `${(counts[i] / max) * 100}%`,
                  height: "100%",
                  background: "#2563eb",
                  borderRadius: 4,
                }}
              />
            </div>
            <span style={styles.value}>{counts[i]}</span>
          </div>
        ))}
      </div>
      {unknown > 0 && (
        <p style={{ fontSize: 11, color: styles.mutedText, marginTop: 10 }}>
          {unknown} client{unknown !== 1 ? "s" : ""} with no machine count detected yet.
        </p>
      )}
    </div>
  );
}

function baseStyles({ cardBg, cardBorder, titleColor, mutedText, barTrackBg }) {
  return {
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
    cardTitle: { margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: titleColor },
    mutedText,
    label: { width: 50, fontSize: 13, color: mutedText },
    barTrack: { flex: 1, height: 8, background: barTrackBg, borderRadius: 4, overflow: "hidden" },
    value: { fontSize: 13, width: 30, textAlign: "right", color: titleColor },
  };
}

const lightStyles = baseStyles({ cardBg: "#fff", cardBorder: "#e2e8f0", titleColor: "#0f172a", mutedText: "#64748b", barTrackBg: "#eff6ff" });
const darkStyles = baseStyles({ cardBg: "#0d1119", cardBorder: "#232b40", titleColor: "#e8eaf0", mutedText: "#8b93a7", barTrackBg: "#151b2b" });