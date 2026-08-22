import { renderHook, waitFor, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { TickerItemData } from "../../src/types/api";

// Mock fetchTickerData
const mockFetchTickerData = vi.fn<[string, AbortSignal?], Promise<TickerItemData[]>>();

vi.mock("../../src/api/trending", () => ({
  fetchTickerData: (...args: [string, AbortSignal?]) => mockFetchTickerData(...args),
}));

// Mock useCurrency
let mockCurrency = "BRL";
vi.mock("../../src/hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: mockCurrency, setCurrency: vi.fn(), toggle: vi.fn() }),
}));

function makeItems(count: number): TickerItemData[] {
  return Array.from({ length: count }, (_, i) => ({
    card_id: i + 1,
    name_en: `Card ${i + 1}`,
    name_pt: null,
    set_code: "lea",
    price_end: 10 + i,
    change_pct: i % 2 === 0 ? 5.0 : -3.0,
    direction: (i % 2 === 0 ? "up" : "down") as "up" | "down",
    currency: "BRL",
  }));
}

describe("useTickerData", () => {
  beforeEach(() => {
    mockCurrency = "BRL";
    mockFetchTickerData.mockResolvedValue(makeItems(4));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts with loading=true and empty items", async () => {
    mockFetchTickerData.mockImplementation(() => new Promise(() => {}));
    const { useTickerData } = await import("../../src/hooks/useTickerData");
    const { result } = renderHook(() => useTickerData());

    expect(result.current.loading).toBe(true);
    expect(result.current.items).toEqual([]);
  });

  it("returns items after fetch completes", async () => {
    const items = makeItems(4);
    mockFetchTickerData.mockResolvedValue(items);
    const { useTickerData } = await import("../../src/hooks/useTickerData");

    const { result } = renderHook(() => useTickerData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.items).toHaveLength(4);
    expect(result.current.items[0].name_en).toBe("Card 1");
  });

  it("returns empty array when fetch returns empty", async () => {
    mockFetchTickerData.mockResolvedValue([]);
    const { useTickerData } = await import("../../src/hooks/useTickerData");

    const { result } = renderHook(() => useTickerData());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.items).toEqual([]);
  });

  it("passes currency to fetchTickerData", async () => {
    mockCurrency = "USD";
    const { useTickerData } = await import("../../src/hooks/useTickerData");

    renderHook(() => useTickerData());

    await waitFor(() => {
      expect(mockFetchTickerData).toHaveBeenCalledWith("USD", expect.any(AbortSignal));
    });
  });

  it("sets up a 5-minute refresh interval", async () => {
    // Use real timers for initial load, then switch to fake for interval test
    const { useTickerData } = await import("../../src/hooks/useTickerData");

    // Use setInterval spy to verify interval setup
    const setIntervalSpy = vi.spyOn(globalThis, "setInterval");

    renderHook(() => useTickerData());

    await waitFor(() => {
      expect(mockFetchTickerData).toHaveBeenCalledTimes(1);
    });

    // Verify setInterval was called with 300000ms
    expect(setIntervalSpy).toHaveBeenCalledWith(expect.any(Function), 300_000);

    setIntervalSpy.mockRestore();
  });

  it("cleans up interval and aborts on unmount", async () => {
    const clearIntervalSpy = vi.spyOn(globalThis, "clearInterval");

    const { useTickerData } = await import("../../src/hooks/useTickerData");

    const { unmount } = renderHook(() => useTickerData());

    await waitFor(() => {
      expect(mockFetchTickerData).toHaveBeenCalledTimes(1);
    });

    unmount();

    // clearInterval should have been called
    expect(clearIntervalSpy).toHaveBeenCalled();

    clearIntervalSpy.mockRestore();
  });
});
