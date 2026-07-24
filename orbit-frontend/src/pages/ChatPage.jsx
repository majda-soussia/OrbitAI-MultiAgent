import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "../api";

export default function ChatPage() {
  const [sessionId, setSessionId] = useState(null);
  const [clientEmail, setClientEmail] = useState(null);
  const [emailInput, setEmailInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);
  const [quota, setQuota] = useState(null);  

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const data = await sendChatMessage(sessionId, text, clientEmail);
      setSessionId(data.session_id);
      if (data.quota) setQuota(data.quota);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.response, agent: data.agent },
      ]);
    } catch (err) {
      console.error("Erreur envoi message:", err);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Erreur de connexion au serveur.", error: true },
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
if (!clientEmail) {
    return (
      <div style={{ ...styles.container, alignItems: "center", justifyContent: "center", display: "flex", flexDirection: "column", gap: 12 }}>
        <h2>Bienvenue sur Orbit AI Assistant</h2>
        <p style={{ color: "#64748b" }}>Entrez votre email pour commencer</p>
        <input
          type="email"
          value={emailInput}
          onChange={(e) => setEmailInput(e.target.value)}
          placeholder="vous@entreprise.com"
          style={{ padding: 10, borderRadius: 8, border: "1px solid #cbd5e1", width: 280 }}
        />
        <button
          style={styles.button}
          onClick={() => emailInput.includes("@") && setClientEmail(emailInput.trim())}
        >
          Commencer
        </button>
      </div>
    );
  }
  return (
    <div style={styles.container}>
      <div style={styles.header}>Orbit AI Assistant</div>

      <div style={styles.messages}>
        {messages.length === 0 && (
          <div style={styles.placeholder}>
            Posez une question sur les solutions Orbit (Energy Management, IoT, SCADA...)
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
        {loading && <div style={styles.typing}>Orbit réfléchit...</div>}
        <div ref={bottomRef} />
      </div>
      {quota && (
          <div style={styles.quotaBar}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, color: "#64748b", marginBottom: 4 }}>
              <span>Plan {quota.plan} — {quota.tokens_used.toLocaleString()} / {quota.token_limit.toLocaleString()} tokens</span>
              <span>{quota.remaining.toLocaleString()} restants</span>
            </div>
            <div style={styles.quotaTrack}>
              <div style={{
                ...styles.quotaFill,
                width: `${Math.min(100, (quota.tokens_used / quota.token_limit) * 100)}%`,
                background: quota.remaining < quota.token_limit * 0.1 ? "#ef4444" : "#2563eb",
              }} />
            </div>
          </div>
        )}
      <div style={styles.inputBar}>
        <textarea
          style={styles.textarea}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Écrivez votre message..."
          rows={1}
        />
        <button style={styles.button} onClick={handleSend} disabled={loading}>
          Envoyer
        </button>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    flexDirection: "column",
    height: "100vh",
    maxWidth: 720,
    margin: "0 auto",
    fontFamily: "system-ui, sans-serif",
  },
  header: {
    padding: "16px 20px",
    fontWeight: 600,
    fontSize: 18,
    borderBottom: "1px solid #e2e8f0",
  },
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
    borderRadius: 8,
    border: "none",
    background: "#2563eb",
    color: "#fff",
    fontWeight: 600,
    cursor: "pointer",
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