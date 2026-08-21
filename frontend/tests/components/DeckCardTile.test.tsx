import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeckCardTile } from "../../src/components/DeckCardTile";
import type { DeckCard } from "../../src/types/api";

function renderTile(card: DeckCard) {
  return render(
    <MemoryRouter>
      <DeckCardTile card={card} />
    </MemoryRouter>,
  );
}

const OWNED_CARD: DeckCard = {
  id: 10,
  name_en: "Lightning Bolt",
  set_code: "lea",
  collector_number: "161",
  quantity: 4,
  card_id: 42,
  in_collection: true,
  owned_quantity: 3,
  collection_entry_id: 100,
  image_url: "https://api.scryfall.com/cards/lea/161?format=image&version=normal",
  latest_price: 5.0,
};

const UNOWNED_CARD: DeckCard = {
  id: 11,
  name_en: "Force of Will",
  set_code: "all",
  collector_number: "28",
  quantity: 2,
  card_id: 50,
  in_collection: false,
  owned_quantity: 0,
  collection_entry_id: null,
  image_url: "https://api.scryfall.com/cards/all/28?format=image&version=normal",
  latest_price: null,
};

describe("DeckCardTile", () => {
  it("renders card name", () => {
    renderTile(OWNED_CARD);
    expect(screen.getByTestId("card-name").textContent).toBe("Lightning Bolt");
  });

  it("renders set badge", () => {
    renderTile(OWNED_CARD);
    expect(screen.getByTestId("set-badge").textContent).toBe("lea");
  });

  it("renders collector number", () => {
    renderTile(OWNED_CARD);
    expect(screen.getByTestId("collector-number").textContent).toBe("#161");
  });

  it("renders quantity badge for qty > 1", () => {
    renderTile(OWNED_CARD);
    expect(screen.getByTestId("quantity-badge").textContent).toBe("x4");
  });

  it("does not render quantity badge for qty == 1", () => {
    renderTile({ ...OWNED_CARD, quantity: 1 });
    expect(screen.queryByTestId("quantity-badge")).toBeNull();
  });

  it("renders price when available", () => {
    renderTile(OWNED_CARD);
    expect(screen.getByTestId("card-price").textContent).toContain("5,00");
  });

  it("renders '--' when price is null", () => {
    renderTile(UNOWNED_CARD);
    expect(screen.getByTestId("card-price").textContent).toBe("--");
  });

  it("shows not-owned overlay for cards not in collection", () => {
    renderTile(UNOWNED_CARD);
    expect(screen.getByTestId("not-owned-overlay")).toBeDefined();
  });

  it("does not show overlay for owned cards", () => {
    renderTile(OWNED_CARD);
    expect(screen.queryByTestId("not-owned-overlay")).toBeNull();
  });

  it("links to collection entry for owned cards", () => {
    renderTile(OWNED_CARD);
    const link = screen.getByTestId("deck-card-link-10");
    expect(link.getAttribute("href")).toBe("/collection/100");
  });

  it("links to card detail for unowned cards with card_id", () => {
    renderTile(UNOWNED_CARD);
    const link = screen.getByTestId("deck-card-link-11");
    expect(link.getAttribute("href")).toBe("/cards/50");
  });

  it("renders without link when no card_id and not in collection", () => {
    const noIdCard: DeckCard = {
      ...UNOWNED_CARD,
      card_id: null,
    };
    renderTile(noIdCard);
    expect(screen.queryByTestId("deck-card-link-11")).toBeNull();
    expect(screen.getByTestId("deck-card-tile-11")).toBeDefined();
  });
});
