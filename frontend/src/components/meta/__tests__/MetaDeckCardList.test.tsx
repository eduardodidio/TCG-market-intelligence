import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { MetaDeckCardList } from "../MetaDeckCardList";
import { makeCard } from "./fixtures";

function renderList(cards: Parameters<typeof MetaDeckCardList>[0]["cards"]) {
  return render(
    <MemoryRouter>
      <MetaDeckCardList cards={cards} />
    </MemoryRouter>,
  );
}

describe("MetaDeckCardList", () => {
  it("groups cards by board in commander → main → side order", () => {
    renderList([
      makeCard({ name: "Pyroblast", board: "side", quantity: 2 }),
      makeCard({ name: "Lightning Bolt", board: "main" }),
      makeCard({ name: "Atraxa", board: "commander", quantity: 1 }),
    ]);
    const sections = screen.getByTestId("meta-card-list").querySelectorAll("section");
    expect([...sections].map((s) => s.getAttribute("data-testid"))).toEqual([
      "meta-board-commander",
      "meta-board-main",
      "meta-board-side",
    ]);
    expect(within(screen.getByTestId("meta-board-side")).getByText("Pyroblast")).toBeInTheDocument();
  });

  it("links to /cards/:id only when card_id exists", () => {
    renderList([
      makeCard({ name: "Linked", card_id: 42 }),
      makeCard({ name: "Unlinked", card_id: null }),
    ]);
    const links = screen.getAllByTestId("meta-card-link");
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "/cards/42");
    expect(links[0]).toHaveTextContent("Linked");
  });

  it("shows price, ✓ for fully owned and x/y for partially owned", () => {
    renderList([
      makeCard({ name: "A", quantity: 4, owned_qty: 4, price_brl: 5 }),
      makeCard({ name: "B", quantity: 4, owned_qty: 1, price_brl: null }),
      makeCard({ name: "C", quantity: 2, owned_qty: null }),
    ]);
    const owned = screen.getAllByTestId("meta-card-owned");
    expect(owned).toHaveLength(2);
    expect(owned[0]).toHaveTextContent("✓");
    expect(owned[1]).toHaveTextContent("1/4");
    const prices = screen.getAllByTestId("meta-card-price");
    expect(prices[0].textContent).toMatch(/R\$\s*5,00/);
    expect(prices[1]).toHaveTextContent("—");
  });

  it("renders an empty message when there are no cards", () => {
    renderList([]);
    expect(screen.getByTestId("meta-card-list-empty")).toBeInTheDocument();
  });
});
