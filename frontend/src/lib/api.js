/**
 * API client with automatic access-token handling and refresh.
 *
 * - Access token kept in memory, refresh token in localStorage.
 * - On 401 the client refreshes once, then retries the original request.
 */

const REFRESH_KEY = "chronicle.refresh_token";
const THEME_KEY = "chronicle.theme";

let accessToken = null;
let refreshPromise = null;

export class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

export function setTokens({ access_token, refresh_token } = {}) {
  if (access_token !== undefined) accessToken = access_token || null;
  if (refresh_token) localStorage.setItem(REFRESH_KEY, refresh_token);
}

export function clearTokens() {
  accessToken = null;
  localStorage.removeItem(REFRESH_KEY);
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_KEY);
}

export function getStoredTheme() {
  return localStorage.getItem(THEME_KEY) || "system";
}

export function storeTheme(theme) {
  localStorage.setItem(THEME_KEY, theme);
}

async function parse(response) {
  const text = await response.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function refreshAccessToken() {
  const refresh_token = getRefreshToken();
  if (!refresh_token) throw new ApiError(401, "No refresh token");

  if (!refreshPromise) {
    refreshPromise = fetch("/api/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token }),
    })
      .then(async (res) => {
        if (!res.ok) {
          clearTokens();
          throw new ApiError(401, "Session expired");
        }
        const data = await res.json();
        setTokens({ access_token: data.access_token, refresh_token: data.refresh_token });
        return data;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }
  return refreshPromise;
}

/**
 * Perform an API request.
 * @param {string} path
 * @param {{method?: string, body?: any, formData?: FormData, retry?: boolean}} options
 */
export async function api(path, options = {}) {
  const { method = "GET", body, formData, retry = true } = options;

  const headers = {};
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
  let payload;
  if (formData) {
    payload = formData;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  const response = await fetch(path, { method, headers, body: payload });

  if (response.status === 401 && retry && getRefreshToken()) {
    try {
      await refreshAccessToken();
    } catch {
      clearTokens();
      throw new ApiError(401, "Session expired");
    }
    return api(path, { ...options, retry: false });
  }

  const data = await parse(response);
  if (!response.ok) {
    const detail = data && (data.detail || data.message || data.error);
    throw new ApiError(response.status, detail || `Request failed (${response.status})`);
  }
  return data;
}

/** Attempt to restore a session from the stored refresh token. */
export async function restoreSession() {
  if (!getRefreshToken()) return false;
  try {
    await refreshAccessToken();
    return true;
  } catch {
    return false;
  }
}

export async function loginRequest(email, password) {
  const data = await api("/api/auth/login", {
    method: "POST",
    body: { email, password },
    retry: false,
  });
  setTokens({ access_token: data.access_token, refresh_token: data.refresh_token });
  return data;
}

export async function signupRequest(email, password, displayName) {
  const data = await api("/api/auth/signup", {
    method: "POST",
    body: { email, password, display_name: displayName || undefined },
    retry: false,
  });
  setTokens({ access_token: data.access_token, refresh_token: data.refresh_token });
  return data;
}

export async function logoutRequest() {
  const refresh_token = getRefreshToken();
  try {
    if (refresh_token) {
      await api("/api/auth/logout", { method: "POST", body: { refresh_token }, retry: false });
    }
  } catch {
    // revoking is best-effort; local session is cleared regardless
  } finally {
    clearTokens();
  }
}
