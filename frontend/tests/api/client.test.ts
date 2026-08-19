import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { apiGet } from "../../src/api/client";
import { mockCardSummaries, mockApiError } from "../fixtures/api-responses";

describe("apiGet", () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  it("returns typed data on success", async () => {
    const mockResponse = mockCardSummaries(3);
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    });

    const result = await apiGet<typeof mockResponse.data>("/api/v1/cards");

    expect(result.data).toEqual(mockResponse.data);
    expect(result.errors).toHaveLength(0);
    expect(result.meta.request_id).toBe("req-test-001");
  });

  it("passes query params to the URL", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCardSummaries()),
    });

    await apiGet("/api/v1/cards", { game: "magic", name: "bolt" });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("game=magic");
    expect(calledUrl).toContain("name=bolt");
  });

  it("skips empty params", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockCardSummaries()),
    });

    await apiGet("/api/v1/cards", { name: "", game: "magic" });

    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).not.toContain("name=");
    expect(calledUrl).toContain("game=magic");
  });

  it("returns errors envelope on HTTP 4xx", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: () => Promise.resolve({ detail: "Card not found" }),
    });

    const result = await apiGet("/api/v1/cards/999");

    expect(result.data).toBeNull();
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].code).toBe("HTTP_404");
    expect(result.errors[0].message).toBe("Card not found");
  });

  it("uses backend error envelope when available", async () => {
    const backendError = mockApiError("VALIDATION_ERROR", "Invalid field");
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: "Unprocessable Entity",
      json: () => Promise.resolve(backendError),
    });

    const result = await apiGet("/api/v1/cards");

    expect(result.errors[0].code).toBe("VALIDATION_ERROR");
    expect(result.errors[0].message).toBe("Invalid field");
  });

  it("returns NETWORK_ERROR on fetch failure", async () => {
    globalThis.fetch = vi
      .fn()
      .mockRejectedValue(new TypeError("Failed to fetch"));

    const result = await apiGet("/api/v1/cards");

    expect(result.data).toBeNull();
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].code).toBe("NETWORK_ERROR");
    expect(result.errors[0].message).toBe("Failed to fetch");
  });

  it("aborts when external signal fires (composeAbortSignals)", async () => {
    const externalController = new AbortController();

    globalThis.fetch = vi.fn().mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("The operation was aborted.", "AbortError"));
          });
        }),
    );

    const resultPromise = apiGet("/api/v1/cards", undefined, {
      signal: externalController.signal,
      timeoutMs: 60000, // long timeout so it won't fire
    });

    // Abort via external signal
    externalController.abort();

    const result = await resultPromise;

    expect(result.data).toBeNull();
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].code).toBe("TIMEOUT");
  });

  it("handles already-aborted external signal", async () => {
    const externalController = new AbortController();
    externalController.abort(); // abort before calling apiGet

    globalThis.fetch = vi.fn().mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          // If signal is already aborted, reject immediately
          if (init?.signal?.aborted) {
            reject(new DOMException("The operation was aborted.", "AbortError"));
            return;
          }
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("The operation was aborted.", "AbortError"));
          });
        }),
    );

    const result = await apiGet("/api/v1/cards", undefined, {
      signal: externalController.signal,
      timeoutMs: 60000,
    });

    expect(result.data).toBeNull();
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].code).toBe("TIMEOUT");
  });

  it("returns TIMEOUT error when request exceeds timeout", async () => {
    // Mock fetch that never resolves (simulates hang)
    globalThis.fetch = vi.fn().mockImplementation(
      (_url: string, init?: RequestInit) =>
        new Promise((_resolve, reject) => {
          // Listen for abort
          init?.signal?.addEventListener("abort", () => {
            reject(new DOMException("The operation was aborted.", "AbortError"));
          });
        }),
    );

    const resultPromise = apiGet("/api/v1/cards", undefined, {
      timeoutMs: 5000,
    });

    // Advance time past the timeout
    await vi.advanceTimersByTimeAsync(5001);

    const result = await resultPromise;

    expect(result.data).toBeNull();
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].code).toBe("TIMEOUT");
    expect(result.errors[0].message).toBe("Request timed out");
  });
});
