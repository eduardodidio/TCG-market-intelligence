import { describe, it, expect, vi, beforeEach } from "vitest";

const mockApiGet = vi.fn();

vi.mock("../client", () => ({
  apiGet: (...args: unknown[]) => mockApiGet(...args),
}));

import { fetchMetaDeck, fetchMetaDecks, fetchMetaFormats } from "../metaDecks";
import { META_FORMATS } from "../../types/metaDecks";

const okEnvelope = { data: {}, meta: {}, errors: [] };

describe("metaDecks API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockResolvedValue(okEnvelope);
  });

  describe("META_FORMATS", () => {
    it("lists the seven formats in display order", () => {
      expect(META_FORMATS).toEqual([
        "commander",
        "standard",
        "pioneer",
        "modern",
        "legacy",
        "pauper",
        "vintage",
      ]);
    });
  });

  describe("fetchMetaFormats", () => {
    it("calls the formats endpoint without params", async () => {
      await fetchMetaFormats();
      expect(mockApiGet).toHaveBeenCalledWith("/api/v1/meta-decks/formats", undefined, undefined);
    });

    it("forwards the abort signal", async () => {
      const controller = new AbortController();
      await fetchMetaFormats({ signal: controller.signal });
      expect(mockApiGet).toHaveBeenCalledWith("/api/v1/meta-decks/formats", undefined, {
        signal: controller.signal,
      });
    });
  });

  describe("fetchMetaDecks", () => {
    it("sends only format when no optional params are given", async () => {
      await fetchMetaDecks({ format: "modern" });
      expect(mockApiGet).toHaveBeenCalledWith(
        "/api/v1/meta-decks",
        { format: "modern" },
        undefined,
      );
    });

    it("stringifies numeric limit and offset", async () => {
      await fetchMetaDecks({ format: "pauper", limit: 20, offset: 40 });
      expect(mockApiGet).toHaveBeenCalledWith(
        "/api/v1/meta-decks",
        { format: "pauper", limit: "20", offset: "40" },
        undefined,
      );
    });

    it("sends offset 0 (not treated as falsy)", async () => {
      await fetchMetaDecks({ format: "legacy", offset: 0 });
      expect(mockApiGet.mock.calls[0][1]).toEqual({ format: "legacy", offset: "0" });
    });

    it("omits undefined params and includes snapshot_date when set", async () => {
      await fetchMetaDecks({
        format: "commander",
        limit: undefined,
        snapshot_date: "2026-09-20",
      });
      const query = mockApiGet.mock.calls[0][1];
      expect(query).toEqual({ format: "commander", snapshot_date: "2026-09-20" });
      expect(query).not.toHaveProperty("limit");
      expect(query).not.toHaveProperty("offset");
    });

    it("omits an empty snapshot_date", async () => {
      await fetchMetaDecks({ format: "vintage", snapshot_date: "" });
      expect(mockApiGet.mock.calls[0][1]).toEqual({ format: "vintage" });
    });

    it("forwards the abort signal", async () => {
      const controller = new AbortController();
      await fetchMetaDecks({ format: "modern" }, { signal: controller.signal });
      expect(mockApiGet.mock.calls[0][2]).toEqual({ signal: controller.signal });
    });

    it("passes through an error envelope without throwing", async () => {
      const errorEnvelope = {
        data: null,
        meta: {},
        errors: [{ code: "VALIDATION_ERROR", message: "bad format" }],
      };
      mockApiGet.mockResolvedValue(errorEnvelope);
      await expect(fetchMetaDecks({ format: "modern" })).resolves.toBe(errorEnvelope);
    });
  });

  describe("fetchMetaDeck", () => {
    it("calls the detail endpoint with the deck id", async () => {
      await fetchMetaDeck(42);
      expect(mockApiGet).toHaveBeenCalledWith("/api/v1/meta-decks/42", undefined, undefined);
    });

    it("returns the envelope from apiGet", async () => {
      const envelope = {
        data: { id: 1, cards: [] },
        meta: {},
        errors: [],
      };
      mockApiGet.mockResolvedValue(envelope);
      await expect(fetchMetaDeck(1)).resolves.toBe(envelope);
    });

    it("passes through a 404 error envelope without throwing", async () => {
      const notFound = {
        data: null,
        meta: {},
        errors: [{ code: "NOT_FOUND", message: "deck not found" }],
      };
      mockApiGet.mockResolvedValue(notFound);
      await expect(fetchMetaDeck(9999)).resolves.toBe(notFound);
    });
  });
});
