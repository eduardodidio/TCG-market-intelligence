import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TrendingListItem } from "../../src/components/TrendingListItem";
import type { TrendingCardEntry } from "../../src/types/api";

function mockEntry(overrides?: Partial<TrendingCardEntry>): TrendingCardEntry {
  return {
    card_id: 42,
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "lea",
    collector_number: "161",
    image_url: null,
    price_start: 10.0,
    price_end: 15.0,
    change_pct: 50.0,
    change_abs: 5.0,
    consistency: 0.9,
    composite_score: 75.0,
    observation_count: 5,
    currency: "BRL",
    ...overrides,
  };
}

function renderItem(entry: TrendingCardEntry) {
  return render(
    <MemoryRouter>
      <TrendingListItem entry={entry} />
    </MemoryRouter>,
  );
}

describe("TrendingListItem", () => {
  it("renders card name", () => {
    renderItem(mockEntry());
    expect(screen.getByText("Lightning Bolt")).toBeTruthy();
  });

  it("renders set code badge", () => {
    renderItem(mockEntry());
    expect(screen.getByText("lea")).toBeTruthy();
  });

  it("shows positive change percentage with green color", () => {
    renderItem(mockEntry());
    const change = screen.getByText("+50.0%");
    expect(change).toBeTruthy();
    expect(change).toHaveClass("text-green-400");
  });

  it("shows negative change percentage with red color", () => {
    renderItem(mockEntry({ change_pct: -12.5, change_abs: -2.5 }));
    const change = screen.getByText("-12.5%");
    expect(change).toBeTruthy();
    expect(change).toHaveClass("text-red-400");
  });

  it("renders current price in BRL", () => {
    renderItem(mockEntry());
    expect(screen.getByText("R$15.00")).toBeTruthy();
  });

  it("renders current price in USD", () => {
    renderItem(mockEntry({ price_end: 3.5, currency: "USD" }));
    expect(screen.getByText("$3.50")).toBeTruthy();
  });

  it("renders current price in PILA", () => {
    renderItem(mockEntry({ price_end: 230.0, currency: "PILA" }));
    expect(screen.getByText("230.00 pilas")).toBeTruthy();
  });

  it("links to card detail page", () => {
    renderItem(mockEntry());
    const link = screen.getByTestId("trending-list-item");
    expect(link).toHaveAttribute("href", "/cards/42");
  });

  it("handles missing set_code gracefully", () => {
    renderItem(mockEntry({ set_code: null }));
    expect(screen.queryByText("lea")).toBeNull();
    // Name and price should still render
    expect(screen.getByText("Lightning Bolt")).toBeTruthy();
    expect(screen.getByText("R$15.00")).toBeTruthy();
  });

  it("has hover styling class", () => {
    renderItem(mockEntry());
    const link = screen.getByTestId("trending-list-item");
    expect(link.className).toContain("hover:bg-slate-700/50");
  });
});
