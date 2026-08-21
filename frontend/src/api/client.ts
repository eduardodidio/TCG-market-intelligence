import type { ApiResponse } from "../types/api";
import { API_BASE_URL } from "../utils/constants";

const DEFAULT_TIMEOUT_MS = 10_000;

/**
 * Typed fetch wrapper that returns the standard API envelope.
 * Handles HTTP errors, network errors, and request timeouts.
 */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string>,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<ApiResponse<T>> {
  const url = new URL(path, API_BASE_URL || window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }

  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  // Compose signals: external signal + timeout
  const signal = options?.signal
    ? composeAbortSignals(options.signal, controller.signal)
    : controller.signal;

  try {
    const response = await fetch(url.toString(), {
      headers: { Accept: "application/json" },
      signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const errorBody = await response.json().catch(() => null);
      // If the backend returned a proper envelope with errors, use it
      if (errorBody && Array.isArray(errorBody.errors) && errorBody.errors.length > 0) {
        return errorBody as ApiResponse<T>;
      }
      // Otherwise build an envelope from the HTTP status
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
  } catch (err: unknown) {
    clearTimeout(timeoutId);

    const isAbort =
      err instanceof DOMException && err.name === "AbortError";
    const message = isAbort
      ? "Request timed out"
      : err instanceof Error
        ? err.message
        : "Unknown error";
    const code = isAbort ? "TIMEOUT" : "NETWORK_ERROR";

    return {
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code, message }],
    };
  }
}

/**
 * Typed POST wrapper that sends JSON and returns the standard API envelope.
 */
export async function apiPost<T>(
  path: string,
  body: unknown,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<ApiResponse<T>> {
  const url = new URL(path, API_BASE_URL || window.location.origin);

  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const signal = options?.signal
    ? composeAbortSignals(options.signal, controller.signal)
    : controller.signal;

  // Include auth token if available
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  const token = localStorage.getItem("tcg_access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url.toString(), {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      signal,
    });

    clearTimeout(timeoutId);

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
  } catch (err: unknown) {
    clearTimeout(timeoutId);

    const isAbort =
      err instanceof DOMException && err.name === "AbortError";
    const message = isAbort
      ? "Request timed out"
      : err instanceof Error
        ? err.message
        : "Unknown error";
    const code = isAbort ? "TIMEOUT" : "NETWORK_ERROR";

    return {
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code, message }],
    };
  }
}

/**
 * Typed DELETE wrapper.
 */
export async function apiDelete(
  path: string,
  options?: { signal?: AbortSignal; timeoutMs?: number },
): Promise<void> {
  const url = new URL(path, API_BASE_URL || window.location.origin);

  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const signal = options?.signal
    ? composeAbortSignals(options.signal, controller.signal)
    : controller.signal;

  const headers: Record<string, string> = {
    Accept: "application/json",
  };
  const token = localStorage.getItem("tcg_access_token");
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  try {
    const response = await fetch(url.toString(), {
      method: "DELETE",
      headers,
      signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok && response.status !== 204) {
      const errorBody = await response.json().catch(() => null);
      throw new Error(errorBody?.detail || response.statusText);
    }
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof Error) throw err;
    throw new Error("Unknown error");
  }
}

/**
 * Compose two AbortSignals — aborts when either fires.
 */
function composeAbortSignals(
  a: AbortSignal,
  b: AbortSignal,
): AbortSignal {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (a.aborted || b.aborted) {
    controller.abort();
    return controller.signal;
  }
  a.addEventListener("abort", abort, { once: true });
  b.addEventListener("abort", abort, { once: true });
  return controller.signal;
}
