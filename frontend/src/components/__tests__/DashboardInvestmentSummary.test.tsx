import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DashboardInvestmentSummary } from "../DashboardInvestmentSummary";
import type { PortfolioSummary } from "../../types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        "dashboard.investmentTitle": "Investment",
        "dashboard.investmentProgress": "{{count}} of {{total}} cards with paid price",
        "dashboard.investmentEmptyTitle": "Track your collection's appreciation",
        "dashboard.investmentEmptyDesc":
          "Set the paid price on your cards to see invested value and P&L.",
        "dashboard.investmentEmptyCta": "Go to collection",
        "dashboard.investmentUnpriced": "{{count}} cards without current price (excluded from P&L)",
        "dashboard.investmentError": "Could not load investment data",
        "dashboard.cardsWithoutAcquisition": "{{count}} cards without acquisition price",
        "portfolio.totalInvested": "Total Invested",
        "portfolio.currentValue": "Current Value",
        "portfolio.totalPnl": "Total P&L",
        "portfolio.pnlPct": "P&L %",
      };
      let str = translations[key] || key;
      if (opts) {
        Object.entries(opts).forEach(([k, v]) => {
          str = str.replace(`{{${k}}}`, String(v));
        });
      }
      return str;
    },
    i18n: { language: "en" },
  }),
}));

vi.mock("../CurrencyIndicator", () => ({
  CurrencyIndicator: ({ currency }: { currency: string }) => (
    <span data-testid={`currency-indicator-${currency.toLowerCase()}`} />
  ),
}));

vi.mock("../KpiCard", () => ({
  KpiCard: ({ title, value }: { title: string; value: React.ReactNode }) => (
    <div data-testid="kpi-card">
      <span>{title}</span>
      <span>{value}</span>
    </div>
  ),
}));

vi.mock("../Skeleton", () => ({
  SkeletonKpi: () => <div data-testid="skeleton-kpi" />,
}));

vi.mock("../../utils/format", () => ({
  formatCurrency: (v: number) => `R$ ${v.toFixed(2)}`,
}));

// Mock recharts to avoid rendering issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
}));

const mockFetchPortfolioSummary = vi.fn();
const mockFetchPortfolioHistory = vi.fn();
vi.mock("../../api/collection", () => ({
  fetchPortfolioSummary: () => mockFetchPortfolioSummary(),
  fetchPortfolioHistory: (days: number) => mockFetchPortfolioHistory(days),
}));

function renderComponent(totalUnique = 10) {
  return render(
    <MemoryRouter>
      <DashboardInvestmentSummary totalUnique={totalUnique} />
    </MemoryRouter>,
  );
}

function makeSummary(overrides: Partial<PortfolioSummary> = {}): PortfolioSummary {
  return {
    total_invested: 100,
    total_current_value: 150,
    total_pnl: 50,
    total_pnl_pct: 50,
    invested_card_count: 5,
    cards_without_acquisition: 0,
    ...overrides,
  };
}

