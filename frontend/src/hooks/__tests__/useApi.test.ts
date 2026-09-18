import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useApi } from "../useApi";
import type { ApiResponse } from "../../types/api";

function makeResponse<T>(data: T): ApiResponse<T> {
  return { data, errors: [], meta: { total: 1 } } as ApiResponse<T>;
}

describe("useApi", () => {
  let dateNowSpy: ReturnType<typeof vi.spyOn>;
  let currentTime: number;

  beforeEach(() => {
    currentTime = 1000;
    dateNowSpy = vi.spyOn(Date, "now").mockImplementation(() => currentTime);
  });

  afterEach(() => {
    dateNowSpy.mockRestore();
  });

  it("fetches data on mount", async () => {
    const fetcher = vi.fn().mockResolvedValue(makeResponse("hello"));

    let result: ReturnType<typeof renderHook<ReturnType<typeof useApi<string>>, unknown>>;
    await act(async () => {
      result = renderHook(() => useApi(fetcher));
    });

    expect(result!.result.current.data).toBe("hello");
    expect(result!.result.current.loading).toBe(false);
    expect(result!.result.current.error).toBeNull();
  });

  it("does not refetch on visibility change when refetchOnFocus is false", async () => {
    const fetcher = vi.fn().mockResolvedValue(makeResponse("data"));

    await act(async () => {
      renderHook(() => useApi(fetcher));
    });
    expect(fetcher).toHaveBeenCalledTimes(1);

    // Simulate tab focus after debounce period
    currentTime = 200_000;
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("refetches on visibility change when refetchOnFocus is true and 120s elapsed", async () => {
    const fetcher = vi.fn().mockResolvedValue(makeResponse("data"));

    await act(async () => {
      renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));
    });
    expect(fetcher).toHaveBeenCalledTimes(1);

    // Advance past the 120s debounce
    currentTime = 121_001;
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(fetcher).toHaveBeenCalledTimes(2);
  });

  it("does NOT refetch on visibility change within 120s debounce window", async () => {
    const fetcher = vi.fn().mockResolvedValue(makeResponse("data"));

    await act(async () => {
      renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));
    });
    expect(fetcher).toHaveBeenCalledTimes(1);

    // Only 60s elapsed — within debounce
    currentTime = 61_000;
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("does not refetch when tab is hidden", async () => {
    const fetcher = vi.fn().mockResolvedValue(makeResponse("data"));

    await act(async () => {
      renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));
    });
    expect(fetcher).toHaveBeenCalledTimes(1);

    currentTime = 200_000;
    Object.defineProperty(document, "visibilityState", {
      value: "hidden",
      writable: true,
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("debounce threshold is 120s — refetch at 119s blocked, at 121s allowed", async () => {
    const fetcher = vi.fn().mockResolvedValue(makeResponse("data"));

    await act(async () => {
      renderHook(() => useApi(fetcher, [], { refetchOnFocus: true }));
    });
    expect(fetcher).toHaveBeenCalledTimes(1);

    // At 119s — should NOT refetch
    currentTime = 120_000;
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(fetcher).toHaveBeenCalledTimes(1);

    // At 121s — should refetch
    currentTime = 122_000;
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });
    expect(fetcher).toHaveBeenCalledTimes(2);
  });
});
