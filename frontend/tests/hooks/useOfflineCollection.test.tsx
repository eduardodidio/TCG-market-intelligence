import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";

// Mock idb-keyval
const mockStore = new Map<string, unknown>();
vi.mock("idb-keyval", () => ({
  get: vi.fn((key: string) => Promise.resolve(mockStore.get(key))),
  set: vi.fn((key: string, val: unknown) => {
    mockStore.set(key, val);
    return Promise.resolve();
  }),
}));

// Mock fetchCollection
const mockFetchCollection = vi.fn();
vi.mock("../../src/api/collection", () => ({
  fetchCollection: (...args: unknown[]) => mockFetchCollection(...args),
}));

import { useOfflineCollection } from "../../src/hooks/useOfflineCollection";

describe("useOfflineCollection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockStore.clear();
  });

  it("fetches collection from API and caches to IndexedDB", async () => {
    const cards = [{ id: 1, name: "Lightning Bolt" }];
    mockFetchCollection.mockResolvedValue({ data: cards });

    const { result } = renderHook(() => useOfflineCollection());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(cards);
    expect(result.current.isOffline).toBe(false);
    expect(result.current.lastSyncedAt).toBeTruthy();
    expect(mockStore.get("tcg_offline_collection")).toEqual(cards);
  });

  it("falls back to IndexedDB cache when fetch fails", async () => {
    const cached = [{ id: 2, name: "Counterspell" }];
    mockStore.set("tcg_offline_collection", cached);
    mockStore.set("tcg_offline_collection_synced_at", "2026-01-01T00:00:00Z");
    mockFetchCollection.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useOfflineCollection());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toEqual(cached);
    expect(result.current.isOffline).toBe(true);
    expect(result.current.lastSyncedAt).toBe("2026-01-01T00:00:00Z");
  });

  it("returns error when fetch fails and no cache available", async () => {
    mockFetchCollection.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useOfflineCollection());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.isOffline).toBe(true);
    expect(result.current.error).toBe("No cached data available");
  });
});
