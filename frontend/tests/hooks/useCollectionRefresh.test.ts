import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

// Mock the scans API
vi.mock("../../src/api/scans", () => ({
  triggerScanAuth: vi.fn(),
  getScanStatusAuth: vi.fn(),
}));

// Mock constants
vi.mock("../../src/utils/constants", () => ({
  API_BASE_URL: "http://localhost:8000",
  DEFAULT_PAGE_LIMIT: 24,
  GRID_SIZE_CONFIG: {},
}));

// We need a mock EventSource that the useScanStream hook will use
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

  emit(type: string, data: unknown) {
    const event = new MessageEvent(type, { data: JSON.stringify(data) });
    for (const handler of this.listeners[type] || []) {
      handler(event);
    }
  }
}

describe("useCollectionRefresh", () => {
  beforeEach(() => {
    MockEventSource.instances = [];
    (globalThis as Record<string, unknown>).EventSource = MockEventSource as unknown as typeof EventSource;
    vi.useFakeTimers({ shouldAdvanceTime: true });
    // Set up localStorage with a fake token
    vi.spyOn(Storage.prototype, "getItem").mockImplementation((key: string) => {
      if (key === "tcg_access_token") return "fake-jwt-token";
      return null;
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
    delete (globalThis as Record<string, unknown>).EventSource;
  });

  it("starts with default state", async () => {
    const { useCollectionRefresh } = await import("../../src/hooks/useCollectionRefresh");
    const { result } = renderHook(() => useCollectionRefresh());

    expect(result.current.isRefreshing).toBe(false);
    expect(result.current.progress).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.isDone).toBe(false);
    expect(result.current.lastScannedCard).toBeNull();
  });

  it("triggers scan and connects SSE", async () => {
    const { triggerScanAuth } = await import("../../src/api/scans");
    const mockTrigger = vi.mocked(triggerScanAuth);
    mockTrigger.mockResolvedValue({
      data: { scan_id: 42, status: "pending" },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { useCollectionRefresh } = await import("../../src/hooks/useCollectionRefresh");
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh();
    });

    expect(mockTrigger).toHaveBeenCalledWith({ scan_type: "collection", provider: "liga" });
    expect(result.current.isRefreshing).toBe(true);
    // EventSource should have been created
    expect(MockEventSource.instances.length).toBeGreaterThanOrEqual(1);
  });

  it("updates progress and lastScannedCard from SSE events", async () => {
    const { triggerScanAuth } = await import("../../src/api/scans");
    vi.mocked(triggerScanAuth).mockResolvedValue({
      data: { scan_id: 1, status: "pending" },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { useCollectionRefresh } = await import("../../src/hooks/useCollectionRefresh");
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh();
    });

    // Find the EventSource and emit a card_scanned event
    const es = MockEventSource.instances[MockEventSource.instances.length - 1];

    await act(async () => {
      es.emit("card_scanned", {
        event_type: "card_scanned",
        scan_id: 1,
        timestamp: "2026-08-21T10:00:00",
        external_id: "1001",
        card_name: "Lightning Bolt",
        price_found: true,
        price: 12.5,
        cards_processed: 1,
        cards_total: 10,
        cards_failed: 0,
        observations_saved: 1,
      });
    });

    expect(result.current.progress).toEqual({ processed: 1, total: 10 });
    expect(result.current.lastScannedCard).toEqual({
      name: "Lightning Bolt",
      externalId: "1001",
      priceFound: true,
      price: 12.5,
    });
  });

  it("sets isDone on scan_complete", async () => {
    const onComplete = vi.fn();
    const { triggerScanAuth } = await import("../../src/api/scans");
    vi.mocked(triggerScanAuth).mockResolvedValue({
      data: { scan_id: 1, status: "pending" },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { useCollectionRefresh } = await import("../../src/hooks/useCollectionRefresh");
    const { result } = renderHook(() => useCollectionRefresh(onComplete));

    await act(async () => {
      await result.current.startRefresh();
    });

    const es = MockEventSource.instances[MockEventSource.instances.length - 1];

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

    expect(result.current.isDone).toBe(true);
    expect(result.current.isRefreshing).toBe(false);
    expect(onComplete).toHaveBeenCalled();
  });

  it("cancelRefresh disconnects SSE", async () => {
    const { triggerScanAuth } = await import("../../src/api/scans");
    vi.mocked(triggerScanAuth).mockResolvedValue({
      data: { scan_id: 1, status: "pending" },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    const { useCollectionRefresh } = await import("../../src/hooks/useCollectionRefresh");
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh();
    });

    act(() => {
      result.current.cancelRefresh();
    });

    expect(result.current.isRefreshing).toBe(false);
    expect(result.current.progress).toBeNull();
    expect(result.current.lastScannedCard).toBeNull();
  });

  it("sets error when triggerScan fails", async () => {
    const { triggerScanAuth } = await import("../../src/api/scans");
    vi.mocked(triggerScanAuth).mockResolvedValue({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code: "HTTP_500", message: "Server error" }],
    });

    const { useCollectionRefresh } = await import("../../src/hooks/useCollectionRefresh");
    const { result } = renderHook(() => useCollectionRefresh());

    await act(async () => {
      await result.current.startRefresh();
    });

    expect(result.current.error).toBe("Server error");
    expect(result.current.isRefreshing).toBe(false);
  });

  it("exposes public API contract (no breaking changes)", async () => {
    const { useCollectionRefresh } = await import("../../src/hooks/useCollectionRefresh");
    const { result } = renderHook(() => useCollectionRefresh());

    // All original fields must be present
    expect(result.current).toHaveProperty("isRefreshing");
    expect(result.current).toHaveProperty("progress");
    expect(result.current).toHaveProperty("error");
    expect(result.current).toHaveProperty("isDone");
    expect(result.current).toHaveProperty("startRefresh");
    expect(result.current).toHaveProperty("cancelRefresh");
    // New field
    expect(result.current).toHaveProperty("lastScannedCard");
  });
});
