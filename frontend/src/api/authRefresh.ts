/**
 * Silent token refresh utility (non-React, pure functions).
 *
 * When a 401 is received, tryRefreshToken() attempts to exchange the
 * stored refresh token for a new access token. Concurrent calls are
 * deduplicated so only one refresh request runs at a time.
 */

import { API_BASE_URL } from "../utils/constants";

const TOKEN_KEY = "tcg_access_token";
const REFRESH_KEY = "tcg_refresh_token";

/** In-flight refresh promise for deduplication. */
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 *
 * - Returns `true` if new tokens were stored successfully.
 * - Returns `false` if the refresh failed (no refresh token, server
 *   rejected it, network error, etc.).
 * - Concurrent callers receive the same promise (deduplication).
 */
export async function tryRefreshToken(): Promise<boolean> {
  // Deduplicate: if a refresh is already in flight, piggy-back on it.
  if (refreshPromise) {
    return refreshPromise;
  }

  refreshPromise = performRefresh();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function performRefresh(): Promise<boolean> {
  const refreshToken = localStorage.getItem(REFRESH_KEY);
  if (!refreshToken) {
    return false;
  }

  try {
    const url = new URL(
      "/api/v1/auth/refresh",
      API_BASE_URL || window.location.origin,
    );

    const response = await fetch(url.toString(), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return false;
    }

    const body = await response.json();
    const data = body?.data ?? body;

    if (data?.access_token && data?.refresh_token) {
      localStorage.setItem(TOKEN_KEY, data.access_token);
      localStorage.setItem(REFRESH_KEY, data.refresh_token);
      return true;
    }

    return false;
  } catch {
    return false;
  }
}

/**
 * Clear stored tokens and redirect to the login page.
 * Skips redirect when already on /login to avoid loops.
 */
export function forceLogout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  if (window.location.pathname !== "/login") {
    const returnTo = encodeURIComponent(window.location.pathname);
    window.location.href = `/login?returnTo=${returnTo}&expired=1`;
  }
}

/** Exposed for testing — reset internal deduplication state. */
export function _resetForTest(): void {
  refreshPromise = null;
}
