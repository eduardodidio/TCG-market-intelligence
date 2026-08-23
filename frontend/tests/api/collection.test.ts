import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { setManualPrice } from "../../src/api/collection";

describe("setManualPrice API client", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("sends PATCH request to /api/v1/collection/{id}/price with price and currency", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { id: 42, latest_price: 15.0, price_source: "manual" },
          meta: { cursor: null, total: null, offset: null, request_id: "r1" },
          errors: [],
        }),
    });
    globalThis.fetch = mockFetch as unknown as typeof fetch;

    const result = await setManualPrice(42, 15.0, "BRL");

    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [url, opts] = mockFetch.mock.calls[0];
    expect(String(url)).toContain("/api/v1/collection/42/price");
    expect(opts.method).toBe("PATCH");
    expect(opts.headers["Content-Type"]).toBe("application/json");

    const body = JSON.parse(opts.body);
    expect(body.price).toBe(15.0);
    expect(body.currency).toBe("BRL");

    expect(result.data).toBeDefined();
    expect(result.data!.price_source).toBe("manual");
  });

  it("returns error envelope on API failure", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, offset: null, request_id: "e1" },
          errors: [{ code: "validation_error", message: "Price must be positive" }],
        }),
    });
    globalThis.fetch = mockFetch as unknown as typeof fetch;

    const result = await setManualPrice(42, -1, "BRL");
    expect(result.data).toBeNull();
    expect(result.errors.length).toBeGreaterThan(0);
    expect(result.errors[0].message).toContain("Price must be positive");
  });

  it("includes auth token from localStorage", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: { id: 1 },
          meta: { cursor: null, total: null, offset: null, request_id: "r1" },
          errors: [],
        }),
    });
    globalThis.fetch = mockFetch as unknown as typeof fetch;

    // Set a fake token
    localStorage.setItem("tcg_access_token", "fake-jwt-token");

    await setManualPrice(1, 10.0, "USD");

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.headers["Authorization"]).toBe("Bearer fake-jwt-token");

    // Clean up
    localStorage.removeItem("tcg_access_token");
  });
});
