/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useState, useEffect, useCallback } from "react";
import * as api from "../api";

const AuthContext = createContext(null);

const ACCESS_TOKEN_KEY = "orbit_access_token";
const REFRESH_TOKEN_KEY = "orbit_refresh_token";

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() => localStorage.getItem(ACCESS_TOKEN_KEY));
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    setAccessToken(null);
    setUser(null);
  }, []);
  useEffect(() => {
    api.setAuthCallbacks({
      onRefreshed: (newAccessToken) => setAccessToken(newAccessToken),
      onExpired: () => logout(),
    });
  }, [logout]);

  // On mount (or when the token changes), fetch the current user's
  // profile to confirm the stored token is still valid.
  useEffect(() => {
    let cancelled = false;

    async function loadUser() {
      if (!accessToken) {
        setUser(null);
        setLoading(false);
        return;
      }
      try {
        const me = await api.getCurrentUser(accessToken);
        if (!cancelled) setUser(me);
      } catch {
        // Token invalid/expired and refresh failed elsewhere — log out.
        if (!cancelled) logout();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadUser();
    return () => { cancelled = true; };
  }, [accessToken, logout]);

  async function login(email, password) {
    const data = await api.login(email, password);
    localStorage.setItem(ACCESS_TOKEN_KEY, data.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
    setAccessToken(data.access_token);
    setUser(data.user);
    return data.user;
  }

  async function signup(email, password, plan = "standard") {
    return api.signup(email, password, plan);
  }
  async function forgotPassword(email) {
    return api.forgotPassword(email);
  }

  async function resetPassword(resetToken, newPassword) {
    return api.resetPassword(resetToken, newPassword);
  }

  const value = {
    user,
    accessToken,
    isAuthenticated: !!user,
    isAdmin: !!user?.is_admin,
    loading,
    login,
    signup,
    logout,
    forgotPassword,
    resetPassword,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}