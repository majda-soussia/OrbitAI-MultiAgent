import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { getRagSources, uploadRagSource, deleteRagSource, reindexRagSources } from "../api";

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString();
}

export default function RagSourcesPanel() {
  const { accessToken } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [sources, setSources] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [reindexing, setReindexing] = useState(false);
  const [indexDirty, setIndexDirty] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);
  const fileInputRef = useRef(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getRagSources(accessToken);
      setSources(data.sources || []);
    } catch (err) {
      setError(err.message || "Failed to load RAG sources.");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  function triggerFilePicker() {
    fileInputRef.current?.click();
  }

  async function handleFileSelected(e) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    if (!file.name.endsWith(".json")) {
      alert("Only .json files are accepted.");
      return;
    }

    setUploading(true);
    setStatusMsg(null);
    try {
      await uploadRagSource(file, accessToken);
      setStatusMsg({ type: "success", text: `${file.name} added. Don't forget to reindex.` });
      setIndexDirty(true);
      await refresh();
    } catch (err) {
      setStatusMsg({ type: "error", text: `Upload failed: ${err.message}` });
    } finally {
      setUploading(false);
    }
  }

  async function handleDelete(filename) {
    if (!window.confirm(`Delete ${filename} from the RAG knowledge base? This cannot be undone.`)) {
      return;
    }
    setStatusMsg(null);
    try {
      await deleteRagSource(filename, accessToken);
      setStatusMsg({ type: "success", text: `${filename} deleted. Don't forget to reindex.` });
      setIndexDirty(true);
      await refresh();
    } catch (err) {
      setStatusMsg({ type: "error", text: `Deletion failed: ${err.message}` });
    }
  }

  async function handleReindex() {
    setReindexing(true);
    setStatusMsg(null);
    try {
      await reindexRagSources(accessToken);
      setStatusMsg({ type: "success", text: "RAG index rebuilt successfully." });
      setIndexDirty(false);
    } catch (err) {
      setStatusMsg({ type: "error", text: `Indexing failed: ${err.message}` });
    } finally {
      setReindexing(false);
    }
  }

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={styles.cardTitle}>Knowledge Base (RAG)</h3>
        <span style={{ fontSize: 13, color: styles.mutedText }}>{sources?.length ?? 0} file(s)</span>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          onChange={handleFileSelected}
          style={{ display: "none" }}
        />
        <button style={styles.uploadBtn} onClick={triggerFilePicker} disabled={uploading}>
          {uploading ? "Uploading..." : "+ Add a .json file"}
        </button>
        <button
          style={{ ...styles.reindexBtn, ...(indexDirty ? styles.reindexBtnDirty : {}) }}
          onClick={handleReindex}
          disabled={reindexing}
        >
          {reindexing ? "Reindexing..." : indexDirty ? "⚠ Reindex (pending changes)" : "Reindex"}
        </button>
      </div>

      {statusMsg && (
        <div style={statusMsg.type === "error" ? styles.errorBox : styles.successBox}>
          {statusMsg.text}
        </div>
      )}

      {loading && <div style={styles.info}>Loading...</div>}
      {error && <div style={styles.errorBox}>{error}</div>}

      {!loading && sources && (
        <div style={styles.tableWrap}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>File</th>
                <th style={styles.th}>Size</th>
                <th style={styles.th}>Modified</th>
                <th style={styles.th}></th>
              </tr>
            </thead>
            <tbody>
              {sources.map((s) => (
                <tr key={s.filename}>
                  <td style={styles.td}>{s.filename}</td>
                  <td style={styles.td}>{formatBytes(s.size_bytes)}</td>
                  <td style={styles.td}>{formatDate(s.modified_at)}</td>
                  <td style={{ ...styles.td, textAlign: "right" }}>
                    <button style={styles.deleteBtn} onClick={() => handleDelete(s.filename)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {sources.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ ...styles.td, textAlign: "center", color: styles.mutedText }}>
                    No source files yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ fontSize: 11, color: styles.mutedText, marginTop: 8 }}>
        Adding or deleting a file does not update the index automatically — click "Reindex" so agents use the latest content.
      </p>
    </div>
  );
}

function baseStyles({ cardBg, cardBorder, titleColor, mutedText, thBorder, tdBorder }) {
  return {
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
    cardTitle: { margin: 0, fontSize: 16, fontWeight: 600, color: titleColor },
    mutedText,
    info: { fontSize: 14, color: mutedText },
    errorBox: { fontSize: 13, color: "#b91c1c", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "8px 12px", marginBottom: 12 },
    successBox: { fontSize: 13, color: "#15803d", background: "#f0fdf4", border: "1px solid #bbf7d0", borderRadius: 8, padding: "8px 12px", marginBottom: 12 },
    uploadBtn: { fontSize: 13, padding: "8px 16px", borderRadius: 8, border: "1px solid #2563eb", background: "#eff6ff", color: "#2563eb", cursor: "pointer", fontWeight: 500 },
    reindexBtn: { fontSize: 13, padding: "8px 16px", borderRadius: 8, border: `1px solid ${cardBorder}`, background: cardBg, color: mutedText, cursor: "pointer", fontWeight: 500 },
    reindexBtnDirty: { border: "1px solid #f59e0b", background: "#fffbeb", color: "#b45309" },
    tableWrap: { overflowX: "auto" },
    table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
    th: { textAlign: "left", padding: "8px 10px", color: mutedText, fontWeight: 600, borderBottom: `1px solid ${thBorder}`, whiteSpace: "nowrap" },
    td: { padding: "10px 10px", borderBottom: `1px solid ${tdBorder}`, color: titleColor },
    deleteBtn: { fontSize: 12, padding: "5px 12px", borderRadius: 6, border: "1px solid #ef4444", background: "#fef2f2", color: "#ef4444", cursor: "pointer", fontWeight: 500 },
  };
}

const lightStyles = baseStyles({ cardBg: "#fff", cardBorder: "#e2e8f0", titleColor: "#0f172a", mutedText: "#94a3b8", thBorder: "#e2e8f0", tdBorder: "#f1f5f9" });
const darkStyles = baseStyles({ cardBg: "#0d1119", cardBorder: "#232b40", titleColor: "#e8eaf0", mutedText: "#5b6478", thBorder: "#232b40", tdBorder: "#161c2c" });