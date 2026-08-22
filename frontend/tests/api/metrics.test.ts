import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchCardMetrics } from "../../src/api/metrics";
import type { ApiResponse, CardMetricsResponse } from "../../src/types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

const mockData: CardMetricsResponse = {
  entry_id: 1,
  card_id: 42,
  period: "30d",
  currency: "BRL",
  moving_averages: [],
  extremes: null,
  volatility: null,
  momentum: null,
  performance: null,
  period_comparison: null,
  data_points: 0,
};

describe("fetchCardMetrics", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    localStorage.setItem("tcg_access_token", "test-token");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("calls correct endpoint URL", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(envelope(mockData)),
    });

    await fetchCardMetrics(1, "30d", "BRL");

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/collection/1/metrics");
    expect(calledUrl).toContain("period=30d");
    expect(calledUrl).toContain("currency=BRL");
  });

  it("passes period and currency params", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(envelope(mockData)),
    });

    await fetchCardMetrics(5, "7d", "USD");

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/collection/5/metrics");
    expect(calledUrl).toContain("period=7d");
    expect(calledUrl).toContain("currency=USD");
  });

  it("includes auth header", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(envelope(mockData)),
    });

    await fetchCardMetrics(1, "30d", "BRL");

    const callArgs = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1] as RequestInit;
    expect(callArgs.headers).toBeDefined();
    const headers = callArgs.headers as Record<string, string>;
    expect(headers["Authorization"]).toBe("Bearer test-token");
  });

  it("returns data on success", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(envelope(mockData)),
    });

    const result = await fetchCardMetrics(1, "30d", "BRL");
    expect(result.data).toEqual(mockData);
    expect(result.errors).toHaveLength(0);
  });
});
