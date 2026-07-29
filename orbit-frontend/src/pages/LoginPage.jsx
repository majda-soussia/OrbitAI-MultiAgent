import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email.trim(), password);
      navigate("/chat");
    } catch (err) {
      setError(err.message || "Connexion impossible.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Connexion</h1>
        <p style={styles.subtitle}>Accédez à votre espace Orbit AI Assistant</p>

        <form onSubmit={handleSubmit} style={styles.form}>
          <label style={styles.label}>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={styles.input}
              placeholder="vous@entreprise.com"
              autoComplete="email"
            />
          </label>

          <label style={styles.label}>
            Mot de passe
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={styles.input}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </label>

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" style={styles.button} disabled={loading}>
            {loading ? "Connexion..." : "Se connecter"}
          </button>
        </form>

        <p style={styles.footerText}>
          Pas encore de compte ? <Link to="/signup" style={styles.link}>Créer un compte</Link>
        </p>
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
    width: 360,
    boxShadow: "0 1px 3px rgba(0,0,0,0.06)",
  },
  title: { margin: "0 0 4px", fontSize: 22, fontWeight: 600, color: "#0f172a" },
  subtitle: { margin: "0 0 24px", fontSize: 14, color: "#64748b" },
  form: { display: "flex", flexDirection: "column", gap: 16 },
  label: { display: "flex", flexDirection: "column", gap: 6, fontSize: 13, color: "#334155", fontWeight: 500 },
  input: {
    padding: "10px 12px",
    borderRadius: 8,
    border: "1px solid #cbd5e1",
    fontSize: 14,
    fontFamily: "inherit",
  },
  button: {
    marginTop: 4,
    padding: "10px 0",
    borderRadius: 8,
    border: "none",
    background: "#2563eb",
    color: "#fff",
    fontWeight: 600,
    fontSize: 14,
    cursor: "pointer",
  },
  error: {
    background: "#fef2f2",
    color: "#dc2626",
    padding: "8px 12px",
    borderRadius: 8,
    fontSize: 13,
  },
  footerText: { marginTop: 20, fontSize: 13, color: "#64748b", textAlign: "center" },
  link: { color: "#2563eb", fontWeight: 500, textDecoration: "none" },
};