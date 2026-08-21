import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
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

  it("shows 'No price data' when price is null", () => {
    renderTile({ ...CARD, latest_price: null });
    const priceEl = screen.getByTestId("card-price");
    expect(priceEl.textContent).toBe("No price data");
  });

  it("shows 'No price data' when price is 0", () => {
    renderTile({ ...CARD, latest_price: 0 });
    const priceEl = screen.getByTestId("card-price");
    expect(priceEl.textContent).toBe("No price data");
  });

  it("uses muted styling for missing price", () => {
    renderTile({ ...CARD, latest_price: null });
    const priceEl = screen.getByTestId("card-price");
    expect(priceEl.className).toContain("text-tcg-dimmed");
    expect(priceEl.className).not.toContain("text-tcg-secondary");
  });

  it("uses cyan styling for valid price", () => {
    renderTile(CARD);
    const priceEl = screen.getByTestId("card-price");
    expect(priceEl.className).toContain("text-tcg-secondary");
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

  // --- Image fallback chain tests ---

  it("renders Scryfall image by set+number when both are present", () => {
    renderTile(CARD);
    const img = screen.getByRole("img");
    expect(img.getAttribute("src")).toBe(
      "https://api.scryfall.com/cards/dmr/123?format=image&version=normal",
    );
  });

  it("falls back to name-based Scryfall URL on image error using name_en", () => {
    renderTile(CARD);
    const img = screen.getByRole("img");
    // Simulate primary image failing
    fireEvent.error(img);
    // Should now use name_en for the fallback URL (not name_pt)
    expect(img.getAttribute("src")).toBe(
      "https://api.scryfall.com/cards/named?exact=Lightning%20Bolt&format=image&version=normal",
    );
  });

  it("shows placeholder SVG when card has only name_pt and no set info", () => {
    renderTile({
      ...CARD,
      name_en: "",
      name_pt: "Teste de Resistencia",
      set_code: null,
      collector_number: null,
    });
    // No <img> element should be rendered — only the placeholder SVG
    expect(screen.queryByRole("img")).toBeNull();
    // The placeholder SVG should be present (aria-hidden)
    const placeholder = screen.getByTestId("card-image-placeholder");
    const svg = placeholder.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg!.getAttribute("aria-hidden")).toBe("true");
  });

  it("shows placeholder SVG after both primary and fallback images fail", () => {
    renderTile(CARD);
    const img = screen.getByRole("img");
    // Primary fails
    fireEvent.error(img);
    // Fallback also fails
    fireEvent.error(img);
    // Now should show placeholder SVG, no broken image
    expect(screen.queryByRole("img")).toBeNull();
    const placeholder = screen.getByTestId("card-image-placeholder");
    const svg = placeholder.querySelector("svg");
    expect(svg).not.toBeNull();
  });

  it("does not use Portuguese name for Scryfall fallback URL", () => {
    const ptCard: CardSummary = {
      ...CARD,
      name_en: "Endurance Test",
      name_pt: "Teste de Resistencia",
    };
    renderTile(ptCard);
    const img = screen.getByRole("img");
    // Simulate primary image failing
    fireEvent.error(img);
    // Fallback URL must use the English name, not Portuguese
    const src = img.getAttribute("src")!;
    expect(src).toContain("Endurance%20Test");
    expect(src).not.toContain("Teste");
  });

  it("shows placeholder when name_en is absent and set/number image fails", () => {
    renderTile({
      ...CARD,
      name_en: "",
      name_pt: "Remora Mistica",
    });
    const img = screen.getByRole("img");
    // Primary image (set/number) fails — no fallback URL because name_en is empty
    fireEvent.error(img);
    // Should show placeholder, not a broken image
    expect(screen.queryByRole("img")).toBeNull();
    const svg = screen.getByTestId("card-image-placeholder").querySelector("svg");
    expect(svg).not.toBeNull();
  });
});
