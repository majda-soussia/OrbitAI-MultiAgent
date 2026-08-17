import { useState, useEffect, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { verifyEmail } from "../api";
import { useTheme } from "../context/ThemeContext";

export default function VerifyEmailPage() {
  const { isDark } = useTheme();
  const styles = isDark ? darkStyles : lightStyles;
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [status, setStatus] = useState(token ? "loading" : "error");
  const [message, setMessage] = useState(
    token ? "" : "Invalid verification link: no token found."
  );
  const calledRef = useRef(false);

  useEffect(() => {
    if (calledRef.current) return;
    calledRef.current = true;

    if (!token) return;

    (async () => {
      try {
        const result = await verifyEmail(token);
        setStatus("success");
        setMessage(
          result.message || "Your email has been successfully verified."
        );
      } catch (err) {
        setStatus("error");
        setMessage(
          err.message || "This verification link is invalid or has expired."
        );
      }
    })();
  }, [token]);

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        {status === "loading" && (
          <>
            <h1 style={styles.title}>Verifying your email...</h1>
            <p style={styles.subtitle}>
              Please wait while we verify your email address.
            </p>
          </>
        )}

        {status === "success" && (
          <>
            <div style={{ ...styles.iconWrap, background: styles.successIconBg }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#2563eb" strokeWidth="2">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>

            <h1 style={styles.title}>Email Verified</h1>
            <p style={styles.subtitle}>{message}</p>

            <Link to="/login" style={styles.button}>
              Sign In
            </Link>
          </>
        )}

        {status === "error" && (
          <>
            <div style={{ ...styles.iconWrap, background: styles.errorIconBg }}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#dc2626" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M15 9l-6 6M9 9l6 6" />
              </svg>
            </div>

            <h1 style={styles.title}>Verification Failed</h1>
            <p style={styles.subtitle}>{message}</p>

            <div style={{ display: "flex", gap: 10, justifyContent: "center" }}>
              <Link to="/signup" style={styles.secondaryButton}>
                Create Account
              </Link>

              <Link to="/login" style={styles.button}>
                Sign In
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function baseStyles({ pageBg, cardBg, cardBorder, shadow, titleColor, subtitleColor, successIconBg, errorIconBg, secondaryBtnBg, secondaryBtnBorder, secondaryBtnColor }) {
  return {
    container: { display: "flex", alignItems: "center", justifyContent: "center", minHeight: "calc(100vh - 49px)", fontFamily: "system-ui, sans-serif", background: pageBg },
    card: { background: cardBg, border: `1px solid ${cardBorder}`, borderRadius: 12, padding: "32px 36px", width: 380, textAlign: "center", boxShadow: shadow },
    iconWrap: { width: 56, height: 56, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" },
    successIconBg, errorIconBg,
    title: { margin: "0 0 8px", fontSize: 20, fontWeight: 600, color: titleColor },
    subtitle: { margin: "0 0 20px", fontSize: 14, color: subtitleColor, lineHeight: 1.5 },
    button: { padding: "10px 20px", borderRadius: 8, border: "none", background: "#2563eb", color: "#fff", fontWeight: 600, fontSize: 14, cursor: "pointer", textDecoration: "none", display: "inline-block" },
    secondaryButton: { padding: "10px 20px", borderRadius: 8, border: `1px solid ${secondaryBtnBorder}`, background: secondaryBtnBg, color: secondaryBtnColor, fontWeight: 600, fontSize: 14, cursor: "pointer", textDecoration: "none", display: "inline-block" },
  };
}

const lightStyles = baseStyles({
  pageBg: "#f8fafc", cardBg: "#fff", cardBorder: "#e2e8f0", shadow: "0 1px 3px rgba(0,0,0,0.06)",
  titleColor: "#0f172a", subtitleColor: "#64748b",
  successIconBg: "#eff6ff", errorIconBg: "#fef2f2",
  secondaryBtnBg: "#fff", secondaryBtnBorder: "#cbd5e1", secondaryBtnColor: "#334155",
});

const darkStyles = baseStyles({
  pageBg: "#05070d", cardBg: "#0d1119", cardBorder: "#232b40", shadow: "0 1px 3px rgba(0,0,0,0.3)",
  titleColor: "#e8eaf0", subtitleColor: "#8b93a7",
  successIconBg: "#151b2b", errorIconBg: "#2a1416",
  secondaryBtnBg: "#151b2b", secondaryBtnBorder: "#232b40", secondaryBtnColor: "#c3c9d6",
});