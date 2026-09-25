import { describe, it, expect, vi, beforeEach } from "vitest";

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();
const mockApiDelete = vi.fn();

vi.mock("../client", () => ({
  apiGet: (...args: unknown[]) => mockApiGet(...args),
  apiPost: (...args: unknown[]) => mockApiPost(...args),
  apiDelete: (...args: unknown[]) => mockApiDelete(...args),
}));

import {
  createDeckSuggestion,
  deleteDeckSuggestion,
  getDeckSuggestion,
  listDeckSuggestions,
  MTG_COLOR_KEYS,
  saveDeckSuggestion,
  SUGGESTION_ARCHETYPES,
  SUGGESTION_FORMATS,
} from "../deckSuggestions";

const BASE = "/api/v1/deck-suggestions";

describe("deckSuggestions API", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApiGet.mockResolvedValue({ data: null, errors: [], meta: {} });
    mockApiPost.mockResolvedValue({ data: null, errors: [], meta: {} });
    mockApiDelete.mockResolvedValue(undefined);
  });

  describe("createDeckSuggestion", () => {
    it("POSTs the body to the base path", async () => {
      const body = { format_name: "commander", commander_card_id: 42, notes: "x" };
      await createDeckSuggestion(body);
      expect(mockApiPost).toHaveBeenCalledWith(BASE, body);
    });

    it("passes an errors envelope through unchanged", async () => {
      const envelope = {
        data: null,
        errors: [{ code: "VALIDATION_LIMIT_EXCEEDED", message: "too many" }],
        meta: { cursor: null, total: null, offset: null, request_id: "" },
      };
      mockApiPost.mockResolvedValueOnce(envelope);
      const res = await createDeckSuggestion({
        format_name: "modern",
        colors: ["R"],
        archetype: "aggro",
      });
      expect(res).toBe(envelope);
    });
  });

  describe("listDeckSuggestions", () => {
    it("GETs without params when no status is given", async () => {
      await listDeckSuggestions();
      expect(mockApiGet).toHaveBeenCalledWith(BASE, undefined);
    });

    it("GETs with a status param", async () => {
      await listDeckSuggestions("done");
      expect(mockApiGet).toHaveBeenCalledWith(BASE, { status: "done" });
    });

    it("returns the helper's response", async () => {
      const envelope = { data: [], errors: [], meta: {} };
      mockApiGet.mockResolvedValueOnce(envelope);
      expect(await listDeckSuggestions()).toBe(envelope);
    });
  });

  describe("getDeckSuggestion", () => {
    it("GETs the detail path", async () => {
      await getDeckSuggestion(7);
      expect(mockApiGet).toHaveBeenCalledWith(`${BASE}/7`);
    });

    it("interpolates id 0 and large ids", async () => {
      await getDeckSuggestion(0);
      await getDeckSuggestion(2147483647);
      expect(mockApiGet).toHaveBeenNthCalledWith(1, `${BASE}/0`);
      expect(mockApiGet).toHaveBeenNthCalledWith(2, `${BASE}/2147483647`);
    });

    it("passes a not-found envelope through", async () => {
      const envelope = {
        data: null,
        errors: [{ code: "RESOURCE_NOT_FOUND", message: "nope" }],
        meta: {},
      };
      mockApiGet.mockResolvedValueOnce(envelope);
      expect(await getDeckSuggestion(99)).toBe(envelope);
    });
  });

  describe("saveDeckSuggestion", () => {
    it("POSTs an empty body when no deck name", async () => {
      await saveDeckSuggestion(1);
      expect(mockApiPost).toHaveBeenCalledWith(`${BASE}/1/save`, {});
    });

    it("POSTs an empty body when deck name is empty", async () => {
      await saveDeckSuggestion(1, "");
      expect(mockApiPost).toHaveBeenCalledWith(`${BASE}/1/save`, {});
    });

    it("POSTs deck_name when provided", async () => {
      await saveDeckSuggestion(3, "Atraxa Superfriends");
      expect(mockApiPost).toHaveBeenCalledWith(`${BASE}/3/save`, {
        deck_name: "Atraxa Superfriends",
      });
    });

    it("passes a conflict envelope through", async () => {
      const envelope = {
        data: null,
        errors: [{ code: "RESOURCE_CONFLICT", message: "not done" }],
        meta: {},
      };
      mockApiPost.mockResolvedValueOnce(envelope);
      expect(await saveDeckSuggestion(5)).toBe(envelope);
    });
  });

  describe("deleteDeckSuggestion", () => {
    it("DELETEs the detail path", async () => {
      await deleteDeckSuggestion(12);
      expect(mockApiDelete).toHaveBeenCalledWith(`${BASE}/12`);
    });

    it("propagates helper rejection", async () => {
      mockApiDelete.mockRejectedValueOnce(new Error("HTTP 409"));
      await expect(deleteDeckSuggestion(12)).rejects.toThrow("HTTP 409");
    });
  });

  describe("constants", () => {
    it("exposes all backend formats with card counts", () => {
      expect(SUGGESTION_FORMATS.map((f) => f.value)).toEqual([
        "commander", "standard", "pioneer", "modern",
        "legacy", "vintage", "pauper", "casual",
      ]);
      expect(SUGGESTION_FORMATS.find((f) => f.value === "commander")?.cardCount).toBe(100);
      expect(SUGGESTION_FORMATS.find((f) => f.value === "modern")?.cardCount).toBe(60);
    });

    it("exposes all backend archetypes", () => {
      expect(SUGGESTION_ARCHETYPES.map((a) => a.value)).toEqual([
        "aggro", "control", "midrange", "combo", "tempo", "ramp",
      ]);
    });

    it("exposes WUBRG color keys in order", () => {
      expect([...MTG_COLOR_KEYS]).toEqual(["W", "U", "B", "R", "G"]);
    });
  });
});
