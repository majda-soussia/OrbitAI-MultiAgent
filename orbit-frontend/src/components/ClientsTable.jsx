import { useMemo, useState } from "react";
import { useTheme } from "../context/ThemeContext";

const SORT_OPTIONS = [
  { value: "tokens_desc", label: "Tokens (high to low)" },
  { value: "tokens_asc", label: "Tokens (low to high)" },
  { value: "last_seen_desc", label: "Last seen (recent first)" },
  { value: "email_asc", label: "Client (A-Z)" },
];

export default function ClientsTable({ clients, onSelectClient }) {
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [search, setSearch] = useState("");
  const [planFilter, setPlanFilter] = useState("all");
  const [industryFilter, setIndustryFilter] = useState("all");
  const [sortBy, setSortBy] = useState("tokens_desc");

  const rows = useMemo(() => Object.entries(clients || {}), [clients]);

  const industries = useMemo(() => {
    const set = new Set();
    rows.forEach(([, c]) => {
      if (c.industry_type) set.add(c.industry_type);
    });
    return Array.from(set).sort();
  }, [rows]);

  const filtered = useMemo(() => {
    let result = rows.filter(([email, c]) => {
      const matchesSearch = email.toLowerCase().includes(search.toLowerCase());
      const matchesPlan = planFilter === "all" || c.plan === planFilter;
      const matchesIndustry = industryFilter === "all" || c.industry_type === industryFilter;
      return matchesSearch && matchesPlan && matchesIndustry;
    });

    result = result.sort(([emailA, a], [emailB, b]) => {
      switch (sortBy) {
        case "tokens_asc":
          return a.tokens_used - b.tokens_used;
        case "tokens_desc":
          return b.tokens_used - a.tokens_used;
        case "last_seen_desc":
          return (b.last_seen || "").localeCompare(a.last_seen || "");
        case "email_asc":
          return emailA.localeCompare(emailB);
        default:
          return 0;
      }
    });

    return result;
  }, [rows, search, planFilter, industryFilter, sortBy]);

  return (
    <div style={styles.card}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h3 style={styles.cardTitle}>Clients</h3>
        <span style={{ fontSize: 13, color: styles.mutedText }}>{filtered.length} of {rows.length}</span>
      </div>

      <div style={styles.filterRow}>
        <input
          type="text"
          placeholder="Search by email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={styles.searchInput}
        />
        <select value={planFilter} onChange={(e) => setPlanFilter(e.target.value)} style={styles.select}>
          <option value="all">All plans</option>
          <option value="standard">Standard</option>
          <option value="premium">Premium</option>
        </select>
        <select value={industryFilter} onChange={(e) => setIndustryFilter(e.target.value)} style={styles.select}>
          <option value="all">All industries</option>
          {industries.map((ind) => (
            <option key={ind} value={ind}>{ind}</option>
          ))}
        </select>
        <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} style={styles.select}>
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>

      <div style={styles.tableWrap}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>Client</th>
              <th style={styles.th}>Industry</th>
              <th style={styles.th}>Machines</th>
              <th style={styles.th}>Plan</th>
              <th style={styles.th}>Tokens</th>
              <th style={styles.th}>Last Seen</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(([email, c]) => (
              <tr key={email} style={styles.row} onClick={() => onSelectClient(email)}>
                <td style={styles.td}>{email}</td>
                <td style={styles.td}>{c.industry_type || <span style={styles.muted}>—</span>}</td>
                <td style={styles.td}>{c.machine_count ?? <span style={styles.muted}>—</span>}</td>
                <td style={styles.td}>
                  <span style={c.plan === "premium" ? styles.badgePremium : styles.badgeStandard}>
                    {c.plan}
                  </span>
                </td>
                <td style={styles.td}>
                  {c.tokens_used.toLocaleString()} / {c.token_limit.toLocaleString()}
                </td>
                <td style={styles.td}>{c.last_seen === "—" ? "—" : new Date(c.last_seen).toLocaleString()}</td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} style={{ ...styles.td, textAlign: "center", color: styles.mutedText }}>
                  No clients match these filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p style={{ fontSize: 11, color: styles.mutedText, marginTop: 8 }}>
        Google / Memory columns will need a bulk-status endpoint to add without
        an N+1 query per client — not included yet.
      </p>
    </div>
  );
}

function baseStyles({ cardBg, cardBorder, titleColor, mutedText, inputBg, inputBorder, inputColor, thBorder, rowHover, tdBorder }) {
  return {
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "16px 20px", fontFamily: "system-ui, sans-serif" },
    cardTitle: { margin: 0, fontSize: 16, fontWeight: 600, color: titleColor },
    mutedText,
    filterRow: { display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 14 },
    searchInput: { flex: "1 1 200px", padding: "8px 12px", borderRadius: 8, border: `1px solid ${inputBorder}`, fontSize: 13, outline: "none", background: inputBg, color: inputColor },
    select: { padding: "8px 10px", borderRadius: 8, border: `1px solid ${inputBorder}`, fontSize: 13, background: inputBg, color: inputColor },
    tableWrap: { overflowX: "auto" },
    table: { width: "100%", borderCollapse: "collapse", fontSize: 13 },
    th: { textAlign: "left", padding: "8px 10px", color: mutedText, fontWeight: 600, borderBottom: `1px solid ${thBorder}`, whiteSpace: "nowrap" },
    row: { cursor: "pointer" },
    td: { padding: "10px 10px", borderBottom: `1px solid ${tdBorder}`, color: titleColor },
    muted: { color: mutedText },
    badgePremium: { background: "#eff6ff", color: "#2563eb", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
    badgeStandard: { background: "#f1f5f9", color: "#64748b", fontSize: 11, fontWeight: 600, padding: "2px 8px", borderRadius: 6 },
  };
}

const lightStyles = baseStyles({
  cardBg: "#fff", cardBorder: "#e2e8f0", titleColor: "#0f172a", mutedText: "#94a3b8",
  inputBg: "#fff", inputBorder: "#cbd5e1", inputColor: "#334155", thBorder: "#e2e8f0", tdBorder: "#f1f5f9",
});

const darkStyles = baseStyles({
  cardBg: "#0d1119", cardBorder: "#232b40", titleColor: "#e8eaf0", mutedText: "#5b6478",
  inputBg: "#151b2b", inputBorder: "#232b40", inputColor: "#e8eaf0", thBorder: "#232b40", tdBorder: "#161c2c",
});