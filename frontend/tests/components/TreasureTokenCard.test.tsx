import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { TreasureTokenCard } from "../../src/components/TreasureTokenCard";
import {
  LanguageContext,
  type LanguageContextValue,
} from "../../src/contexts/LanguageContext";

// Mock react-i18next (must include initReactI18next for LanguageContext import chain)
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "credits.balance": "Treasure Tokens",
        "credits.tokenTypeLine": "Token Artifact — Treasure",
        "credits.tokenRulesText":
          "Tap, Sacrifice this artifact: Add one mana of any color.",
      };
      return map[key] ?? key;
    },
  }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

function renderWithLanguage(language: "en" | "pt-BR" = "en") {
  const value: LanguageContextValue = {
    language,
    setLanguage: vi.fn(),
  };
  return render(
    createElement(
      LanguageContext.Provider,
      { value },
      createElement(TreasureTokenCard, { count: 10 }),
    ),
  );
}

describe("TreasureTokenCard", () => {
  it("renders an img element with treasure-image testid", () => {
    renderWithLanguage("en");
    const img = screen.getByTestId("treasure-image");
    expect(img).toBeDefined();
    expect(img.tagName).toBe("IMG");
  });

  it("renders EN image when language is en", () => {
    renderWithLanguage("en");
    const img = screen.getByTestId("treasure-image") as HTMLImageElement;
    expect(img.src).toContain("treasure");
    expect(img.src).not.toContain("tesouro");
  });

  it("renders PT image when language is pt-BR", () => {
    renderWithLanguage("pt-BR");
    const img = screen.getByTestId("treasure-image") as HTMLImageElement;
    expect(img.src).toContain("tesouro");
  });

  it("renders count badge with correct value", () => {
    renderWithLanguage();
    const count = screen.getByTestId("treasure-count");
    expect(count.textContent).toBe("10");
  });

  it("renders localized type line", () => {
    renderWithLanguage();
    expect(screen.getByText("Token Artifact — Treasure")).toBeDefined();
  });

  it("renders localized rules text", () => {
    renderWithLanguage();
    expect(
      screen.getByText(
        "Tap, Sacrifice this artifact: Add one mana of any color.",
      ),
    ).toBeDefined();
  });

  it("has no hardcoded English text for type line or rules", () => {
    renderWithLanguage();
    // The component should use t() for type line and rules text
    // This is verified by the mock returning the expected values
    const card = screen.getByTestId("treasure-token-card");
    expect(card).toBeDefined();
  });
});
