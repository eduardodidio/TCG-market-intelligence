import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MoversTable } from "../../src/components/MoversTable";
import { mockMoversResponse } from "../fixtures/api-responses";

function renderMoversTable(
  type: "gainers" | "losers",
  overrides?: { entries?: Parameters<typeof MoversTable>[0]["entries"] },
) {
  const moversData = mockMoversResponse().data!;
  const entries = overrides?.entries ?? (type === "gainers" ? moversData.gainers : moversData.losers);
  const title = type === "gainers" ? "Top Gainers" : "Top Losers";

  return render(
    <MemoryRouter>
      <MoversTable entries={entries} title={title} type={type} />
    </MemoryRouter>,
  );
}

describe("MoversTable", () => {
  it("renders gainers entries with rank, card name, and formatted change", () => {
    renderMoversTable("gainers");

    // Title
    expect(screen.getByText("Top Gainers")).toBeDefined();

    // Card names from fixture
    expect(screen.getByText("Card Gainer 1")).toBeDefined();
    expect(screen.getByText("Card Gainer 2")).toBeDefined();
    expect(screen.getByText("Card Gainer 5")).toBeDefined();

    // Rank numbers (1-5)
    expect(screen.getByText("1")).toBeDefined();
    expect(screen.getByText("5")).toBeDefined();
  });

  it("renders losers entries with card names", () => {
    renderMoversTable("losers");

    expect(screen.getByText("Top Losers")).toBeDefined();
    expect(screen.getByText("Card Loser 1")).toBeDefined();
    expect(screen.getByText("Card Loser 3")).toBeDefined();
  });

  it("renders card names as links to card detail page", () => {
    renderMoversTable("gainers");

    const link = screen.getByText("Card Gainer 1").closest("a");
    expect(link).not.toBeNull();
    expect(link!.getAttribute("href")).toBe("/cards/100");
  });

  it("renders set code next to card name", () => {
    renderMoversTable("gainers");

    // All fixture entries have set_code "DMR"
    const dmrLabels = screen.getAllByText("DMR");
    expect(dmrLabels.length).toBeGreaterThanOrEqual(5);
  });

  it("formats prices using BRL format", () => {
    renderMoversTable("gainers");

    // price_start is 10 for all fixture entries
    const priceElements = screen.getAllByText(/R\$/);
    expect(priceElements.length).toBeGreaterThanOrEqual(1);
  });

  it("formats change percentage with sign", () => {
    renderMoversTable("gainers");

    // First gainer has change_pct = 10, formatted as "+10,0%"
    expect(screen.getByText("+10,0%")).toBeDefined();
  });

  it("applies green styling for gainers type", () => {
    renderMoversTable("gainers");

    const table = screen.getByTestId("movers-table-gainers");
    expect(table).toBeDefined();

    // Title should have green class
    const title = screen.getByText("Top Gainers");
    expect(title.className).toContain("text-tcg-gain");
  });

  it("applies red styling for losers type", () => {
    renderMoversTable("losers");

    const table = screen.getByTestId("movers-table-losers");
    expect(table).toBeDefined();

    // Title should have red class
    const title = screen.getByText("Top Losers");
    expect(title.className).toContain("text-tcg-loss");
  });

  it("renders change percentage with green class for gainers", () => {
    renderMoversTable("gainers");

    const changeCell = screen.getByText("+10,0%");
    expect(changeCell.className).toContain("text-tcg-gain");
    expect(changeCell.className).toContain("font-bold");
  });

  it("renders change percentage with red class for losers", () => {
    renderMoversTable("losers");

    const changeCell = screen.getByText("-10,0%");
    expect(changeCell.className).toContain("text-tcg-loss");
    expect(changeCell.className).toContain("font-bold");
  });

  it("renders empty table body when entries array is empty", () => {
    renderMoversTable("gainers", { entries: [] });

    expect(screen.getByText("Top Gainers")).toBeDefined();
    // Table header exists but no data rows
    expect(screen.getByText("#")).toBeDefined();
    expect(screen.queryByText("Card Gainer 1")).toBeNull();
  });
});
