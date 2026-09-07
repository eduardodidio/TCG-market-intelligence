import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { DuplicatesList } from "../DuplicatesList";
import type { DuplicateCard } from "../../types/tradeMatch";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "common.unknownCard": "Unknown Card",
        "tradeMatch.surplus": "Available",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

const MOCK_CARDS: DuplicateCard[] = [
  {
    card_id: 1,
    name_en: "Lightning Bolt",
    name_pt: null,
    set_code: "2ed",
    collector_number: "157",
    quantity: 3,
    surplus: 2,
    quality: "NM",
    image_uri: null,
    current_price: null,
  },
  {
    card_id: 2,
    name_en: "Counterspell",
    name_pt: null,
    set_code: "2ed",
    collector_number: "55",
    quantity: 2,
    surplus: 1,
    quality: null,
    image_uri: null,
    current_price: null,
  },
];

describe("DuplicatesList", () => {
  it("renders nothing for empty list", () => {
    const { container } = render(
      <MemoryRouter>
        <DuplicatesList duplicates={[]} />
      </MemoryRouter>,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders duplicate cards with surplus badges", () => {
    render(
      <MemoryRouter>
        <DuplicatesList duplicates={MOCK_CARDS} />
      </MemoryRouter>,
    );

    expect(screen.getByTestId("duplicates-list")).toBeDefined();
    expect(screen.getAllByTestId("duplicate-card")).toHaveLength(2);
    // Check that quantity badges are shown
    expect(screen.getByText("x3")).toBeDefined();
    expect(screen.getByText("x2")).toBeDefined();
  });

  it("displays card names", () => {
    render(
      <MemoryRouter>
        <DuplicatesList duplicates={MOCK_CARDS} />
      </MemoryRouter>,
    );

    expect(screen.getByText("Lightning Bolt")).toBeDefined();
    expect(screen.getByText("Counterspell")).toBeDefined();
  });

  it("displays set codes", () => {
    render(
      <MemoryRouter>
        <DuplicatesList duplicates={MOCK_CARDS} />
      </MemoryRouter>,
    );

    // The set code should appear (uppercase)
    const setElements = screen.getAllByText(/2ed/i);
    expect(setElements.length).toBeGreaterThanOrEqual(2);
  });
});
