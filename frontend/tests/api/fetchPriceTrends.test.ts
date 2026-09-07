import { describe, it, expect, vi, beforeEach } from "vitest";
import { fetchPriceTrends } from "../../src/api/cards";

describe("fetchPriceTrends", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("calls API with correct parameters", async () => {
    const mockResponse = {
      data: {
        trends: {
          "1": { prices: [10, 12, 15], change_pct: 50.0 },
          "2": { prices: [], change_pct: null },
        },
      },
      meta: { cursor: null, total: null, offset: null, request_id: "test" },
      errors: [],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await fetchPriceTrends([1, 2], 7);

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(calledUrl).toContain("card_ids=1%2C2");
    expect(calledUrl).toContain("days=7");
    expect(result.data?.trends["1"].change_pct).toBe(50.0);
    expect(result.data?.trends["2"].prices).toEqual([]);
  });

  it("returns typed response", async () => {
    const mockResponse = {
      data: {
        trends: {
          "5": { prices: [1, 2, 3], change_pct: 200.0 },
        },
      },
      meta: { cursor: null, total: null, offset: null, request_id: "test" },
      errors: [],
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await fetchPriceTrends([5]);

    expect(result.data).toBeDefined();
    expect(result.data!.trends["5"]).toBeDefined();
    expect(result.data!.trends["5"].prices).toEqual([1, 2, 3]);
    expect(result.data!.trends["5"].change_pct).toBe(200.0);
  });
});
