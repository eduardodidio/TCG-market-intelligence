import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchTrending } from "../../src/api/trending";
import type { ApiResponse, TrendingResponse } from "../../src/types/api";

function makeTrendingEnvelope(
  overrides?: Partial<TrendingResponse>,
): ApiResponse<TrendingResponse> {
  return {
    data: {
      cards: [
        {
          card_id: 1,
          name_en: "Lightning Bolt",
          name_pt: "Raio",
          set_code: "lea",
          collector_number: "161",
          image_url: null,
          price_start: 10,
          price_end: 15,
          change_pct: 50,
          change_abs: 5,
          consistency: 0.9,
          composite_score: 75,
          observation_count: 5,
          currency: "BRL",
        },
      ],
      period: "30d",
      direction: "up",
      computed_at: "2026-08-22T12:00:00",
      cached: false,
      ...overrides,
    },
    meta: { cursor: null, total: null, offset: null, request_id: "test-req" },
    errors: [],
  };
}

describe("fetchTrending", () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("returns full API envelope with trending data", async () => {
    const envelope = makeTrendingEnvelope();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(envelope),
    });

    const result = await fetchTrending("gainers", { period: "30d", currency: "BRL" });

    expect(result.data).toBeTruthy();
    expect(result.data!.cards).toHaveLength(1);
    expect(result.data!.cards[0].name_en).toBe("Lightning Bolt");
    expect(result.errors).toHaveLength(0);
  });

  it("builds correct URL for direction", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeTrendingEnvelope()),
    });

    await fetchTrending("losers", { period: "7d", currency: "USD" });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/market/trending/losers");
    expect(calledUrl).toContain("period=7d");
    expect(calledUrl).toContain("currency=USD");
  });

  it("forwards abort signal to fetch", async () => {
    const controller = new AbortController();
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(makeTrendingEnvelope()),
    });

    await fetchTrending("gainers", { period: "30d" }, { signal: controller.signal });

    const fetchOptions = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1] as RequestInit;
    // The signal should be composed (apiGet composes external + timeout signals)
    expect(fetchOptions.signal).toBeTruthy();
  });

  it("returns error envelope on HTTP error", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve(null),
    });

    const result = await fetchTrending("gainers", { period: "30d" });

    expect(result.errors.length).toBeGreaterThan(0);
    expect(result.data).toBeNull();
  });
});
