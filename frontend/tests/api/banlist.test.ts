import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  fetchFormats,
  fetchBanList,
  fetchBanlistStatus,
  fetchCardLegalities,
  fetchLegalityHistory,
} from "../../src/api/banlist";

describe("banlist API client", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchOk(data: unknown) {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data,
          meta: { cursor: null, total: null, offset: null, request_id: "r1" },
          errors: [],
        }),
    }) as unknown as typeof fetch;
  }

  it("fetchFormats calls /api/v1/banlist/formats", async () => {
    mockFetchOk(["standard", "modern"]);
    const result = await fetchFormats();
    expect(result.data).toEqual(["standard", "modern"]);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/banlist/formats");
  });

  it("fetchBanList calls /api/v1/banlist with params", async () => {
    mockFetchOk([]);
    await fetchBanList({ format: "standard", status: "banned" });
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/banlist");
    expect(calledUrl).toContain("format=standard");
    expect(calledUrl).toContain("status=banned");
  });

  it("fetchBanList includes owned_only=true only when ownedOnly is true", async () => {
    mockFetchOk([]);
    await fetchBanList({ format: "commander", ownedOnly: true });
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("owned_only=true");
  });

  it("fetchBanList omits owned_only when ownedOnly is false/undefined", async () => {
    mockFetchOk([]);
    await fetchBanList({ format: "commander" });
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).not.toContain("owned_only");
  });

  it("fetchBanlistStatus calls /api/v1/banlist/status", async () => {
    mockFetchOk({
      last_synced_at: null,
      legalities_count: 0,
      banned_count: 0,
      restricted_count: 0,
      history_count: 0,
      formats: 0,
    });
    await fetchBanlistStatus();
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/banlist/status");
  });

  it("fetchCardLegalities calls /api/v1/banlist/card/{id}", async () => {
    mockFetchOk([]);
    await fetchCardLegalities(42);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/banlist/card/42");
  });

  it("fetchLegalityHistory calls /api/v1/banlist/history", async () => {
    mockFetchOk([]);
    await fetchLegalityHistory({ format: "modern", limit: 10 });
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/banlist/history");
    expect(calledUrl).toContain("format=modern");
    expect(calledUrl).toContain("limit=10");
  });
});
