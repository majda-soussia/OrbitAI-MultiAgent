import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";

export default function SignupPage() {
  const { signup } = useAuth();
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters long.");
      return;
    }

    setLoading(true);

    try {
      const result = await signup(email.trim(), password);
      setSuccess(
        result.message ||
          "Your account has been created. Please check your email to verify your account."
      );
    } catch (err) {
      setError(err.message || "Unable to create your account.");
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h1 style={styles.title}>Check your inbox</h1>

          <p style={styles.subtitle}>{success}</p>

          <p style={styles.footerText}>
            <Link to="/login" style={styles.link}>
              Back to Sign In
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Create an account</h1>
        <p style={styles.subtitle}>Join Orbit AI Assistant</p>

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

          <label style={styles.label}>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={styles.input}
              placeholder="At least 8 characters"
              autoComplete="new-password"
            />
          </label>

          <label style={styles.label}>
            Confirm Password
            <input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
              style={styles.input}
              placeholder="••••••••"
              autoComplete="new-password"
            />
          </label>

          {error && <div style={styles.error}>{error}</div>}

          <button type="submit" style={styles.button} disabled={loading}>
            {loading ? "Creating account..." : "Create Account"}
          </button>
        </form>

        <p style={styles.footerText}>
          Already have an account?{" "}
          <Link to="/login" style={styles.link}>
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}

function baseStyles({ pageBg, cardBg, cardBorder, shadow, titleColor, subtitleColor, labelColor, inputBg, inputBorder, inputColor, errorBg, errorColor, footerColor, linkColor }) {
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
    footerText: { marginTop: 20, fontSize: 13, color: footerColor, textAlign: "center" },
    link: { color: linkColor, fontWeight: 500, textDecoration: "none" },
  };
}

const lightStyles = baseStyles({
  pageBg: "#f8fafc", cardBg: "#fff", cardBorder: "#e2e8f0", shadow: "0 1px 3px rgba(0,0,0,0.06)",
  titleColor: "#0f172a", subtitleColor: "#64748b", labelColor: "#334155",
  inputBg: "#fff", inputBorder: "#cbd5e1", inputColor: "#0f172a",
  errorBg: "#fef2f2", errorColor: "#dc2626", footerColor: "#64748b", linkColor: "#2563eb",
});

const darkStyles = baseStyles({
  pageBg: "#05070d", cardBg: "#0d1119", cardBorder: "#232b40", shadow: "0 1px 3px rgba(0,0,0,0.3)",
  titleColor: "#e8eaf0", subtitleColor: "#8b93a7", labelColor: "#c3c9d6",
  inputBg: "#151b2b", inputBorder: "#232b40", inputColor: "#e8eaf0",
  errorBg: "#2a1416", errorColor: "#f87171", footerColor: "#8b93a7", linkColor: "#5b9bff",
});