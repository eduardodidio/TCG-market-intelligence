import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { MarketSummaryKpis } from "../../src/components/MarketSummaryKpis";
import type { MarketSummaryResponse } from "../../src/types/api";

function makeSummaryData(
  overrides?: Partial<MarketSummaryResponse>,
): MarketSummaryResponse {
  return {
    total_cards_tracked: 150,
    total_observations: 500,
    avg_price: 12.5,
    avg_price_change_pct: 3.75,
    gainers_count: 80,
    losers_count: 50,
    unchanged_count: 20,
    market_direction: "up",
    period: "30d",
    currency: "BRL",
    computed_at: "2026-08-22T12:00:00",
    ...overrides,
  };
}

describe("MarketSummaryKpis", () => {
  it("renders 5 KPI cards when data is provided", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData()}
        loading={false}
        currency="BRL"
      />,
    );

    const kpiCards = screen.getAllByTestId("kpi-card");
    expect(kpiCards).toHaveLength(5);
  });

  it("renders data-testid market-summary-kpis when not loading", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData()}
        loading={false}
        currency="BRL"
      />,
    );

    expect(screen.getByTestId("market-summary-kpis")).toBeDefined();
  });

  it("shows 5 skeleton KPIs when loading", () => {
    render(
      <MarketSummaryKpis data={null} loading={true} currency="BRL" />,
    );

    expect(screen.getByTestId("market-summary-loading")).toBeDefined();
    const skeletons = screen.getAllByTestId("skeleton-kpi");
    expect(skeletons).toHaveLength(5);
  });

  it("shows dashes when data is null", () => {
    render(
      <MarketSummaryKpis data={null} loading={false} currency="BRL" />,
    );

    // avg_price is null -> formatCurrency returns "--"
    // avg_price_change_pct is null -> shows "--"
    const dashes = screen.getAllByText("--");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it("shows dashes for null avg_price_change_pct", () => {
    const data = makeSummaryData({ avg_price_change_pct: null });
    render(
      <MarketSummaryKpis data={data} loading={false} currency="BRL" />,
    );

    const dashes = screen.getAllByText("--");
    expect(dashes.length).toBeGreaterThanOrEqual(1);
  });

  it("direction badge has green color for 'up' direction", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ market_direction: "up" })}
        loading={false}
        currency="BRL"
      />,
    );

    const badge = screen.getByText("Bullish");
    expect(badge).toHaveClass("bg-emerald-500/20");
    expect(badge).toHaveClass("text-emerald-400");
  });

  it("direction badge has red color for 'down' direction", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ market_direction: "down" })}
        loading={false}
        currency="BRL"
      />,
    );

    const badge = screen.getByText("Bearish");
    expect(badge).toHaveClass("bg-red-500/20");
    expect(badge).toHaveClass("text-red-400");
  });

  it("direction badge has gray color for 'flat' direction", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ market_direction: "flat" })}
        loading={false}
        currency="BRL"
      />,
    );

    const badge = screen.getByText("Flat");
    expect(badge).toHaveClass("bg-slate-500/20");
    expect(badge).toHaveClass("text-slate-400");
  });

  it("shows cards tracked count", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ total_cards_tracked: 42 })}
        loading={false}
        currency="BRL"
      />,
    );

    expect(screen.getByText("42")).toBeDefined();
  });

  it("shows positive avg change with + sign", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ avg_price_change_pct: 5.25 })}
        loading={false}
        currency="BRL"
      />,
    );

    expect(screen.getByText("+5.25%")).toBeDefined();
  });

  it("shows negative avg change without + sign", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ avg_price_change_pct: -2.5 })}
        loading={false}
        currency="BRL"
      />,
    );

    expect(screen.getByText("-2.50%")).toBeDefined();
  });

  it("computes gainers ratio correctly", () => {
    // 80 gainers out of 80+20 = 100 total -> 80%
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ gainers_count: 80, losers_count: 20 })}
        loading={false}
        currency="BRL"
      />,
    );

    expect(screen.getByText("80%")).toBeDefined();
  });

  it("gainers ratio is 0% when no movers", () => {
    render(
      <MarketSummaryKpis
        data={makeSummaryData({ gainers_count: 0, losers_count: 0 })}
        loading={false}
        currency="BRL"
      />,
    );

    expect(screen.getByText("0%")).toBeDefined();
  });
});
