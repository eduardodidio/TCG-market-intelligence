import { describe, it, expect, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { createElement } from "react";
import {
  LanguageContext,
  type LanguageContextValue,
} from "../../src/contexts/LanguageContext";
import { useTreasureImage } from "../../src/hooks/useTreasureImage";

// Vitest handles image imports as the file path string
function renderWithLanguage(language: "en" | "pt-BR") {
  const value: LanguageContextValue = {
    language,
    setLanguage: vi.fn(),
  };
  return renderHook(() => useTreasureImage(), {
    wrapper: ({ children }) =>
      createElement(LanguageContext.Provider, { value }, children),
  });
}

describe("useTreasureImage", () => {
  it("returns EN image when language is en", () => {
    const { result } = renderWithLanguage("en");
    expect(result.current).toContain("treasure");
    expect(result.current).not.toContain("tesouro");
  });

  it("returns PT image when language is pt-BR", () => {
    const { result } = renderWithLanguage("pt-BR");
    expect(result.current).toContain("tesouro");
  });

  it("defaults to EN image when context is null", () => {
    const { result } = renderHook(() => useTreasureImage());
    // No LanguageContext provider — ctx is null, defaults to 'en'
    expect(result.current).toContain("treasure");
  });
});
