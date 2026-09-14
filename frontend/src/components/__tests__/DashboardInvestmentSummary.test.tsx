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

const mockFetchPortfolioSummary = vi.fn();
vi.mock("../../api/collection", () => ({
  fetchPortfolioSummary: () => mockFetchPortfolioSummary(),
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
    ...overrides,
  };
}

describe("DashboardInvestmentSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading skeletons initially", () => {
    mockFetchPortfolioSummary.mockReturnValue(new Promise(() => {}));
    renderComponent();
    expect(screen.getAllByTestId("skeleton-kpi")).toHaveLength(4);
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

  it("shows '—' when total_pnl_pct is null", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ total_pnl_pct: null }),
      errors: [],
    });
    renderComponent();
    await waitFor(() => expect(screen.getByText("—")).toBeInTheDocument());
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
});
