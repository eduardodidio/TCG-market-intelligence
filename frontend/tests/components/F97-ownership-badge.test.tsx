import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TrendingListItem } from "../../src/components/TrendingListItem";
import { TrendingCard } from "../../src/components/TrendingCard";
import type { TrendingCardEntry } from "../../src/types/api";

function makeTrendingEntry(overrides?: Partial<TrendingCardEntry>): TrendingCardEntry {
  return {
    card_id: 42,
    name_en: "Lightning Bolt",
    name_pt: null,
    set_code: "lea",
    collector_number: "161",
    image_url: null,
    price_start: 10,
    price_end: 15,
    change_pct: 50,
    change_abs: 5,
    consistency: 0.9,
    composite_score: 75,
    observation_count: 5,
    currency: "BRL",
    ...overrides,
  };
}

function wrap(component: React.ReactNode) {
  return render(
    <MemoryRouter>
      {component}
    </MemoryRouter>,
  );
}

describe("F97-T03: Ownership badge on TrendingListItem", () => {
  it("shows owned-badge when card_id is in ownedCardIds", () => {
    const entry = makeTrendingEntry({ card_id: 42 });
    const owned = new Set([42]);
    wrap(<TrendingListItem entry={entry} ownedCardIds={owned} />);
    expect(screen.getByTestId("owned-badge")).toBeDefined();
  });

  it("does not show owned-badge when card_id is NOT in ownedCardIds", () => {
    const entry = makeTrendingEntry({ card_id: 42 });
    const owned = new Set([99]);
    wrap(<TrendingListItem entry={entry} ownedCardIds={owned} />);
    expect(screen.queryByTestId("owned-badge")).toBeNull();
  });

  it("does not show owned-badge when ownedCardIds is undefined", () => {
    const entry = makeTrendingEntry({ card_id: 42 });
    wrap(<TrendingListItem entry={entry} />);
    expect(screen.queryByTestId("owned-badge")).toBeNull();
  });

  it("does not show owned-badge when ownedCardIds is empty Set", () => {
    const entry = makeTrendingEntry({ card_id: 42 });
    wrap(<TrendingListItem entry={entry} ownedCardIds={new Set()} />);
    expect(screen.queryByTestId("owned-badge")).toBeNull();
  });
});

describe("F97-T03: Ownership badge on TrendingCard", () => {
  it("shows owned-badge when card_id is in ownedCardIds", () => {
    const entry = makeTrendingEntry({ card_id: 42 });
    const owned = new Set([42]);
    wrap(<TrendingCard entry={entry} ownedCardIds={owned} />);
    expect(screen.getByTestId("owned-badge")).toBeDefined();
  });

  it("does not show owned-badge when card_id is NOT in ownedCardIds", () => {
    const entry = makeTrendingEntry({ card_id: 42 });
    const owned = new Set([99]);
    wrap(<TrendingCard entry={entry} ownedCardIds={owned} />);
    expect(screen.queryByTestId("owned-badge")).toBeNull();
  });

  it("does not show owned-badge when ownedCardIds is undefined", () => {
    const entry = makeTrendingEntry({ card_id: 42 });
    wrap(<TrendingCard entry={entry} />);
    expect(screen.queryByTestId("owned-badge")).toBeNull();
  });
});
