import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CardTile } from "../../src/components/CardTile";
import type { CardSummary } from "../../src/types/api";

function renderTile(card: CardSummary) {
  return render(
    <MemoryRouter>
      <CardTile card={card} />
    </MemoryRouter>,
  );
}

const CARD: CardSummary = {
  id: 42,
  game: "magic",
  name_en: "Lightning Bolt",
  name_pt: "Raio",
  set_code: "DMR",
  collector_number: "123",
  latest_price: 8.5,
};

describe("CardTile", () => {
  it("renders the card name", () => {
    renderTile(CARD);
    expect(screen.getByText("Lightning Bolt")).toBeDefined();
  });

  it("renders the set code badge", () => {
    renderTile(CARD);
    expect(screen.getByText("DMR")).toBeDefined();
  });

  it("renders the collector number", () => {
    renderTile(CARD);
    expect(screen.getByText("#123")).toBeDefined();
  });

  it("renders the formatted BRL price", () => {
    renderTile(CARD);
    const priceEl = screen.getByTestId("card-price");
    // formatBRL(8.5) produces locale-dependent output, but should contain "8,50"
    expect(priceEl.textContent).toContain("8,50");
  });

  it("renders '--' when price is null", () => {
    renderTile({ ...CARD, latest_price: null });
    const priceEl = screen.getByTestId("card-price");
    expect(priceEl.textContent).toBe("--");
  });

  it("links to the correct card detail page", () => {
    renderTile(CARD);
    const link = screen.getByTestId("card-tile-42");
    expect(link.getAttribute("href")).toBe("/cards/42");
  });

  it("falls back to name_pt when name_en is empty", () => {
    renderTile({ ...CARD, name_en: "", name_pt: "Raio" });
    expect(screen.getByText("Raio")).toBeDefined();
  });

  it("shows 'Unknown Card' when both names are empty/null", () => {
    renderTile({ ...CARD, name_en: "", name_pt: null });
    expect(screen.getByText("Unknown Card")).toBeDefined();
  });

  it("renders image placeholder area", () => {
    renderTile(CARD);
    expect(screen.getByTestId("card-image-placeholder")).toBeDefined();
  });

  it("handles missing set_code and collector_number", () => {
    renderTile({ ...CARD, set_code: null, collector_number: null });
    // Should still render without errors
    expect(screen.getByText("Lightning Bolt")).toBeDefined();
  });
});
