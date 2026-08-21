import type { ScanListResponse, ScanRequest, ScanRun, ScanTriggerResponse } from "../types/api";
import { API_BASE_URL } from "../utils/constants";

const DEFAULT_TIMEOUT_MS = 15_000;

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...init,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...init?.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.detail || response.statusText);
    }

    return (await response.json()) as T;
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Request timed out");
    }
    throw err;
  }
}

function buildUrl(path: string, params?: Record<string, string>): string {
  const url = new URL(path, API_BASE_URL || window.location.origin);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== "") {
        url.searchParams.set(key, value);
      }
    }
  }
  return url.toString();
}

export function fetchScans(
  params?: Record<string, string>,
): Promise<ScanListResponse> {
  return fetchJson<ScanListResponse>(buildUrl("/api/v1/scans", params));
}

export function fetchScanDetail(id: number): Promise<ScanRun> {
  return fetchJson<ScanRun>(buildUrl(`/api/v1/scans/${id}`));
}

export function triggerScan(body: ScanRequest): Promise<ScanTriggerResponse> {
  return fetchJson<ScanTriggerResponse>(buildUrl("/api/v1/scans"), {
    method: "POST",
    body: JSON.stringify(body),
  });
}
