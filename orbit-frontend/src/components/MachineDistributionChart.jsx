import { useMemo } from "react";

const BUCKETS = [
  { label: "0-10", min: 0, max: 10 },
  { label: "11-20", min: 11, max: 20 },
  { label: "20+", min: 21, max: Infinity },
];

export default function MachineDistributionChart({ clients }) {
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
        <p style={{ fontSize: 11, color: "#94a3b8", marginTop: 10 }}>
          {unknown} client{unknown !== 1 ? "s" : ""} with no machine count detected yet.
        </p>
      )}
    </div>
  );
}

const styles = {
  card: { background: "#fff", border: "1px solid #e2e8f0", borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
  cardTitle: { margin: "0 0 12px", fontSize: 16, fontWeight: 600, color: "#0f172a" },
  label: { width: 50, fontSize: 13, color: "#64748b" },
  barTrack: { flex: 1, height: 8, background: "#eff6ff", borderRadius: 4, overflow: "hidden" },
  value: { fontSize: 13, width: 30, textAlign: "right", color: "#0f172a" },
};