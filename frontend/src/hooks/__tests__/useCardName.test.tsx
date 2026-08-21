import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { type ReactNode } from "react";
import { LanguageProvider } from "../../contexts/LanguageContext";
import { useCardName } from "../useCardName";

// Mock i18n to control language
vi.mock("../../i18n/i18n", () => ({
  default: {
    language: "en",
    changeLanguage: vi.fn(),
  },
}));

function wrapper({ children }: { children: ReactNode }) {
  return <LanguageProvider>{children}</LanguageProvider>;
}

describe("useCardName hook", () => {
  describe("getCardName", () => {
    it("returns name_en when language is en", () => {
      localStorage.setItem("tcg_language", "en");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const name = result.current.getCardName("Lightning Bolt", "Relampago", "Fallback");
      expect(name).toBe("Lightning Bolt");
    });

    it("returns name_pt when language is pt-BR and name_pt exists", () => {
      localStorage.setItem("tcg_language", "pt-BR");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const name = result.current.getCardName("Lightning Bolt", "Relampago");
      expect(name).toBe("Relampago");
      localStorage.removeItem("tcg_language");
    });

    it("falls back to name_en when language is pt-BR but name_pt is null", () => {
      localStorage.setItem("tcg_language", "pt-BR");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const name = result.current.getCardName("Lightning Bolt", null);
      expect(name).toBe("Lightning Bolt");
      localStorage.removeItem("tcg_language");
    });

    it("falls back to name_pt when name_en is null (any language)", () => {
      localStorage.setItem("tcg_language", "en");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const name = result.current.getCardName(null, "Relampago");
      expect(name).toBe("Relampago");
    });

    it("falls back to fallback when both names are null", () => {
      const { result } = renderHook(() => useCardName(), { wrapper });
      const name = result.current.getCardName(null, null, "Unknown Card");
      expect(name).toBe("Unknown Card");
    });

    it("returns 'Unknown Card' when all args are null/undefined", () => {
      const { result } = renderHook(() => useCardName(), { wrapper });
      const name = result.current.getCardName(undefined, undefined);
      expect(name).toBe("Unknown Card");
    });

    it("falls back to name_en when language is pt-BR and name_pt is empty string", () => {
      localStorage.setItem("tcg_language", "pt-BR");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const name = result.current.getCardName("Lightning Bolt", "");
      expect(name).toBe("Lightning Bolt");
      localStorage.removeItem("tcg_language");
    });
  });

  describe("getSubtitleName", () => {
    it("returns name_en as subtitle when language is pt-BR", () => {
      localStorage.setItem("tcg_language", "pt-BR");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const subtitle = result.current.getSubtitleName("Lightning Bolt", "Relampago");
      expect(subtitle).toBe("Lightning Bolt");
      localStorage.removeItem("tcg_language");
    });

    it("returns name_pt as subtitle when language is en", () => {
      localStorage.setItem("tcg_language", "en");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const subtitle = result.current.getSubtitleName("Lightning Bolt", "Relampago");
      expect(subtitle).toBe("Relampago");
    });

    it("returns null when no alternate name exists", () => {
      localStorage.setItem("tcg_language", "en");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const subtitle = result.current.getSubtitleName("Lightning Bolt", null);
      expect(subtitle).toBeNull();
    });

    it("returns null when both names are the same", () => {
      localStorage.setItem("tcg_language", "en");
      const { result } = renderHook(() => useCardName(), { wrapper });
      const subtitle = result.current.getSubtitleName("Lightning Bolt", "Lightning Bolt");
      expect(subtitle).toBeNull();
    });
  });

  describe("without LanguageProvider", () => {
    it("defaults to en behavior when no provider is present", () => {
      const { result } = renderHook(() => useCardName());
      const name = result.current.getCardName("Lightning Bolt", "Relampago");
      expect(name).toBe("Lightning Bolt");
    });
  });
});
