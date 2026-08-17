import { useState, useEffect, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { getTokensCost, setTokenPrice } from "../api";

const CURRENT_MONTH_LABEL = new Date().toLocaleDateString(undefined, { month: "long", year: "numeric" });

function formatCost(value, currency) {
  return `${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })} ${currency}`;
}

export default function CostSummaryCard() {
  const { accessToken } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [cost, setCost] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [editing, setEditing] = useState(false);
  const [priceInput, setPriceInput] = useState("");
  const [currencyInput, setCurrencyInput] = useState("€");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getTokensCost(accessToken);
      setCost(data);
      setPriceInput(String(data.price_per_1k_tokens));
      setCurrencyInput(data.currency || "€");
    } catch (err) {
      setError(err.message || "Échec du chargement du coût.");
    } finally {
      setLoading(false);
    }
  }, [accessToken]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleSavePrice() {
    const parsed = parseFloat(priceInput.replace(",", "."));
    if (Number.isNaN(parsed) || parsed < 0) {
      setSaveError("Entre un nombre valide, positif ou zéro.");
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      await setTokenPrice(parsed, currencyInput.trim() || "€", accessToken);
      setEditing(false);
      await refresh();
    } catch (err) {
      setSaveError(err.message || "Échec de l'enregistrement.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <h3 style={styles.cardTitle}>Estimated Cost</h3>
        {!editing && (
          <button style={styles.editLink} onClick={() => setEditing(true)}>
            {cost?.is_free ? "Set a price" : "Edit price"}
          </button>
        )}
      </div>

      {loading && <div style={styles.info}>Chargement...</div>}
      {error && <div style={styles.errorBox}>{error}</div>}

      {editing && (
        <div style={styles.editBox}>
          <p style={{ fontSize: 12, color: styles.mutedText, margin: "0 0 8px" }}>
            Prix pour 1000 tokens (mets 0 si le modèle est gratuit / local).
          </p>
          <div style={{ display: "flex", gap: 8, marginBottom: 8 }}>
            <input
              type="text"
              inputMode="decimal"
              value={priceInput}
              onChange={(e) => setPriceInput(e.target.value)}
              placeholder="0.002"
              style={styles.priceInput}
            />
            <input
              type="text"
              value={currencyInput}
              onChange={(e) => setCurrencyInput(e.target.value)}
              placeholder="€"
              style={styles.currencyInput}
              maxLength={4}
            />
          </div>
          {saveError && <div style={styles.errorBox}>{saveError}</div>}
          <div style={{ display: "flex", gap: 8 }}>
            <button style={styles.saveBtn} onClick={handleSavePrice} disabled={saving}>
              {saving ? "Enregistrement..." : "Enregistrer"}
            </button>
            <button style={styles.cancelBtn} onClick={() => setEditing(false)} disabled={saving}>
              Annuler
            </button>
          </div>
        </div>
      )}

      {!editing && !loading && cost && cost.is_free && (
        <div style={styles.freeBox}>
          <span style={styles.freeBadge}>Local model — free</span>
          <p style={{ fontSize: 12, color: styles.mutedText, margin: "8px 0 0" }}>
            Prix actuel : 0 {cost.currency} / 1K tokens. Clique sur "Set a price" pour définir un tarif si tu passes à une API payante.
          </p>
        </div>
      )}

      {!editing && !loading && cost && !cost.is_free && (
        <>
          <div style={styles.mainValue}>{formatCost(cost.cost_this_month, cost.currency)}</div>
          <p style={{ fontSize: 12, color: styles.mutedText, margin: "2px 0 4px" }}>
            usage estimé pour {CURRENT_MONTH_LABEL}
          </p>
          <p style={{ fontSize: 11, color: styles.mutedText, margin: "0 0 14px", fontFamily: "monospace" }}>
            {cost.tokens_this_month.toLocaleString()} tokens ÷ 1000 × {cost.price_per_1k_tokens} {cost.currency}
          </p>

          <div style={styles.row}>
            <span style={styles.rowLabel}>Total (depuis le début)</span>
            <span style={styles.rowValue}>{formatCost(cost.total_cost, cost.currency)}</span>
          </div>
          <p style={{ fontSize: 10, color: styles.mutedText, margin: "0 0 6px", fontFamily: "monospace" }}>
            {cost.total_tokens.toLocaleString()} tokens ÷ 1000 × prix
          </p>
          <div style={styles.row}>
            <span style={styles.rowLabel}>Prix / 1K tokens</span>
            <span style={styles.rowValue}>{formatCost(cost.price_per_1k_tokens, cost.currency)}</span>
          </div>

          {Object.keys(cost.by_agent_cost).length > 0 && (
            <div style={{ marginTop: 12 }}>
              <p style={{ fontSize: 11, color: styles.mutedText, margin: "0 0 6px", textTransform: "uppercase", letterSpacing: 0.4 }}>
                Par agent
              </p>
              {Object.entries(cost.by_agent_cost)
                .sort(([, a], [, b]) => b - a)
                .map(([agent, value]) => (
                  <div key={agent}>
                    <div style={styles.row}>
                      <span style={styles.rowLabel}>{agent.replace("Agent", "")}</span>
                      <span style={styles.rowValue}>{formatCost(value, cost.currency)}</span>
                    </div>
                    <p style={{ fontSize: 10, color: styles.mutedText, margin: "0 0 2px", fontFamily: "monospace" }}>
                      {(cost.by_agent_tokens[agent] || 0).toLocaleString()} tokens ÷ 1000 × {cost.price_per_1k_tokens} {cost.currency}
                    </p>
                  </div>
                ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

function baseStyles({ cardBg, cardBorder, titleColor, mutedText, freeBg, freeBorder, freeColor, rowBorder, inputBg, inputBorder, inputColor, editLinkColor }) {
  return {
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
    cardTitle: { margin: 0, fontSize: 15, fontWeight: 600, color: titleColor },
    mutedText,
    info: { fontSize: 14, color: mutedText },
    errorBox: { fontSize: 13, color: "#b91c1c", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "8px 12px", marginBottom: 8 },
    editLink: { fontSize: 12, color: editLinkColor, background: "transparent", border: "none", cursor: "pointer", fontWeight: 500, padding: 0 },
    editBox: { marginTop: 8 },
    priceInput: { flex: 1, padding: "7px 10px", borderRadius: 6, border: `1px solid ${inputBorder}`, fontSize: 13, background: inputBg, color: inputColor, outline: "none" },
    currencyInput: { width: 50, padding: "7px 8px", borderRadius: 6, border: `1px solid ${inputBorder}`, fontSize: 13, background: inputBg, color: inputColor, outline: "none", textAlign: "center" },
    saveBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: "1px solid #2563eb", background: "#2563eb", color: "#fff", cursor: "pointer", fontWeight: 500 },
    cancelBtn: { fontSize: 12, padding: "6px 14px", borderRadius: 6, border: `1px solid ${inputBorder}`, background: "transparent", color: mutedText, cursor: "pointer" },
    freeBox: { padding: "6px 0" },
    freeBadge: { display: "inline-block", background: freeBg, color: freeColor, border: `1px solid ${freeBorder}`, fontSize: 12, fontWeight: 600, padding: "4px 10px", borderRadius: 6 },
    mainValue: { fontSize: 26, fontWeight: 700, color: titleColor },
    row: { display: "flex", justifyContent: "space-between", fontSize: 12, padding: "6px 0", borderTop: `1px solid ${rowBorder}` },
    rowLabel: { color: mutedText },
    rowValue: { color: titleColor, fontWeight: 500 },
  };
}

const lightStyles = baseStyles({
  cardBg: "#fff", cardBorder: "#e2e8f0", titleColor: "#0f172a", mutedText: "#64748b",
  freeBg: "#f0fdf4", freeBorder: "#bbf7d0", freeColor: "#15803d", rowBorder: "#f1f5f9",
  inputBg: "#fff", inputBorder: "#cbd5e1", inputColor: "#0f172a", editLinkColor: "#2563eb",
});

const darkStyles = baseStyles({
  cardBg: "#0d1119", cardBorder: "#232b40", titleColor: "#e8eaf0", mutedText: "#8b93a7",
  freeBg: "#0f2418", freeBorder: "#1c3a29", freeColor: "#4ade80", rowBorder: "#161c2c",
  inputBg: "#151b2b", inputBorder: "#232b40", inputColor: "#e8eaf0", editLinkColor: "#5b9bff",
});