import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useScanStream } from "../../src/hooks/useScanStream";
import type { ScanStreamEvent } from "../../src/hooks/useScanStream";

// Mock EventSource
class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onerror: (() => void) | null = null;
  listeners: Record<string, ((e: MessageEvent) => void)[]> = {};
  closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
    // Auto-fire onopen after a tick
    setTimeout(() => this.onopen?.(), 0);
  }

  addEventListener(type: string, handler: (e: MessageEvent) => void) {
    this.listeners[type] = this.listeners[type] || [];
    this.listeners[type].push(handler);
  }

  removeEventListener() {}

  close() {
    this.closed = true;
  }

  // Test helper: emit an SSE event
  emit(type: string, data: unknown) {
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    for (const handler of this.listeners[type] || []) {
      handler(event);
    }
  }

  // Test helper: trigger error
  triggerError() {
    this.onerror?.();
  }
}

// Mock scans API
vi.mock("../../src/api/scans", () => ({
  getScanStatusAuth: vi.fn(),
}));

// Mock constants
vi.mock("../../src/utils/constants", () => ({
  API_BASE_URL: "http://localhost:8000",
}));

describe("useScanStream", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    (globalThis as Record<string, unknown>).EventSource = MockEventSource as unknown as typeof EventSource;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    delete (globalThis as Record<string, unknown>).EventSource;
  });

  it("does not connect when scanId is null", () => {
    renderHook(() =>
      useScanStream({ scanId: null, token: "jwt" }),
    );
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("connects to SSE endpoint with token", () => {
    renderHook(() =>
      useScanStream({ scanId: 42, token: "mytoken" }),
    );
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain("/api/v1/scans/42/stream");
    expect(MockEventSource.instances[0].url).toContain("token=mytoken");
  });

  it("parses events and calls onEvent", async () => {
    const onEvent = vi.fn();
    renderHook(() =>
      useScanStream({ scanId: 1, token: "jwt", onEvent }),
    );

    const es = MockEventSource.instances[0];

    const event: ScanStreamEvent = {
      event_type: "card_scanned",
      scan_id: 1,
      timestamp: "2026-08-21T10:00:00",
      card_name: "Lightning Bolt",
      price_found: true,
      cards_processed: 1,
      cards_total: 10,
      cards_failed: 0,
      observations_saved: 1,
    };

    await act(async () => {
      es.emit("card_scanned", event);
    });

    expect(onEvent).toHaveBeenCalledWith(expect.objectContaining({
      event_type: "card_scanned",
      card_name: "Lightning Bolt",
    }));
  });

  it("updates progress on card_scanned events", async () => {
    const { result } = renderHook(() =>
      useScanStream({ scanId: 1, token: "jwt" }),
    );

    const es = MockEventSource.instances[0];

    await act(async () => {
      es.emit("card_scanned", {
        event_type: "card_scanned",
        scan_id: 1,
        timestamp: "2026-08-21T10:00:00",
        cards_processed: 5,
        cards_total: 10,
        cards_failed: 0,
        observations_saved: 5,
      });
    });

    expect(result.current.progress).toEqual({ processed: 5, total: 10 });
    expect(result.current.lastEvent?.cards_processed).toBe(5);
  });

  it("calls onComplete and closes on scan_complete", async () => {
    const onComplete = vi.fn();
    renderHook(() =>
      useScanStream({ scanId: 1, token: "jwt", onComplete }),
    );

    const es = MockEventSource.instances[0];

    await act(async () => {
      es.emit("scan_complete", {
        event_type: "scan_complete",
        scan_id: 1,
        timestamp: "2026-08-21T10:01:00",
        cards_processed: 10,
        cards_total: 10,
        cards_failed: 0,
        observations_saved: 8,
      });
    });

    expect(onComplete).toHaveBeenCalled();
    expect(es.closed).toBe(true);
  });

  it("closes EventSource on disconnect()", async () => {
    const { result } = renderHook(() =>
      useScanStream({ scanId: 1, token: "jwt" }),
    );

    const es = MockEventSource.instances[0];

    act(() => {
      result.current.disconnect();
    });

    expect(es.closed).toBe(true);
    expect(result.current.isConnected).toBe(false);
  });

  it("closes EventSource on unmount", () => {
    const { unmount } = renderHook(() =>
      useScanStream({ scanId: 1, token: "jwt" }),
    );

    const es = MockEventSource.instances[0];
    unmount();
    expect(es.closed).toBe(true);
  });

  it("falls back to polling on EventSource error when fallbackToPolling is true", async () => {
    const { getScanStatusAuth } = await import("../../src/api/scans");
    const mockGetStatus = vi.mocked(getScanStatusAuth);
    mockGetStatus.mockResolvedValue({
      data: {
        id: 1,
        scan_type: "collection",
        filters_json: "{}",
        status: "completed",
        cards_total: 10,
        cards_processed: 10,
        cards_failed: 0,
        observations_saved: 8,
        error_summary: null,
        started_at: null,
        finished_at: null,
        created_at: "",
      },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    renderHook(() =>
      useScanStream({
        scanId: 1,
        token: "jwt",
        fallbackToPolling: true,
      }),
    );

    const es = MockEventSource.instances[0];

    await act(async () => {
      es.triggerError();
    });

    // Should have started polling (will call getScanStatusAuth on interval)
    expect(es.closed).toBe(true);
  });

  it("sets error when fallbackToPolling is false and SSE fails", async () => {
    const onError = vi.fn();
    const { result } = renderHook(() =>
      useScanStream({
        scanId: 1,
        token: "jwt",
        fallbackToPolling: false,
        onError,
      }),
    );

    const es = MockEventSource.instances[0];

    act(() => {
      es.triggerError();
    });

    await waitFor(() => {
      expect(onError).toHaveBeenCalledWith("SSE connection failed");
    });
    expect(result.current.error).toBe("SSE connection failed");
  });
});
