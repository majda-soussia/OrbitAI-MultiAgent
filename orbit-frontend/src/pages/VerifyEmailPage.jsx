import { useState, useEffect, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { verifyEmail } from "../api";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState(token ? "loading" : "error"); // "loading" | "success" | "error"
  const [message, setMessage] = useState(
    token ? "" : "Lien de vérification invalide : aucun token trouvé."
  );
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return; // avoid double-call under React StrictMode
    calledRef.current = true;

    if (!token) {
      return;
    }

    (async () => {
      try {
        const result = await verifyEmail(token);
        setStatus("success");
        setMessage(result.message || "Votre email a été vérifié avec succès.");
      } catch (err) {
        setStatus("error");
        setMessage(err.message || "Ce lien de vérification est invalide ou a expiré.");
      }
    })();
  }, [token]);

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {status === "loading" && (
          <>
            <h1 style={styles.title}>Vérification en cours...</h1>
            <p style={styles.subtitle}>Merci de patienter un instant.</p>
          </>
        )}

        {status === "success" && (
          <>
            <div style={{ ...styles.iconWrap, background: "#eff6ff" }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <h1 style={styles.title}>Email vérifié</h1>
            <p style={styles.subtitle}>{message}</p>
            <Link to="/login" style={styles.button}>Se connecter</Link>
          </>
        )}

        {status === "error" && (
          <>
            <div style={{ ...styles.iconWrap, background: "#fef2f2" }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M15 9l-6 6M9 9l6 6" />
              </svg>
            </div>
            <h1 style={styles.title}>Échec de la vérification</h1>
            <p style={styles.subtitle}>{message}</p>
            <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
              <Link to="/signup" style={styles.secondaryButton}>Créer un compte</Link>
              <Link to="/login" style={styles.button}>Se connecter</Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "calc(100vh - 49px)",
    fontFamily: "system-ui, sans-serif",
    background: "#f8fafc",
  },
  card: {
    background: "#fff",
    border: "1px solid #e2e8f0",
    borderRadius: 12,
    padding: "32px 36px",
    width: 380,
    textAlign: "center",
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  iconWrap: {
    width: 56,
    height: 56,
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    margin: "0 auto 16px",
  },
  title: { margin: "0 0 8px", fontSize: 20, fontWeight: 600, color: "#0f172a" },
  subtitle: { margin: "0 0 20px", fontSize: 14, color: "#64748b" },
  button: {
    padding: "10px 20px",
    borderRadius: 8,
    border: "none",
    background: "#2563eb",
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    textDecoration: "none",
    display: "inline-block",
  },
  secondaryButton: {
    padding: "10px 20px",
    borderRadius: 8,
    border: "1px solid #cbd5e1",
    background: "#fff",
    color: "#334155",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
    textDecoration: "none",
    display: "inline-block",
  },
};