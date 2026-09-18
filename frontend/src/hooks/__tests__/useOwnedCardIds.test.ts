import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useOwnedCardIds } from "../useOwnedCardIds";

// Mock useAuth
const mockIsAuthenticated = vi.fn(() => true);
vi.mock("../useAuth", () => ({
  useAuth: () => ({ isAuthenticated: mockIsAuthenticated() }),
}));

// Mock fetchCollection
const mockFetchCollection = vi.fn();
vi.mock("../../api/collection", () => ({
  fetchCollection: (...args: unknown[]) => mockFetchCollection(...args),
}));

describe("useOwnedCardIds", () => {
  let dateNowSpy: ReturnType<typeof vi.spyOn>;
  let currentTime: number;

  beforeEach(() => {
    currentTime = 1000;
    dateNowSpy = vi.spyOn(Date, "now").mockImplementation(() => currentTime);
    vi.clearAllMocks();
    mockIsAuthenticated.mockReturnValue(true);
    mockFetchCollection.mockResolvedValue({
      data: [{ card_id: 1 }, { card_id: 2 }, { card_id: 3 }],
      errors: [],
    });
  });

  afterEach(() => {
    dateNowSpy.mockRestore();
  });

  it("fetches collection on mount for authenticated users", async () => {
    let result: ReturnType<typeof renderHook<Set<number>, unknown>>;
    await act(async () => {
      result = renderHook(() => useOwnedCardIds());
    });

    expect(result!.result.current.size).toBe(3);
    expect(mockFetchCollection).toHaveBeenCalledTimes(1);
  });

  it("returns empty set for unauthenticated users", async () => {
    mockIsAuthenticated.mockReturnValue(false);

    let result: ReturnType<typeof renderHook<Set<number>, unknown>>;
    await act(async () => {
      result = renderHook(() => useOwnedCardIds());
    });

    expect(result!.result.current.size).toBe(0);
  });

  it("does NOT refetch on visibility change within 120s debounce", async () => {
    await act(async () => {
      renderHook(() => useOwnedCardIds());
    });
    expect(mockFetchCollection).toHaveBeenCalledTimes(1);

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

    expect(mockFetchCollection).toHaveBeenCalledTimes(1);
  });

  it("refetches on visibility change after 120s elapsed", async () => {
    await act(async () => {
      renderHook(() => useOwnedCardIds());
    });
    expect(mockFetchCollection).toHaveBeenCalledTimes(1);

    // Advance past the 120s debounce
    currentTime = 122_000;
    Object.defineProperty(document, "visibilityState", {
      value: "visible",
      writable: true,
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(mockFetchCollection).toHaveBeenCalledTimes(2);
  });

  it("does NOT refetch when tab becomes hidden", async () => {
    await act(async () => {
      renderHook(() => useOwnedCardIds());
    });
    expect(mockFetchCollection).toHaveBeenCalledTimes(1);

    currentTime = 200_000;
    Object.defineProperty(document, "visibilityState", {
      value: "hidden",
      writable: true,
      configurable: true,
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
    });

    expect(mockFetchCollection).toHaveBeenCalledTimes(1);
  });
});
