import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
import { ThemeProvider, useTheme } from "./context/ThemeContext";
import ChatPage from "./pages/ChatPage";
import AdminPage from "./pages/AdminPage";
import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";
import VerifyEmailPage from "./pages/VerifyEmailPage";
import IntegrationsPage from "./pages/IntegrationsPage";
import ForgotPasswordPage from "./pages/ForgotPasswordPage";
import ResetPasswordPage from "./pages/ResetPasswordPage";

function RequireAdmin({ children }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();

  if (loading) return <div style={{ padding: 30 }}>Loading...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (!isAdmin) {
    return (
      <div style={{ padding: 30, fontFamily: "system-ui, sans-serif" }}>
        <h2>Access Denied</h2>
        <p style={{ color: "#64748b" }}>
          This page is restricted to administrators.
        </p>
      </div>
    );
  }
  return children;
}
function RequireAuth({ children }) {
  const { isAuthenticated, loading } = useAuth();

  if (loading) return <div style={{ padding: 30 }}>Chargement...</div>;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function NavBar() {
  const { isAuthenticated, isAdmin, user, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  const navStyles = isDark ? darkNavStyles : lightNavStyles;

  return (
    <nav style={navStyles.nav}>
      <div style={{ display: "flex", gap: 16 }}>
        <Link to="/chat" style={navStyles.link}>Chat</Link>
        {isAuthenticated && (
          <Link to="/integrations" style={navStyles.link}>
            Integrations
          </Link>
        )}
        {isAdmin && <Link to="/admin" style={navStyles.link}>Admin</Link>}
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button
          onClick={toggleTheme}
          style={navStyles.themeBtn}
          aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
          title={isDark ? "Switch to light mode" : "Switch to dark mode"}
        >
          {isDark ? (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41" />
            </svg>
          ) : (
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
          )}
        </button>
        {isAuthenticated ? (
          <>
            <span style={navStyles.userEmail}>{user?.email}</span>
            <button onClick={handleLogout} style={navStyles.logoutBtn}>Sign Out</button>
          </>
        ) : (
          <>
            <Link to="/login" style={navStyles.link}>Sign In</Link>
            <Link to="/signup" style={navStyles.link}>Sign Up</Link>
          </>
        )}
      </div>
    </nav>
  );
}

function AppRoutes() {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/" element={<Navigate to="/chat" replace />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/integrations" element={<RequireAuth><IntegrationsPage /></RequireAuth>} />
        <Route path="/admin" element={<RequireAdmin><AdminPage /></RequireAdmin>} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}

const lightNavStyles = {
  nav: {
    padding: "12px 20px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid #e2e8f0",
    background: "#fff",
    fontFamily: "system-ui, sans-serif",
  },
  link: { color: "#2563eb", textDecoration: "none", fontSize: 14, fontWeight: 500 },
  userEmail: { fontSize: 13, color: "#64748b" },
  logoutBtn: {
    fontSize: 13,
    padding: "6px 12px",
    borderRadius: 6,
    border: "1px solid #cbd5e1",
    background: "#fff",
    color: "#64748b",
    cursor: "pointer",
  },
  themeBtn: {
    width: 32,
    height: 32,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    border: "1px solid #cbd5e1",
    background: "#fff",
    color: "#64748b",
    cursor: "pointer",
  },
};

const darkNavStyles = {
  nav: {
    padding: "12px 20px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid #161c2c",
    background: "#05070d",
    fontFamily: "system-ui, sans-serif",
  },
  link: { color: "#5b9bff", textDecoration: "none", fontSize: 14, fontWeight: 500 },
  userEmail: { fontSize: 13, color: "#8b93a7" },
  logoutBtn: {
    fontSize: 13,
    padding: "6px 12px",
    borderRadius: 6,
    border: "1px solid #232b40",
    background: "#0d1119",
    color: "#c3c9d6",
    cursor: "pointer",
  },
  themeBtn: {
    width: 32,
    height: 32,
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: 8,
    border: "1px solid #232b40",
    background: "#0d1119",
    color: "#c3c9d6",
    cursor: "pointer",
  },
};