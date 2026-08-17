import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export default function ForgotPasswordPage() {
  const { forgotPassword } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

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

function baseStyles({ pageBg, cardBg, cardBorder, shadow, titleColor, subtitleColor, labelColor, inputBg, inputBorder, inputColor, errorBg, errorColor, successBg, successColor, footerColor, linkColor }) {
  return {
    container: { display: "flex", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 49px)", fontFamily: "system-ui, sans-serif", background: pageBg },
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "32px 36px", width: 360, boxShadow: shadow },
    title: { margin: "0 0 4px", fontSize: 22, fontWeight: 600, color: titleColor },
    subtitle: { margin: "0 0 24px", fontSize: 14, color: subtitleColor },
    form: { display: "flex", flexDirection: "column", gap: 16 },
    label: { display: "flex", flexDirection: "column", gap: 6, fontSize: 13, color: labelColor, fontWeight: 500 },
    input: { padding: "10px 12px", borderRadius: 8, border: `1px solid ${inputBorder}`, fontSize: 14, fontFamily: "inherit", background: inputBg, color: inputColor },
    button: { marginTop: 4, padding: "10px 0", borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", fontWeight: 600, fontSize: 14, cursor: "pointer" },
    error: { background: errorBg, color: errorColor, padding: "8px 12px", borderRadius: 8, fontSize: 13 },
    success: { background: successBg, color: successColor, padding: "12px 14px", borderRadius: 8, fontSize: 13, lineHeight: 1.5 },
    footerText: { marginTop: 20, fontSize: 13, color: footerColor, textAlign: "center" },
    link: { color: linkColor, fontWeight: 500, textDecoration: "none" },
  };
}

const lightStyles = baseStyles({
  pageBg: "#f8fafc", cardBg: "#fff", cardBorder: "#e2e8f0", shadow: "0 1px 3px rgba(0,0,0,0.06)",
  titleColor: "#0f172a", subtitleColor: "#64748b", labelColor: "#334155",
  inputBg: "#fff", inputBorder: "#cbd5e1", inputColor: "#0f172a",
  errorBg: "#fef2f2", errorColor: "#dc2626", successBg: "#f0fdf4", successColor: "#16a34a",
  footerColor: "#64748b", linkColor: "#2563eb",
});

const darkStyles = baseStyles({
  pageBg: "#05070d", cardBg: "#0d1119", cardBorder: "#232b40", shadow: "0 1px 3px rgba(0,0,0,0.3)",
  titleColor: "#e8eaf0", subtitleColor: "#8b93a7", labelColor: "#c3c9d6",
  inputBg: "#151b2b", inputBorder: "#232b40", inputColor: "#e8eaf0",
  errorBg: "#2a1416", errorColor: "#f87171", successBg: "#0f2418", successColor: "#4ade80",
  footerColor: "#8b93a7", linkColor: "#5b9bff",
});