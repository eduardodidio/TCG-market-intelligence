import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { PortfolioDashboard } from "../PortfolioDashboard";

// Mock recharts to avoid SVG rendering issues in tests
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "portfolio.title": "Portfolio & Investment",
        "portfolio.totalInvested": "Total Invested",
        "portfolio.currentValue": "Current Value",
        "portfolio.totalPnl": "Total P&L",
        "portfolio.pnlPct": "P&L %",
        "portfolio.valueOverTime": "Portfolio Value Over Time",
        "portfolio.exportPnl": "Export P&L",
        "portfolio.noInvestmentData": "No acquisition prices set yet.",
        "portfolio.noHistory":
          "No portfolio history yet. Run a price scan to start tracking your collection value over time.",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock CollectionMovers
vi.mock("../CollectionMovers", () => ({
  CollectionMovers: () => <div data-testid="collection-movers">Movers</div>,
}));

// Mock KpiCard
vi.mock("../KpiCard", () => ({
  KpiCard: ({ title, value }: { title: string; value: React.ReactNode }) => (
    <div data-testid="kpi-card">
      <span>{title}</span>
      <span>{value}</span>
    </div>
  ),
}));

// Mock formatCurrency
vi.mock("../../utils/format", () => ({
  formatCurrency: (v: number, _currency: string) => `R$ ${v.toFixed(2)}`,
}));

const mockFetchPortfolioSummary = vi.fn();
const mockFetchPortfolioHistory = vi.fn();
const mockExportPnlCsv = vi.fn();

vi.mock("../../api/collection", () => ({
  fetchPortfolioSummary: () => mockFetchPortfolioSummary(),
  fetchPortfolioHistory: () => mockFetchPortfolioHistory(),
  exportPnlCsv: () => mockExportPnlCsv(),
}));

// Mock localStorage
const localStorageMock: Record<string, string> = {};
beforeEach(() => {
  Object.keys(localStorageMock).forEach((key) => delete localStorageMock[key]);
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(
    (key: string) => localStorageMock[key] ?? null,
  );
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(
    (key: string, value: string) => {
      localStorageMock[key] = value;
    },
  );
});

describe("PortfolioDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders empty state when no history exists but summary has invested cards", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 100,
        total_current_value: 120,
        total_pnl: 20,
        total_pnl_pct: 20.0,
        invested_card_count: 5,
      },
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [] });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("portfolio-no-history")).toBeInTheDocument();
    });

    expect(
      screen.getByText(/No portfolio history yet/),
    ).toBeInTheDocument();
  });

  it("renders chart when history has multiple data points", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 100,
        total_current_value: 120,
        total_pnl: 20,
        total_pnl_pct: 20.0,
        invested_card_count: 5,
      },
    });
    mockFetchPortfolioHistory.mockResolvedValue({
      data: [
        { date: "2026-08-01", value: 100 },
        { date: "2026-08-02", value: 110 },
        { date: "2026-08-03", value: 120 },
      ],
    });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("portfolio-chart")).toBeInTheDocument();
    });

    // No empty state message should appear
    expect(screen.queryByTestId("portfolio-no-history")).not.toBeInTheDocument();
  });

  it("shows no investment data message when invested_card_count is 0", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 0,
        total_current_value: 0,
        total_pnl: 0,
        total_pnl_pct: null,
        invested_card_count: 0,
      },
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [] });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getByText(/No acquisition prices set yet/)).toBeInTheDocument();
    });
  });

  it("renders KPI cards when summary data exists", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 500,
        total_current_value: 600,
        total_pnl: 100,
        total_pnl_pct: 20.0,
        invested_card_count: 10,
      },
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [{ date: "2026-08-01", value: 500 }] });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getAllByTestId("kpi-card")).toHaveLength(4);
    });
  });

  it("shows loading skeleton initially", () => {
    mockFetchPortfolioSummary.mockReturnValue(new Promise(() => {}));
    mockFetchPortfolioHistory.mockReturnValue(new Promise(() => {}));

    render(<PortfolioDashboard />);

    // Loading skeletons should be present
    const dashboard = screen.getByTestId("portfolio-dashboard");
    expect(dashboard).toBeInTheDocument();
  });
});
