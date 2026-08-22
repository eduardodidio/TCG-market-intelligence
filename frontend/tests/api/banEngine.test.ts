import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchCollectionBanned, fetchEntryLegalities } from "../../src/api/banEngine";

describe("banEngine API client", () => {
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

  it("fetchCollectionBanned calls /api/v1/collection/banned", async () => {
    mockFetchOk([]);
    const result = await fetchCollectionBanned();
    expect(result.data).toEqual([]);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/collection/banned");
  });

  it("fetchCollectionBanned with format param", async () => {
    mockFetchOk([]);
    await fetchCollectionBanned({ format: "standard" });
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("format=standard");
  });

  it("fetchCollectionBanned with days param", async () => {
    mockFetchOk([]);
    await fetchCollectionBanned({ days: 7 });
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("days=7");
  });

  it("fetchEntryLegalities calls correct URL", async () => {
    mockFetchOk([]);
    await fetchEntryLegalities(42);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("/api/v1/collection/42/legality");
  });

  it("fetchEntryLegalities with days param", async () => {
    mockFetchOk([]);
    await fetchEntryLegalities(42, { days: 60 });
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock
      .calls[0][0] as string;
    expect(calledUrl).toContain("days=60");
  });
});
