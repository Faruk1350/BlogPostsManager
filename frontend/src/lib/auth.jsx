import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import {
  api,
  clearTokens,
  getStoredTheme,
  loginRequest,
  logoutRequest,
  restoreSession,
  signupRequest,
  storeTheme,
} from "./api";

const AuthContext = createContext(null);

function applyTheme(theme) {
  const resolved =
    theme === "system"
      ? window.matchMedia("(prefers-color-scheme: dark)").matches
        ? "dark"
        : "light"
      : theme;
  document.documentElement.dataset.theme = resolved;
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [preferences, setPreferences] = useState(null);
  const [ready, setReady] = useState(false);

  const applySession = useCallback((data) => {
    setUser(data.user || null);
    setProfile(data.profile || null);
    if (data.preferences) {
      setPreferences(data.preferences);
      storeTheme(data.preferences.theme || "system");
      applyTheme(data.preferences.theme || "system");
    }
  }, []);

  // Restore session on first load.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      applyTheme(getStoredTheme());
      const restored = await restoreSession();
      if (restored && !cancelled) {
        try {
          const me = await api("/api/auth/me");
          applySession(me);
        } catch {
          clearTokens();
        }
      }
      if (!cancelled) setReady(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [applySession]);

  const login = useCallback(
    async (email, password) => {
      const data = await loginRequest(email, password);
      const me = await api("/api/auth/me");
      applySession({ ...me, user: data.user, profile: data.profile });
      return data;
    },
    [applySession]
  );

  const signup = useCallback(
    async (email, password, displayName) => {
      const data = await signupRequest(email, password, displayName);
      const me = await api("/api/auth/me");
      applySession({ ...me, user: data.user, profile: data.profile });
      return data;
    },
    [applySession]
  );

  const logout = useCallback(async () => {
    await logoutRequest();
    setUser(null);
    setProfile(null);
    setPreferences(null);
  }, []);

  const updateProfile = useCallback(async (updates) => {
    const updated = await api("/api/me", { method: "PUT", body: updates });
    setProfile(updated);
    return updated;
  }, []);

  const updatePreferences = useCallback(async (updates) => {
    const updated = await api("/api/me/preferences", { method: "PUT", body: updates });
    setPreferences(updated);
    storeTheme(updated.theme);
    applyTheme(updated.theme);
    return updated;
  }, []);

  const changePassword = useCallback(
    (currentPassword, newPassword) =>
      api("/api/auth/password", {
        method: "PUT",
        body: { current_password: currentPassword, new_password: newPassword },
      }),
    []
  );

  const reload = useCallback(async () => {
    const me = await api("/api/auth/me");
    applySession(me);
    return me;
  }, [applySession]);

  const value = useMemo(
    () => ({
      ready,
      user,
      profile,
      preferences,
      isAuthenticated: Boolean(user && profile),
      isAdmin: Boolean(user?.is_admin),
      login,
      signup,
      logout,
      updateProfile,
      updatePreferences,
      changePassword,
      reload,
    }),
    [ready, user, profile, preferences, login, signup, logout, updateProfile, updatePreferences, changePassword, reload]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
