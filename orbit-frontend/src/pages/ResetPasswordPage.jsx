import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ResetPasswordPage() {
  const { resetPassword } = useAuth();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      await resetPassword(token, password);
      setSuccess(true);
      setTimeout(() => navigate("/login"), 2500);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div style={styles.container}>
        <div style={styles.card}>
          <h1 style={styles.title}>Invalid Link</h1>
          <p style={styles.subtitle}>
            This password reset link is missing or malformed.
          </p>
          <p style={styles.footerText}>
            <Link to="/forgot-password" style={styles.link}>
              Request a new link
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <h1 style={styles.title}>Set New Password</h1>
        <p style={styles.subtitle}>Choose a new password for your account</p>

        {success ? (
          <div style={styles.success}>
            Password set successfully. Redirecting to sign in...
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={styles.form}>
            <label style={styles.label}>
              New Password
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                style={styles.input}
                placeholder="••••••••"
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
              {loading ? "Setting password..." : "Set Password"}
            </button>
          </form>
        )}

        <p style={styles.footerText}>
          <Link to="/login" style={styles.link}>
            Back to sign in
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