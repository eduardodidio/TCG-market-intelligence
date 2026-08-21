import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { fetchDecks, fetchDeck, importDeck, deleteDeck } from "../../src/api/decks";

describe("Deck API client", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchJson(data: unknown, ok = true, status = 200) {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok,
      status,
      statusText: "OK",
      json: () => Promise.resolve(data),
    }) as unknown as typeof fetch;
  }

  describe("fetchDecks", () => {
    it("returns deck list", async () => {
      const envelope = {
        data: [{ id: 1, name: "Test" }],
        meta: { cursor: null, total: null, offset: null, request_id: "r1" },
        errors: [],
      };
      mockFetchJson(envelope);

      const resp = await fetchDecks();
      expect(resp.data).toHaveLength(1);
      expect(resp.data![0].name).toBe("Test");
    });
  });

  describe("fetchDeck", () => {
    it("returns deck detail", async () => {
      const envelope = {
        data: { id: 1, name: "Test", cards: [] },
        meta: { cursor: null, total: null, offset: null, request_id: "r1" },
        errors: [],
      };
      mockFetchJson(envelope);

      const resp = await fetchDeck(1);
      expect(resp.data!.id).toBe(1);
    });
  });

  describe("importDeck", () => {
    it("sends POST with correct body", async () => {
      const envelope = {
        data: { deck_id: 1, name: "My Deck", cards_imported: 4, cards_linked: 2 },
        meta: { cursor: null, total: null, offset: null, request_id: "r1" },
        errors: [],
      };
      mockFetchJson(envelope);

      const resp = await importDeck("My Deck", "text", "4 Bolt");
      expect(resp.data!.deck_id).toBe(1);

      const fetchCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(fetchCall[1].method).toBe("POST");

      const body = JSON.parse(fetchCall[1].body);
      expect(body.name).toBe("My Deck");
      expect(body.format).toBe("text");
      expect(body.content).toBe("4 Bolt");
    });
  });

  describe("deleteDeck", () => {
    it("sends DELETE request", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        statusText: "No Content",
        json: () => Promise.resolve(null),
      }) as unknown as typeof fetch;

      await deleteDeck(1);

      const fetchCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(fetchCall[1].method).toBe("DELETE");
      expect(fetchCall[0]).toContain("/api/v1/decks/1");
    });
  });
});
