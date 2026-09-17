import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PortfolioDashboard } from "../PortfolioDashboard";
import type { PortfolioSummary } from "../../types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));

vi.mock("../../utils/format", () => ({
  formatCurrency: (v: number) => `R$ ${v.toFixed(2)}`,
}));

vi.mock("../KpiCard", () => ({
  KpiCard: ({ title, value }: { title: string; value: React.ReactNode }) => (
    <div data-testid="kpi-card">
      <span>{title}</span>
      <span>{value}</span>
    </div>
  ),
}));

// Mock recharts
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  CartesianGrid: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
}));

const mockFetchPortfolioSummary = vi.fn();
const mockFetchPortfolioHistory = vi.fn();
vi.mock("../../api/collection", () => ({
  fetchPortfolioSummary: () => mockFetchPortfolioSummary(),
  fetchPortfolioHistory: (days: number) => mockFetchPortfolioHistory(days),
  exportPnlCsv: vi.fn(),
}));

// Capture CollectionMovers props
let capturedMoversProps: Record<string, unknown> | null = null;
vi.mock("../CollectionMovers", () => ({
  CollectionMovers: (props: Record<string, unknown>) => {
    capturedMoversProps = props;
    return <div data-testid="collection-movers-mock" />;
  },
}));

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

describe("PortfolioDashboard consistency audit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedMoversProps = null;
    // Ensure localStorage says visible
    localStorage.setItem("portfolio_dashboard_visible", "true");
  });

  it("renders CollectionMovers with investmentOnly=true", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: makeSummary(), errors: [] });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });

    render(<PortfolioDashboard />);

    await waitFor(() => expect(screen.getByTestId("collection-movers-mock")).toBeInTheDocument());
    expect(capturedMoversProps).not.toBeNull();
    expect(capturedMoversProps!.investmentOnly).toBe(true);
  });

  it("does not render movers when invested_card_count is 0", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: makeSummary({ invested_card_count: 0 }),
      errors: [],
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      const noData = screen.getByText("portfolio.noInvestmentData");
      expect(noData).toBeInTheDocument();
    });
    expect(screen.queryByTestId("collection-movers-mock")).not.toBeInTheDocument();
  });
});
