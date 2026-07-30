import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ForgotPasswordPage() {
  const { forgotPassword } = useAuth();

  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await forgotPassword(email.trim());
      // On affiche le même message de succès que la requête ait abouti
      // ou non côté backend (le backend lui-même ne révèle jamais si
      // l'email existe) — évite toute fuite d'info côté UI aussi.
      setSubmitted(true);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Forgot Password</h1>
        <p style={styles.subtitle}>
          Enter your email and we'll send you a reset link
        </p>

        {submitted ? (
          <div style={styles.success}>
            If an account exists with this email, a reset link has been sent.
            Check your inbox.
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={styles.form}>
            <label style={styles.label}>
              Email
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={styles.input}
                placeholder="you@company.com"
                autoComplete="email"
              />
            </label>

            {error && <div style={styles.error}>{error}</div>}

            <button type="submit" style={styles.button} disabled={loading}>
              {loading ? "Sending..." : "Send Reset Link"}
            </button>
          </form>
        )}

        <p style={styles.footerText}>
          Remembered your password?{" "}
          <Link to="/login" style={styles.link}>
            Sign in
          </Link>
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
  title: {
    margin: "0 0 4px",
    fontSize: 22,
    fontWeight: 600,
    color: "#0f172a",
  },
  subtitle: {
    margin: "0 0 24px",
    fontSize: 14,
    color: "#64748b",
  },
  form: {
    display: "flex",
    flexDirection: "column",
    gap: 16,
  },
  label: {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    fontSize: 13,
    color: "#334155",
    fontWeight: 500,
  },
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
  success: {
    background: "#f0fdf4",
    color: "#16a34a",
    padding: "12px 14px",
    borderRadius: 8,
    fontSize: 13,
    lineHeight: 1.5,
  },
  footerText: {
    marginTop: 20,
    fontSize: 13,
    color: "#64748b",
    textAlign: "center",
  },
  link: {
    color: "#2563eb",
    fontWeight: 500,
    textDecoration: "none",
  },
};