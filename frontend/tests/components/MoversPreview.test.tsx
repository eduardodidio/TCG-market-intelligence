import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MoversPreview } from "../../src/components/MoversPreview";
import { mockMoversResponse } from "../fixtures/api-responses";

function renderMoversPreview() {
  const data = mockMoversResponse().data!;
  return render(
    <MemoryRouter>
      <MoversPreview gainers={data.gainers} losers={data.losers} />
    </MemoryRouter>,
  );
}

describe("MoversPreview", () => {
  it("renders gainers list", () => {
    renderMoversPreview();

    expect(screen.getByText("Top Gainers")).toBeDefined();
    expect(screen.getByText("Card Gainer 1")).toBeDefined();
    expect(screen.getByText("Card Gainer 5")).toBeDefined();
  });

  it("renders losers list", () => {
    renderMoversPreview();

    expect(screen.getByText("Top Losers")).toBeDefined();
    expect(screen.getByText("Card Loser 1")).toBeDefined();
    expect(screen.getByText("Card Loser 5")).toBeDefined();
  });

  it("renders card name links to correct URLs", () => {
    renderMoversPreview();

    const gainer1Link = screen.getByText("Card Gainer 1").closest("a");
    expect(gainer1Link?.getAttribute("href")).toBe("/cards/100");

    const loser1Link = screen.getByText("Card Loser 1").closest("a");
    expect(loser1Link?.getAttribute("href")).toBe("/cards/100");
  });

  it("renders set code badges", () => {
    renderMoversPreview();

    const badges = screen.getAllByText("DMR");
    expect(badges.length).toBeGreaterThanOrEqual(2);
  });

  it("renders 'View all' links pointing to /market/movers", () => {
    renderMoversPreview();

    const viewAllLinks = screen.getAllByText("View all");
    expect(viewAllLinks).toHaveLength(2);

    for (const link of viewAllLinks) {
      expect(link.closest("a")?.getAttribute("href")).toBe("/market/movers");
    }
  });

  it("renders percentage changes with correct formatting", () => {
    renderMoversPreview();

    // First gainer: change_pct = 10 -> "+10,0%"
    expect(screen.getByText("+10,0%")).toBeDefined();

    // First loser: change_pct = -10 -> "-10,0%"
    expect(screen.getByText("-10,0%")).toBeDefined();
  });

  it("applies correct data-testid", () => {
    renderMoversPreview();

    expect(screen.getByTestId("movers-preview")).toBeDefined();
  });
});
