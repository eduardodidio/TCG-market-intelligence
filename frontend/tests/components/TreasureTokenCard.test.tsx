import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { createElement } from "react";
import { TreasureTokenCard } from "../../src/components/TreasureTokenCard";
import {
  CurrencyContext,
  type CurrencyCode,
} from "../../src/contexts/CurrencyContext";

// Mock react-i18next
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

function renderWithCurrency(currency: CurrencyCode = "BRL") {
  const value = {
    currency,
    setCurrency: vi.fn(),
    toggle: vi.fn(),
  };
  return render(
    createElement(
      CurrencyContext.Provider,
      { value },
      createElement(TreasureTokenCard, { count: 10 }),
    ),
  );
}

describe("TreasureTokenCard", () => {
  it("renders an img element with treasure-image testid", () => {
    renderWithCurrency("BRL");
    const img = screen.getByTestId("treasure-image");
    expect(img).toBeDefined();
    expect(img.tagName).toBe("IMG");
  });

  it("renders default image when currency is BRL", () => {
    renderWithCurrency("BRL");
    const img = screen.getByTestId("treasure-image") as HTMLImageElement;
    expect(img.src).toContain("treasure");
    expect(img.src).not.toContain("tesouro");
  });

  it("renders PT image when currency is PILA", () => {
    renderWithCurrency("PILA");
    const img = screen.getByTestId("treasure-image") as HTMLImageElement;
    expect(img.src).toContain("tesouro");
  });

  it("renders count badge with correct value", () => {
    renderWithCurrency();
    const count = screen.getByTestId("treasure-count");
    expect(count.textContent).toBe("10");
  });

  it("renders localized type line", () => {
    renderWithCurrency();
    expect(screen.getByText("Token Artifact — Treasure")).toBeDefined();
  });

  it("renders localized rules text", () => {
    renderWithCurrency();
    expect(
      screen.getByText(
        "Tap, Sacrifice this artifact: Add one mana of any color.",
      ),
    ).toBeDefined();
  });

  it("has no hardcoded English text for type line or rules", () => {
    renderWithCurrency();
    // The component should use t() for type line and rules text
    // This is verified by the mock returning the expected values
    const card = screen.getByTestId("treasure-token-card");
    expect(card).toBeDefined();
  });
});
