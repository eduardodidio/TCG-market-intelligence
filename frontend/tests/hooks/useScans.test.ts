import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useScans, useTriggerScan } from "../../src/hooks/useScans";
import type { ScanListResponse, ScanTriggerResponse } from "../../src/types/api";
import { makeScanRun } from "../fixtures/scan-responses";

describe("useScans", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("returns scan list data on success", async () => {
    const mockResponse: ScanListResponse = {
      scans: [makeScanRun({ id: 1 }), makeScanRun({ id: 2 })],
      total: 2,
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useScans());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.scans).toHaveLength(2);
    expect(result.current.total).toBe(2);
    expect(result.current.error).toBeNull();
    expect(result.current.scans[0].id).toBe(1);
  });

  it("returns error on fetch failure", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({ detail: "Server error" }),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useScans());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe("Server error");
    expect(result.current.scans).toHaveLength(0);
  });
});

describe("useTriggerScan", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("sends POST request and returns response", async () => {
    const mockResponse: ScanTriggerResponse = { scan_id: 42, status: "pending" };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useTriggerScan());

    const response = await result.current.trigger({ scan_type: "collection" });

    expect(response.scan_id).toBe(42);
    expect(response.status).toBe("pending");

    // Verify POST was called with correct body
    const fetchCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    const requestInit = fetchCall[1] as RequestInit;
    expect(requestInit.method).toBe("POST");
    expect(JSON.parse(requestInit.body as string)).toEqual({ scan_type: "collection" });
  });
});
