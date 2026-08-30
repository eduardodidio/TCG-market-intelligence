import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useApi } from "../../src/hooks/useApi";
import type { ApiResponse } from "../../src/types/api";

function makeResponse<T>(data: T): ApiResponse<T> {
  return { data, errors: [], meta: {} as ApiResponse<T>["meta"] };
}

function makeFetcher<T>(data: T) {
  return vi.fn((_signal: AbortSignal) => Promise.resolve(makeResponse(data)));
}

describe("useApi refetchOnFocus", () => {
  let listeners: Map<string, EventListener>;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    listeners = new Map();
    vi.spyOn(document, "addEventListener").mockImplementation((type, handler) => {
      listeners.set(type, handler as EventListener);
    });
    vi.spyOn(document, "removeEventListener").mockImplementation((type) => {
      listeners.delete(type);
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  function fireVisibilityChange(state: DocumentVisibilityState) {
    Object.defineProperty(document, "visibilityState", {
      value: state,
      writable: true,
      configurable: true,
    });
    const handler = listeners.get("visibilitychange");
    if (handler) {
      handler(new Event("visibilitychange"));
    }
  }

  it("adds visibilitychange listener when refetchOnFocus=true", async () => {
    const fetcher = makeFetcher("hello");

    renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));

    // Wait for initial fetch to settle
    await act(async () => {
      await Promise.resolve();
    });

    expect(listeners.has("visibilitychange")).toBe(true);
  });

  it("does NOT add visibilitychange listener when refetchOnFocus is false (default)", async () => {
    const fetcher = makeFetcher("hello");

    renderHook(() => useApi(fetcher, []));

    await act(async () => {
      await Promise.resolve();
    });

    expect(listeners.has("visibilitychange")).toBe(false);
  });

  it("does NOT add visibilitychange listener when refetchOnFocus is explicitly false", async () => {
    const fetcher = makeFetcher("hello");

    renderHook(() => useApi(fetcher, [], { refetchOnFocus: false }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(listeners.has("visibilitychange")).toBe(false);
  });

  it("triggers refetch on visibilitychange to visible after debounce period", async () => {
    const fetcher = makeFetcher("data");

    renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));

    // Wait for initial fetch
    await act(async () => {
      await Promise.resolve();
    });

    // Initial fetch = 1 call
    expect(fetcher).toHaveBeenCalledTimes(1);

    // Advance time past the 30s debounce
    vi.advanceTimersByTime(31_000);

    // Simulate tab becoming visible
    await act(async () => {
      fireVisibilityChange("visible");
      await Promise.resolve();
    });

    // Should have refetched
    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("skips refetch if last fetch was less than 30s ago (debounce)", async () => {
    const fetcher = makeFetcher("data");

    renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));

    // Wait for initial fetch
    await act(async () => {
      await Promise.resolve();
    });

    expect(fetcher).toHaveBeenCalledTimes(1);

    // Only advance 5s (well within debounce window)
    vi.advanceTimersByTime(5_000);

    // Simulate tab becoming visible
    await act(async () => {
      fireVisibilityChange("visible");
      await Promise.resolve();
    });

    // Should NOT have refetched
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("does not refetch when visibility changes to hidden", async () => {
    const fetcher = makeFetcher("data");

    renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));

    await act(async () => {
      await Promise.resolve();
    });

    expect(fetcher).toHaveBeenCalledTimes(1);

    // Advance past debounce
    vi.advanceTimersByTime(31_000);

    // Simulate tab becoming hidden
    await act(async () => {
      fireVisibilityChange("hidden");
      await Promise.resolve();
    });

    // Should NOT have refetched
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("removes visibility listener on unmount", async () => {
    const fetcher = makeFetcher("data");

    const { unmount } = renderHook(() =>
      useApi(fetcher, [], { refetchOnFocus: true }),
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(listeners.has("visibilitychange")).toBe(true);

    unmount();

    expect(listeners.has("visibilitychange")).toBe(false);
  });

  it("updates lastFetchedAt on refetch so subsequent quick focus is debounced", async () => {
    const fetcher = makeFetcher("data");

    renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));

    await act(async () => {
      await Promise.resolve();
    });

    // Advance past debounce and trigger refetch
    vi.advanceTimersByTime(31_000);

    await act(async () => {
      fireVisibilityChange("visible");
      await Promise.resolve();
    });

    expect(fetcher).toHaveBeenCalledTimes(2);

    // Now only 5s later, try again — should be debounced
    vi.advanceTimersByTime(5_000);

    await act(async () => {
      fireVisibilityChange("visible");
      await Promise.resolve();
    });

    // Still 2 — debounced
    expect(fetcher).toHaveBeenCalledTimes(2);

    // After another 26s (total 31s from last fetch), should work
    vi.advanceTimersByTime(26_000);

    await act(async () => {
      fireVisibilityChange("visible");
      await Promise.resolve();
    });

    expect(fetcher).toHaveBeenCalledTimes(3);
  });
});
