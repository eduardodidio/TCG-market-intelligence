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
