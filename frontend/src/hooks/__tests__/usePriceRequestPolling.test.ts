import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePriceRequestPolling } from "../usePriceRequestPolling";

// Mock fetchPriceRequestStatus
const mockFetch = vi.fn();
vi.mock("../../api/cards", () => ({
  fetchPriceRequestStatus: (...args: unknown[]) => mockFetch(...args),
}));

describe("usePriceRequestPolling", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("does not poll when disabled", () => {
    renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: false,
      }),
    );

    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("polls on enable and calls API", async () => {
    mockFetch.mockResolvedValue({
      data: { status: "pending" },
    });

    const { result } = renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        intervalMs: 5000,
      }),
    );

    // Initial poll is called immediately
    expect(result.current.isPolling).toBe(true);

    // Flush the initial poll promise
    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(mockFetch).toHaveBeenCalledWith(42);
  });

  it("stops polling on completed and calls onCompleted", async () => {
    const onCompleted = vi.fn();

    mockFetch.mockResolvedValue({
      data: { status: "completed", result_price: 12.5 },
    });

    const { result } = renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        onCompleted,
        intervalMs: 5000,
      }),
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(onCompleted).toHaveBeenCalledWith(12.5);
    expect(result.current.isPolling).toBe(false);
    expect(result.current.status).toBe("completed");
    expect(result.current.resultPrice).toBe(12.5);
  });

  it("stops polling on failed and calls onFailed", async () => {
    const onFailed = vi.fn();

    mockFetch.mockResolvedValue({
      data: { status: "failed" },
    });

    const { result } = renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        onFailed,
        intervalMs: 5000,
      }),
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(onFailed).toHaveBeenCalled();
    expect(result.current.isPolling).toBe(false);
    expect(result.current.status).toBe("failed");
  });

  it("stops polling on 'none' status", async () => {
    mockFetch.mockResolvedValue({
      data: { status: "none" },
    });

    const { result } = renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        intervalMs: 5000,
      }),
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(result.current.isPolling).toBe(false);
  });

  it("stops polling after max duration timeout", async () => {
    mockFetch.mockResolvedValue({
      data: { status: "pending" },
    });

    const { result } = renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        intervalMs: 5000,
        maxDurationMs: 15000,
      }),
    );

    // Advance past the max duration
    await act(async () => {
      vi.advanceTimersByTime(16000);
      await vi.runAllTimersAsync();
    });

    expect(result.current.isPolling).toBe(false);
  });

  it("cleans up interval on unmount", async () => {
    mockFetch.mockResolvedValue({
      data: { status: "pending" },
    });

    const { unmount } = renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        intervalMs: 5000,
      }),
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    const callCountBefore = mockFetch.mock.calls.length;
    unmount();

    // Advance timers — no more calls after unmount
    await act(async () => {
      vi.advanceTimersByTime(10000);
    });

    expect(mockFetch.mock.calls.length).toBe(callCountBefore);
  });

  it("handles null result_price in completed status", async () => {
    const onCompleted = vi.fn();

    mockFetch.mockResolvedValue({
      data: { status: "completed", result_price: null },
    });

    renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        onCompleted,
        intervalMs: 5000,
      }),
    );

    await act(async () => {
      await vi.runAllTimersAsync();
    });

    expect(onCompleted).toHaveBeenCalledWith(null);
  });

  it("continues polling on network error", async () => {
    mockFetch
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValue({ data: { status: "completed", result_price: 5.0 } });

    const onCompleted = vi.fn();

    renderHook(() =>
      usePriceRequestPolling({
        cardId: 42,
        enabled: true,
        onCompleted,
        intervalMs: 5000,
      }),
    );

    // First poll: error (continues)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(100);
    });

    expect(onCompleted).not.toHaveBeenCalled();

    // Second poll: success
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(onCompleted).toHaveBeenCalledWith(5.0);
  });
});
