import { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import { sendChatMessage } from "../api";
import { useAuth } from "../context/AuthContext";

export default function ChatPage() {
  const { user, accessToken, isAuthenticated } = useAuth();

  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [quota, setQuota] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    // Once the guest trial is exhausted, stop sending messages entirely
    // instead of letting the user keep typing into a dead end.
    if (quota && quota.plan === "guest" && !quota.allowed) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatMessage(sessionId, text, isAuthenticated ? accessToken : null);
      setSessionId(data.session_id);
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

  const guestQuotaExhausted = quota && quota.plan === "guest" && !quota.allowed;

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        Orbit AI Assistant
        {isAuthenticated && (
          <span style={styles.headerSubtitle}> Signed in as  {user?.email}</span>
        )}
      </div>

      {!isAuthenticated && !guestQuotaExhausted && (
        <div style={styles.guestBanner}>
          You're chatting as a guest (limited free trial).{" "}
          <Link to="/signup" style={styles.bannerLink}>Create an account</Link> for full access.
        </div>
      )}

      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.placeholder}>
           Ask a question about Orbit solutions (Energy Management, IoT, SCADA...)
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              ...styles.bubble,
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              background: msg.role === "user" ? "#2563eb" : "#f1f5f9",
              color: msg.role === "user" ? "#fff" : "#111",
            }}
          >
            {msg.content}
          </div>
        ))}
        {loading && <div style={styles.typing}>Orbit is thinking...</div>}
        <div ref={bottomRef} />
      </div>

      {quota && (
        <div style={styles.quotaBar}>
          <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#64748b", marginBottom: 4 }}>
            <span>
              Plan: {quota.plan} — {quota.tokens_used.toLocaleString()} / {quota.token_limit.toLocaleString()}{" "}
                              {quota.plan === "guest" ? "messages" : "tokens"}
            </span>
            <span>{quota.remaining.toLocaleString()} remaining </span>
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
          <p style={{ margin: "0 0 10px", fontSize: 14, color: "#334155" }}>
            You've reached the limit of the free trial.
          </p>
          <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
            <Link to="/signup" style={styles.button}>Create Account</Link>
            <Link to="/login" style={styles.secondaryButton}> Sign In</Link>
          </div>
        </div>
      ) : (
        <div style={styles.inputBar}>
          <textarea
            style={styles.textarea}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message..."
            rows={1}
          />
          <button style={styles.button} onClick={handleSend} disabled={loading}>
            Send
          </button>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "calc(100vh - 49px)",
    maxWidth: 720,
    margin: "0 auto",
    fontFamily: "system-ui, sans-serif",
  },
  header: {
    padding: "16px 20px",
    fontWeight: 600,
    fontSize: 18,
    borderBottom: "1px solid #e2e8f0",
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  headerSubtitle: { fontSize: 12, fontWeight: 400, color: "#64748b" },
  guestBanner: {
    padding: "8px 20px",
    background: "#eff6ff",
    color: "#1e40af",
    fontSize: 13,
    borderBottom: "1px solid #dbeafe",
  },
  bannerLink: { color: "#2563eb", fontWeight: 600, textDecoration: "none" },
  messages: {
    flex: 1,
    overflowY: "auto",
    padding: 20,
    display: "flex",
    flexDirection: "column",
    gap: 10,
  },
  placeholder: {
    color: "#94a3b8",
    textAlign: "center",
    marginTop: 40,
  },
  bubble: {
    padding: "10px 14px",
    borderRadius: 12,
    maxWidth: "75%",
    whiteSpace: "pre-wrap",
    lineHeight: 1.4,
  },
  typing: {
    color: "#94a3b8",
    fontSize: 14,
    fontStyle: "italic",
  },
  inputBar: {
    display: "flex",
    gap: 8,
    padding: 16,
    borderTop: "1px solid #e2e8f0",
  },
  textarea: {
    flex: 1,
    padding: 10,
    borderRadius: 8,
    border: "1px solid #cbd5e1",
    resize: "none",
    fontFamily: "inherit",
    fontSize: 14,
  },
  button: {
    padding: "0 20px",
    height: 40,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    border: "none",
    background: "#2563eb",
    color: "#fff",
    fontWeight: 600,
    cursor: "pointer",
    textDecoration: "none",
    fontSize: 14,
  },
  secondaryButton: {
    padding: "0 20px",
    height: 40,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    border: "1px solid #cbd5e1",
    background: "#fff",
    color: "#334155",
    fontWeight: 600,
    cursor: "pointer",
    textDecoration: "none",
    fontSize: 14,
  },
  upgradePrompt: {
    padding: "20px",
    borderTop: "1px solid #e2e8f0",
    textAlign: "center",
    background: "#f8fafc",
  },
  quotaBar: {
    padding: "8px 16px",
    borderTop: "1px solid #e2e8f0",
    background: "#f8fafc",
  },
  quotaTrack: {
    height: 4,
    background: "#e2e8f0",
    borderRadius: 2,
    overflow: "hidden",
  },
  quotaFill: {
    height: "100%",
    borderRadius: 2,
    transition: "width 0.3s ease",
  },
};