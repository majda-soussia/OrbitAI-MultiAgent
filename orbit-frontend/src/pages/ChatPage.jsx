import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  sendChatMessage,
  getMemoryStatus,
  setMemoryEnabled as apiSetMemoryEnabled,
} from "../api";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

const CHAT_SESSION_KEY = "orbit_chat_session_id";

const SUGGESTIONS = [
  "Present Orbit Smart Monitoring",
  "Quote for 5 factories",
  "What is predictive maintenance?",
  "Compare Orbit modules",
];

export default function ChatPage() {
  const { user, accessToken, isAuthenticated } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [sessionId, setSessionId] = useState(() => localStorage.getItem(CHAT_SESSION_KEY));
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [quota, setQuota] = useState(null);
  const [memoryEnabled, setMemoryEnabledState] = useState(true);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!isAuthenticated) return;
    let cancelled = false;
    getMemoryStatus(accessToken)
      .then((data) => { if (!cancelled) setMemoryEnabledState(data.memory_enabled); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [isAuthenticated, accessToken]);

  async function handleSend(overrideText) {
    const text = (overrideText ?? input).trim();
    if (!text || loading) return;

    if (quota && quota.plan === "guest" && !quota.allowed) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatMessage(sessionId, text, isAuthenticated ? accessToken : null);
      setSessionId(data.session_id);
      localStorage.setItem(CHAT_SESSION_KEY, data.session_id);
      if (data.quota) setQuota(data.quota);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response, agent: data.agent },
      ]);
    } catch (err) {
      console.error("Message send error:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Unable to connect to the server.", error: true },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleSuggestionClick(text) {
    if (loading) return;
    handleSend(text);
  }

  function handleNewConversation() {
    setMessages([]);
    if (memoryEnabled) return;
    setSessionId(null);
    localStorage.removeItem(CHAT_SESSION_KEY);
    setQuota(null);
  }

  async function handleMemoryToggle(e) {
    const enabled = e.target.checked;
    setMemoryEnabledState(enabled);
    if (isAuthenticated) {
      try {
        await apiSetMemoryEnabled(enabled, accessToken);
      } catch (err) {
        console.error("Memory toggle error:", err);
      }
    }
  }

  const guestQuotaExhausted = quota && quota.plan === "guest" && !quota.allowed;
  const isEmpty = messages.length === 0;

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        <div style={styles.header}>
          <div style={styles.headerTopRow}>
            <div style={styles.headerTitleBlock}>
              <span style={styles.headerDot} />
              <span style={styles.headerTitle}>Orbit AI Assistant</span>
              {isAuthenticated && (
                <span style={styles.headerSubtitle}>{user?.email}</span>
              )}
            </div>
            {isAuthenticated && (
              <div style={styles.headerControls}>
                <label style={styles.memoryLabel}>
                  <input
                    type="checkbox"
                    checked={memoryEnabled}
                    onChange={handleMemoryToggle}
                    style={styles.memoryCheckbox}
                  />
                  Remember conversation
                </label>
                <button style={styles.newConvoButton} onClick={handleNewConversation}>
                  + New conversation
                </button>
              </div>
            )}
          </div>
        </div>

        {!isAuthenticated && !guestQuotaExhausted && (
          <div style={styles.guestBanner}>
            You're chatting as a guest (limited free trial).{" "}
            <Link to="/signup" style={styles.bannerLink}>Create an account</Link> for full access.
          </div>
        )}

        {isEmpty ? (
          <div style={styles.emptyState}>
            <div style={styles.orb} />
            <h1 style={styles.emptyTitle}>Hello.</h1>
            <p style={styles.emptySubtitle}>What can I help you with today?</p>
            <p style={styles.emptyHint}>
              Ask about Orbit's Energy Management, Industrial IoT and Predictive Maintenance solutions.
            </p>
            <div style={styles.suggestionRow}>
              {SUGGESTIONS.map((s) => (
                <button key={s} style={styles.suggestionChip} onClick={() => handleSuggestionClick(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div style={styles.messages}>
            {messages.map((msg, i) => (
              <div
                key={i}
                style={{
                  ...styles.bubble,
                  alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                  background: msg.role === "user" ? "#2563eb" : styles.bubbleAssistantBg,
                  color: msg.role === "user" ? "#fff" : styles.bubbleAssistantColor,
                  border: msg.role === "user" ? "none" : styles.bubbleAssistantBorder,
                }}
              >
                {msg.content}
              </div>
            ))}
            {loading && <div style={styles.typing}>Orbit is thinking...</div>}
            <div ref={bottomRef} />
          </div>
        )}

        {quota && (
          <div style={styles.quotaBar}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: styles.mutedText, marginBottom: 4 }}>
              <span>
                Plan: {quota.plan} — {quota.tokens_used.toLocaleString()} / {quota.token_limit.toLocaleString()}{" "}
                {quota.plan === "guest" ? "messages" : "tokens"}
              </span>
              <span>{quota.remaining.toLocaleString()} remaining</span>
            </div>
            <div style={styles.quotaTrack}>
              <div style={{
                ...styles.quotaFill,
                width: `${Math.min(100, (quota.tokens_used / quota.token_limit) * 100)}%`,
                background: quota.remaining === 0 ? "#ef4444" : "#2563eb",
              }} />
            </div>
          </div>
        )}

        {guestQuotaExhausted ? (
          <div style={styles.upgradePrompt}>
            <p style={{ margin: "0 0 10px", fontSize: 14, color: styles.upgradeText }}>
              You've reached the limit of the free trial.
            </p>
            <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
              <Link to="/signup" style={styles.button}>Create Account</Link>
              <Link to="/login" style={styles.secondaryButton}>Sign In</Link>
            </div>
          </div>
        ) : (
          <div style={styles.inputBar}>
            <div style={styles.inputPill}>
              <textarea
                style={styles.textarea}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Type your message..."
                rows={1}
              />
              <button style={styles.sendButton} onClick={() => handleSend()} disabled={loading}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14" />
                  <path d="M13 6l6 6-6 6" />
                </svg>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function baseStyles({
  pageBg, headerBg, headerBorder, titleColor, subtitleColor, dotShadow,
  convoBtnBg, convoBtnBorder, convoBtnColor, guestBg, guestColor, guestBorder, bannerLink,
  emptyTitleColor, emptyHintColor, chipBg, chipBorder, chipColor,
  bubbleAssistantBg, bubbleAssistantColor, bubbleAssistantBorder, typingColor,
  pillBg, pillBorder, textColor, mutedText, upgradeBg, upgradeBorder, upgradeText,
  quotaTrackBg, secondaryBtnBorder, secondaryBtnColor,
}) {
  return {
    page: { background: pageBg, minHeight: "calc(100vh - 49px)" },
    container: {
      display: "flex", flexDirection: "column", height: "calc(100vh - 49px)",
      maxWidth: 760, margin: "0 auto", fontFamily: "system-ui, sans-serif",
    },
    header: { padding: "14px 24px", borderBottom: `1px solid ${headerBorder}`, background: headerBg },
    headerTopRow: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" },
    headerTitleBlock: { display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" },
    headerDot: { width: 8, height: 8, borderRadius: "50%", background: "#2563eb", boxShadow: `0 0 8px 1px ${dotShadow}`, flexShrink: 0 },
    headerTitle: { fontWeight: 600, fontSize: 15, color: titleColor },
    headerControls: { display: "flex", alignItems: "center", gap: 16 },
    memoryLabel: { display: "flex", alignItems: "center", gap: 6, color: subtitleColor, fontSize: 13, cursor: "pointer", userSelect: "none" },
    memoryCheckbox: { width: 15, height: 15, accentColor: "#2563eb", cursor: "pointer" },
    newConvoButton: {
      padding: "6px 14px", borderRadius: 8, border: `1px solid ${convoBtnBorder}`,
      background: convoBtnBg, color: convoBtnColor, fontSize: 13, fontWeight: 500, cursor: "pointer",
    },
    headerSubtitle: { fontSize: 12, fontWeight: 400, color: subtitleColor, marginLeft: 2 },
    guestBanner: { padding: "8px 20px", background: guestBg, color: guestColor, fontSize: 13, borderBottom: `1px solid ${guestBorder}` },
    bannerLink: { color: bannerLink, fontWeight: 600, textDecoration: "none" },
    emptyState: { flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: "0 24px", gap: 6 },
    orb: {
      width: 84, height: 84, borderRadius: "50%", marginBottom: 20,
      background: "radial-gradient(circle at 32% 28%, #6ea8ff, #2563eb 55%, #12318f 100%)",
      boxShadow: "0 0 60px 6px rgba(37, 99, 235, 0.35)",
    },
    emptyTitle: { margin: 0, fontSize: 34, fontWeight: 700, color: emptyTitleColor, letterSpacing: "-0.02em" },
    emptySubtitle: {
      margin: "6px 0 0", fontSize: 22, fontWeight: 600,
      background: "linear-gradient(90deg, #2563eb, #60a5fa)",
      WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
    },
    emptyHint: { margin: "16px 0 26px", fontSize: 14, color: emptyHintColor, maxWidth: 420, lineHeight: 1.5 },
    suggestionRow: { display: "flex", gap: 10, flexWrap: "wrap", justifyContent: "center" },
    suggestionChip: {
      padding: "8px 16px", borderRadius: 999, border: `1px solid ${chipBorder}`,
      background: chipBg, color: chipColor, fontSize: 13, cursor: "pointer",
    },
    messages: { flex: 1, overflowY: "auto", padding: 20, display: "flex", flexDirection: "column", gap: 10 },
    bubble: { padding: "10px 14px", borderRadius: 12, maxWidth: "75%", whiteSpace: "pre-wrap", lineHeight: 1.4, fontSize: 14 },
    bubbleAssistantBg, bubbleAssistantColor, bubbleAssistantBorder,
    typing: { color: typingColor, fontSize: 14, fontStyle: "italic" },
    inputBar: { padding: "16px 20px 22px" },
    inputPill: { display: "flex", alignItems: "flex-end", gap: 8, padding: "8px 8px 8px 18px", borderRadius: 26, border: `1px solid ${pillBorder}`, background: pillBg },
    textarea: { flex: 1, padding: "8px 0", border: "none", outline: "none", background: "transparent", resize: "none", fontFamily: "inherit", fontSize: 14, color: textColor },
    sendButton: {
      width: 36, height: 36, flexShrink: 0, display: "inline-flex", alignItems: "center", justifyContent: "center",
      borderRadius: "50%", border: "none", background: "linear-gradient(135deg, #6ea8ff, #2563eb)", color: "#fff", cursor: "pointer",
    },
    button: {
      padding: "0 20px", height: 40, display: "inline-flex", alignItems: "center", justifyContent: "center",
      borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", fontWeight: 600, cursor: "pointer", textDecoration: "none", fontSize: 14,
    },
    secondaryButton: {
      padding: "0 20px", height: 40, display: "inline-flex", alignItems: "center", justifyContent: "center",
      borderRadius: 8, border: `1px solid ${secondaryBtnBorder}`, background: "transparent", color: secondaryBtnColor,
      fontWeight: 600, cursor: "pointer", textDecoration: "none", fontSize: 14,
    },
    upgradePrompt: { padding: "20px", borderTop: `1px solid ${upgradeBorder}`, textAlign: "center", background: upgradeBg },
    upgradeText, mutedText,
    quotaBar: { padding: "8px 20px", borderTop: `1px solid ${upgradeBorder}`, background: upgradeBg },
    quotaTrack: { height: 4, background: quotaTrackBg, borderRadius: 2, overflow: "hidden" },
    quotaFill: { height: "100%", borderRadius: 2, transition: "width 0.3s ease" },
  };
}

const darkStyles = baseStyles({
  pageBg: "#05070d", headerBg: "#05070d", headerBorder: "#161c2c",
  titleColor: "#e8eaf0", subtitleColor: "#8b93a7", dotShadow: "rgba(37, 99, 235, 0.7)",
  convoBtnBg: "#0d1119", convoBtnBorder: "#232b40", convoBtnColor: "#c3c9d6",
  guestBg: "#0d1a33", guestColor: "#7fa8f0", guestBorder: "#16233d", bannerLink: "#5b9bff",
  emptyTitleColor: "#f3f4f8", emptyHintColor: "#7b8398",
  chipBg: "#0d1119", chipBorder: "#232b40", chipColor: "#c3c9d6",
  bubbleAssistantBg: "#151b2b", bubbleAssistantColor: "#e2e8f0", bubbleAssistantBorder: "1px solid #232b40",
  typingColor: "#5b6478",
  pillBg: "#0d1119", pillBorder: "#232b40", textColor: "#e8eaf0", mutedText: "#8b93a7",
  upgradeBg: "#0a0e17", upgradeBorder: "#161c2c", upgradeText: "#c3c9d6",
  quotaTrackBg: "#181f30", secondaryBtnBorder: "#232b40", secondaryBtnColor: "#c3c9d6",
});

const lightStyles = baseStyles({
  pageBg: "#f8fafc", headerBg: "#fff", headerBorder: "#e2e8f0",
  titleColor: "#0f172a", subtitleColor: "#64748b", dotShadow: "rgba(37, 99, 235, 0.35)",
  convoBtnBg: "#f8fafc", convoBtnBorder: "#cbd5e1", convoBtnColor: "#334155",
  guestBg: "#eff6ff", guestColor: "#1e40af", guestBorder: "#dbeafe", bannerLink: "#2563eb",
  emptyTitleColor: "#0f172a", emptyHintColor: "#64748b",
  chipBg: "#fff", chipBorder: "#e2e8f0", chipColor: "#334155",
  bubbleAssistantBg: "#f1f5f9", bubbleAssistantColor: "#111827", bubbleAssistantBorder: "none",
  typingColor: "#94a3b8",
  pillBg: "#fff", pillBorder: "#cbd5e1", textColor: "#0f172a", mutedText: "#64748b",
  upgradeBg: "#f8fafc", upgradeBorder: "#e2e8f0", upgradeText: "#334155",
  quotaTrackBg: "#e2e8f0", secondaryBtnBorder: "#cbd5e1", secondaryBtnColor: "#334155",
});