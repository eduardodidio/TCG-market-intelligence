import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TrendingCard } from "../../src/components/TrendingCard";
import type { TrendingCardEntry } from "../../src/types/api";

function mockEntry(overrides?: Partial<TrendingCardEntry>): TrendingCardEntry {
  return {
    card_id: 1,
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "lea",
    collector_number: "161",
    image_url: "https://api.scryfall.com/cards/lea/161?format=image&version=normal",
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

function renderCard(entry: TrendingCardEntry) {
  return render(
    <MemoryRouter>
      <TrendingCard entry={entry} />
    </MemoryRouter>,
  );
}

describe("TrendingCard", () => {
  it("renders card name", () => {
    renderCard(mockEntry());
    expect(screen.getByText("Lightning Bolt")).toBeTruthy();
  });

  it("renders set code", () => {
    renderCard(mockEntry());
    expect(screen.getByText("lea")).toBeTruthy();
  });

  it("shows positive change percentage", () => {
    renderCard(mockEntry());
    expect(screen.getByText("+50.0%")).toBeTruthy();
  });

  it("shows negative change percentage", () => {
    renderCard(mockEntry({ change_pct: -12.5, change_abs: -2.5 }));
    expect(screen.getByText("-12.5%")).toBeTruthy();
  });

  it("shows green arrow for positive change", () => {
    renderCard(mockEntry());
    const arrow = screen.getByText("\u2191");
    expect(arrow.closest("div")).toHaveClass("text-green-400");
  });

  it("shows red arrow for negative change", () => {
    renderCard(mockEntry({ change_pct: -10, change_abs: -1 }));
    const arrow = screen.getByText("\u2193");
    expect(arrow.closest("div")).toHaveClass("text-red-400");
  });

  it("renders composite score bar", () => {
    renderCard(mockEntry());
    expect(screen.getByTestId("score-bar")).toBeTruthy();
  });

  it("links to card detail page", () => {
    renderCard(mockEntry());
    const link = screen.getByTestId("trending-card");
    expect(link).toHaveAttribute("href", "/cards/1");
  });

  it("handles missing image gracefully", () => {
    renderCard(mockEntry({ image_url: null }));
    expect(screen.getByText("No Image")).toBeTruthy();
  });

  it("handles missing set_code gracefully", () => {
    renderCard(mockEntry({ set_code: null }));
    expect(screen.queryByText("lea")).toBeNull();
  });
});
