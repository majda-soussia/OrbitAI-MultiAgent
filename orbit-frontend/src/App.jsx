import { BrowserRouter, Routes, Route, Navigate, Link, useNavigate } from "react-router-dom";
import { AuthProvider, useAuth } from "./context/AuthContext";
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
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <nav style={styles.nav}>
      <div style={{ display: "flex", gap: 16 }}>
        <Link to="/chat" style={styles.link}>Chat</Link>
        {isAuthenticated && (
  <Link to="/integrations" style={styles.link}>
    
    Integrations
  </Link>
)}
        {isAdmin && <Link to="/admin" style={styles.link}>Admin</Link>}
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
        {isAuthenticated ? (
          <>
            <span style={{ fontSize: 13, color: "#64748b" }}>{user?.email}</span>
            <button onClick={handleLogout} style={styles.logoutBtn}>Sign Out</button>
          </>
        ) : (
          <>
            <Link to="/login" style={styles.link}>Sign In</Link>
            <Link to="/signup" style={styles.link}>Sign Up</Link>
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
        <Route path="/integrations" element={ <RequireAuth><IntegrationsPage /></RequireAuth>}/>
        <Route path="/admin" element={<RequireAdmin><AdminPage /></RequireAdmin>}/>
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

const styles = {
  nav: {
    padding: "12px 20px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    borderBottom: "1px solid #e2e8f0",
    fontFamily: "system-ui, sans-serif",
  },
  link: { color: "#2563eb", textDecoration: "none", fontSize: 14, fontWeight: 500 },
  logoutBtn: {
    fontSize: 13,
    padding: "6px 12px",
    borderRadius: 6,
    border: "1px solid #cbd5e1",
    background: "#fff",
    color: "#64748b",
    cursor: "pointer",
  },
};