describe("DashboardInvestmentSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default: history resolves with empty data
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });
  });

  it("shows loading skeletons initially", () => {
    mockFetchPortfolioSummary.mockReturnValue(new Promise(() => {}));
    mockFetchPortfolioHistory.mockReturnValue(new Promise(() => {}));
    renderComponent();
    expect(screen.getAllByTestId("skeleton-kpi")).toHaveLength(4);
  });

  it("shows sparkline skeleton while loading", () => {
    mockFetchPortfolioSummary.mockReturnValue(new Promise(() => {}));
    mockFetchPortfolioHistory.mockReturnValue(new Promise(() => {}));
    renderComponent();
    expect(screen.getByTestId("sparkline-skeleton")).toBeInTheDocument();
  });

  it("renders KPIs and progress bar on success", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: makeSummary(), errors: [] });
    renderComponent(10);
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.getAllByTestId("kpi-card")).toHaveLength(4);
    const progress = screen.getByTestId("dashboard-investment-progress");
    expect(progress).toHaveAttribute("aria-valuenow", "50");
    expect(progress).toHaveAttribute("aria-valuemin", "0");
    expect(progress).toHaveAttribute("aria-valuemax", "100");
    expect(screen.getByText("+R$ 50.00")).toHaveClass("text-emerald-400");
  });

  it("shows red P&L for negative values", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ total_pnl: -20, total_pnl_pct: -20 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.getByText("R$ -20.00")).toHaveClass("text-red-400");
  });

  it("shows neutral P&L for zero", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ total_pnl: 0, total_pnl_pct: 0 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.getByText("R$ 0.00")).not.toHaveClass("text-emerald-400");
    expect(screen.getByText("R$ 0.00")).not.toHaveClass("text-red-400");
  });

  it("shows CTA when invested_card_count is 0", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ invested_card_count: 0 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-empty")).toBeInTheDocument());
    const link = screen.getByText("Go to collection").closest("a");
    expect(link).toHaveAttribute("href", "/collection");
    expect(screen.queryByTestId("kpi-card")).not.toBeInTheDocument();
  });

  it("shows inline error on API error response, no throw", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: null,
      errors: [{ message: "boom" }],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-error")).toBeInTheDocument());
  });

  it("shows inline error when the fetch promise rejects, no throw", async () => {
    mockFetchPortfolioSummary.mockRejectedValue(new Error("network down"));
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-error")).toBeInTheDocument());
  });

  it("clamps progress to 0 when totalUnique is 0", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: makeSummary(), errors: [] });
    renderComponent(0);
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.getByTestId("dashboard-investment-progress")).toHaveAttribute("aria-valuenow", "0");
  });

  it("clamps progress to 100 when invested_card_count exceeds totalUnique", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ invested_card_count: 20 }),
      errors: [],
    });
    renderComponent(10);
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.getByTestId("dashboard-investment-progress")).toHaveAttribute("aria-valuenow", "100");
  });

  it("does not show unpriced hint when unpriced_card_count is undefined", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: makeSummary(), errors: [] });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.queryByTestId("dashboard-investment-unpriced")).not.toBeInTheDocument();
  });

  it("shows unpriced hint with count when unpriced_card_count > 0", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ unpriced_card_count: 3 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-unpriced")).toBeInTheDocument());
    expect(screen.getByTestId("dashboard-investment-unpriced")).toHaveTextContent("3 cards without current price");
  });

  // --- F136 new tests ---

  it("renders P&L sparkline when portfolio history has > 1 data points", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: makeSummary(), errors: [] });
    mockFetchPortfolioHistory.mockResolvedValue({
      data: [
        { date: "2026-09-01", value: 100 },
        { date: "2026-09-02", value: 110 },
        { date: "2026-09-03", value: 120 },
      ],
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("pnl-sparkline")).toBeInTheDocument());
  });

  it("hides sparkline when history has 0-1 data points", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: makeSummary(), errors: [] });
    mockFetchPortfolioHistory.mockResolvedValue({
      data: [{ date: "2026-09-01", value: 100 }],
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.queryByTestId("pnl-sparkline")).not.toBeInTheDocument();
  });

  it("shows missing-price alert when cards_without_acquisition > 0", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ cards_without_acquisition: 7 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("missing-acquisition-alert")).toBeInTheDocument());
    expect(screen.getByTestId("missing-acquisition-alert")).toHaveTextContent("7 cards without acquisition price");
  });

  it("alert links to /collection?has_acquisition_price=false", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ cards_without_acquisition: 3 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("missing-acquisition-alert")).toBeInTheDocument());
    const alert = screen.getByTestId("missing-acquisition-alert");
    expect(alert).toHaveAttribute("href", "/collection?has_acquisition_price=false");
  });

  it("hides alert when cards_without_acquisition is 0", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ cards_without_acquisition: 0 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    expect(screen.queryByTestId("missing-acquisition-alert")).not.toBeInTheDocument();
  });

  it("shows alert even when invested_card_count is 0 (empty state)", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ invested_card_count: 0, cards_without_acquisition: 5 }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("missing-acquisition-alert")).toBeInTheDocument());
    expect(screen.getByTestId("missing-acquisition-alert")).toHaveTextContent("5 cards without acquisition price");
  });

  it("error fetching history does not crash KPI section", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: makeSummary(), errors: [] });
    mockFetchPortfolioHistory.mockRejectedValue(new Error("history error"));
    renderComponent();
    await waitFor(() => expect(screen.getByTestId("dashboard-investment-progress")).toBeInTheDocument());
    // KPIs still render
    expect(screen.getAllByTestId("kpi-card")).toHaveLength(4);
    // sparkline not shown
    expect(screen.queryByTestId("pnl-sparkline")).not.toBeInTheDocument();
  });
});
