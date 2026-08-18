import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { inspectTokens } from "../api";

const CHIP_COLORS = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#dc2626", "#db2777"];

export default function TokenInspectorPanel() {
  const { accessToken } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [text, setText] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  async function handleInspect() {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await inspectTokens(text, accessToken);
      setResult(data);
      setCopied(false);
    } catch (err) {
      setError(err.message || "Inspection failed.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  async function handleCopyJson() {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(JSON.stringify(result, null, 2));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // clipboard API indisponible (contexte non sécurisé, etc.) — on ignore silencieusement
    }
  }

  return (
    <div style={styles.card}>
      <h3 style={styles.cardTitle}>Token Inspector</h3>
      <p style={{ fontSize: 12, color: styles.mutedText, margin: "0 0 12px" }}>
        Paste any text to see exactly how the real Qwen2.5 tokenizer splits it —
        this is a verification tool, independent from what Ollama reports after a call.
      </p>

      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type or paste text here..."
        rows={3}
        style={styles.textarea}
      />

      <button style={styles.inspectBtn} onClick={handleInspect} disabled={loading || !text.trim()}>
        {loading ? "Inspecting..." : "Inspect"}
      </button>

      {error && <div style={styles.errorBox}>{error}</div>}

      {result && (
        <div style={{ marginTop: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8, flexWrap: "wrap", gap: 6 }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: styles.titleColor }}>
              {result.token_count} token{result.token_count !== 1 ? "s" : ""}
            </span>
            <span style={{ fontSize: 11, color: styles.mutedText }}>{result.model}</span>
          </div>

          <div style={styles.statsRow}>
            <div style={styles.statBox}>
              <span style={styles.statValue}>{text.length}</span>
              <span style={styles.statLabel}>characters</span>
            </div>
            <div style={styles.statBox}>
              <span style={styles.statValue}>
                {result.token_count > 0 ? (text.length / result.token_count).toFixed(2) : "—"}
              </span>
              <span style={styles.statLabel}>chars / token</span>
            </div>
            <div style={styles.statBox}>
              <span style={styles.statValue}>{result.token_ids.length}</span>
              <span style={styles.statLabel}>token ids</span>
            </div>
          </div>

          <div style={styles.chipRow}>
            {result.token_pieces.map((piece, i) => (
              <span
                key={i}
                title={`id: ${result.token_ids[i]}`}
                style={{
                  ...styles.chip,
                  background: `${CHIP_COLORS[i % CHIP_COLORS.length]}22`,
                  color: CHIP_COLORS[i % CHIP_COLORS.length],
                  border: `1px solid ${CHIP_COLORS[i % CHIP_COLORS.length]}55`,
                }}
              >
                {piece.replace(/Ġ/g, "␣")}
              </span>
            ))}
          </div>
          <p style={{ fontSize: 10, color: styles.mutedText, marginTop: 8, marginBottom: 12 }}>
            ␣ marks a leading space merged into the token by the tokenizer. Hover a chip to see its numeric id.
          </p>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: styles.titleColor }}>Detailed breakdown</span>
            <button style={styles.copyBtn} onClick={handleCopyJson}>
              {copied ? "Copied ✓" : "Copy as JSON"}
            </button>
          </div>

          <div style={styles.tableWrap}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>#</th>
                  <th style={styles.th}>Piece</th>
                  <th style={styles.th}>Token ID</th>
                </tr>
              </thead>
              <tbody>
                {result.token_pieces.map((piece, i) => (
                  <tr key={i}>
                    <td style={styles.td}>{i + 1}</td>
                    <td style={{ ...styles.td, fontFamily: "monospace" }}>{piece.replace(/Ġ/g, "␣")}</td>
                    <td style={{ ...styles.td, fontFamily: "monospace" }}>{result.token_ids[i]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

function baseStyles({ cardBg, cardBorder, titleColor, mutedText, inputBg, inputBorder, inputColor, statBoxBg, thBorder, tdBorder, copyBtnBg, copyBtnBorder, copyBtnColor }) {
  return {
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
    cardTitle: { margin: "0 0 4px", fontSize: 16, fontWeight: 600, color: titleColor },
    mutedText,
    titleColor,
    textarea: {
      width: "100%", padding: "10px 12px", borderRadius: 8, border: `1px solid ${inputBorder}`,
      fontSize: 13, fontFamily: "inherit", background: inputBg, color: inputColor, resize: "vertical", outline: "none",
      boxSizing: "border-box",
    },
    inspectBtn: {
      marginTop: 8, fontSize: 13, padding: "8px 16px", borderRadius: 8, border: "1px solid #2563eb",
      background: "#2563eb", color: "#fff", cursor: "pointer", fontWeight: 500,
    },
    errorBox: { fontSize: 13, color: "#b91c1c", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "8px 12px", marginTop: 10 },
    chipRow: { display: "flex", flexWrap: "wrap", gap: 6 },
    chip: { fontSize: 12, padding: "3px 8px", borderRadius: 6, fontFamily: "monospace", whiteSpace: "pre" },
    statsRow: { display: "flex", gap: 10, marginBottom: 12 },
    statBox: { flex: 1, background: statBoxBg, borderRadius: 8, padding: "8px 10px", display: "flex", flexDirection: "column", alignItems: "center", gap: 2 },
    statValue: { fontSize: 16, fontWeight: 700, color: titleColor },
    statLabel: { fontSize: 10, color: mutedText, textTransform: "uppercase", letterSpacing: 0.3 },
    copyBtn: { fontSize: 11, padding: "4px 10px", borderRadius: 6, border: `1px solid ${copyBtnBorder}`, background: copyBtnBg, color: copyBtnColor, cursor: "pointer" },
    tableWrap: { maxHeight: 240, overflowY: "auto", border: `1px solid ${thBorder}`, borderRadius: 8 },
    table: { width: "100%", borderCollapse: "collapse", fontSize: 12 },
    th: { textAlign: "left", padding: "6px 10px", color: mutedText, fontWeight: 600, borderBottom: `1px solid ${thBorder}`, position: "sticky", top: 0, background: statBoxBg },
    td: { padding: "5px 10px", borderBottom: `1px solid ${tdBorder}`, color: titleColor },
  };
}

const lightStyles = baseStyles({
  cardBg: "#fff", cardBorder: "#e2e8f0", titleColor: "#0f172a", mutedText: "#64748b",
  inputBg: "#fff", inputBorder: "#cbd5e1", inputColor: "#0f172a",
  statBoxBg: "#f8fafc", thBorder: "#e2e8f0", tdBorder: "#f1f5f9",
  copyBtnBg: "#fff", copyBtnBorder: "#cbd5e1", copyBtnColor: "#64748b",
});

const darkStyles = baseStyles({
  cardBg: "#0d1119", cardBorder: "#232b40", titleColor: "#e8eaf0", mutedText: "#8b93a7",
  inputBg: "#151b2b", inputBorder: "#232b40", inputColor: "#e8eaf0",
  statBoxBg: "#151b2b", thBorder: "#232b40", tdBorder: "#161c2c",
  copyBtnBg: "#151b2b", copyBtnBorder: "#232b40", copyBtnColor: "#c3c9d6",
});