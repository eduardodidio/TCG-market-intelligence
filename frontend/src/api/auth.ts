import type { ApiResponse } from "../types/api";
import { API_BASE_URL } from "../utils/constants";

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserProfile {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  auth_provider: string;
  preferred_language: string | null;
  is_active: boolean;
}

const TOKEN_KEY = "tcg_access_token";
const REFRESH_KEY = "tcg_refresh_token";

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function storeTokens(tokens: AuthTokens): void {
  localStorage.setItem(TOKEN_KEY, tokens.access_token);
  localStorage.setItem(REFRESH_KEY, tokens.refresh_token);
}

export function clearTokens(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
}

async function authFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResponse<T>> {
  const url = new URL(path, API_BASE_URL || window.location.origin);

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(options.headers as Record<string, string> || {}),
  };

  const token = getStoredToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(url.toString(), {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null);
    if (errorBody && Array.isArray(errorBody.errors) && errorBody.errors.length > 0) {
      return errorBody as ApiResponse<T>;
    }
    return {
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [
        {
          code: `HTTP_${response.status}`,
          message: errorBody?.detail || response.statusText,
        },
      ],
    };
  }

  return (await response.json()) as ApiResponse<T>;
}

export async function login(
  email: string,
  password: string,
): Promise<ApiResponse<AuthTokens>> {
  const resp = await authFetch<AuthTokens>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  if (resp.data) {
    storeTokens(resp.data);
  }
  return resp;
}

export async function register(
  email: string,
  password: string,
  displayName?: string,
): Promise<ApiResponse<AuthTokens>> {
  const resp = await authFetch<AuthTokens>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      display_name: displayName || null,
    }),
  });
  if (resp.data) {
    storeTokens(resp.data);
  }
  return resp;
}

export async function refreshTokens(): Promise<ApiResponse<AuthTokens>> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) {
    return {
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code: "NO_REFRESH_TOKEN", message: "No refresh token" }],
    };
  }
  const resp = await authFetch<AuthTokens>("/api/v1/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (resp.data) {
    storeTokens(resp.data);
  }
  return resp;
}

export async function fetchMe(): Promise<ApiResponse<UserProfile>> {
  return authFetch<UserProfile>("/api/v1/auth/me");
}

export async function logout(): Promise<void> {
  try {
    await authFetch("/api/v1/auth/logout", { method: "POST" });
  } finally {
    clearTokens();
  }
}
