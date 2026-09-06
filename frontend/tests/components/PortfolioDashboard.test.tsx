import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { PortfolioDashboard } from "../../src/components/PortfolioDashboard";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "portfolio.title": "Portfolio & Investment",
        "portfolio.totalInvested": "Total Invested",
        "portfolio.currentValue": "Current Value",
        "portfolio.totalPnl": "Total P&L",
        "portfolio.pnlPct": "P&L %",
        "portfolio.valueOverTime": "Portfolio Value Over Time",
        "portfolio.exportPnl": "Export P&L",
        "portfolio.noInvestmentData": "No acquisition prices set yet.",
      };
      return map[key] || key;
    },
  }),
}));

vi.mock("../../src/utils/format", () => ({
  formatCurrency: (value: number | null, _currency: string) => {
    if (value == null) return "--";
    return `R$ ${value.toFixed(2)}`;
  },
}));

// Mock recharts to avoid DOM rendering issues
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));

const mockFetchPortfolioSummary = vi.fn();
const mockFetchPortfolioHistory = vi.fn();
const mockExportPnlCsv = vi.fn();

vi.mock("../../src/api/collection", () => ({
  fetchPortfolioSummary: (...args: unknown[]) => mockFetchPortfolioSummary(...args),
  fetchPortfolioHistory: (...args: unknown[]) => mockFetchPortfolioHistory(...args),
  exportPnlCsv: (...args: unknown[]) => mockExportPnlCsv(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe("PortfolioDashboard", () => {
  it("renders toggle button", () => {
    mockFetchPortfolioSummary.mockResolvedValue({ data: null, errors: [] });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });

    render(<PortfolioDashboard />);
    expect(screen.getByTestId("portfolio-toggle")).toBeInTheDocument();
    expect(screen.getByText("Portfolio & Investment")).toBeInTheDocument();
  });

  it("shows no investment data message when no entries", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 0,
        total_current_value: 0,
        total_pnl: 0,
        total_pnl_pct: null,
        invested_card_count: 0,
      },
      errors: [],
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getByText("No acquisition prices set yet.")).toBeInTheDocument();
    });
  });

  it("shows KPI cards when data is available", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 100.0,
        total_current_value: 150.0,
        total_pnl: 50.0,
        total_pnl_pct: 50.0,
        invested_card_count: 5,
      },
      errors: [],
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getByText("Total Invested")).toBeInTheDocument();
      expect(screen.getByText("Current Value")).toBeInTheDocument();
      expect(screen.getByText("Total P&L")).toBeInTheDocument();
      expect(screen.getByText("P&L %")).toBeInTheDocument();
    });
  });

  it("shows export button when data is available", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 100.0,
        total_current_value: 150.0,
        total_pnl: 50.0,
        total_pnl_pct: 50.0,
        invested_card_count: 5,
      },
      errors: [],
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });

    render(<PortfolioDashboard />);

    await waitFor(() => {
      expect(screen.getByTestId("export-pnl-btn")).toBeInTheDocument();
    });
  });

  it("toggles visibility and persists in localStorage", async () => {
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 100.0,
        total_current_value: 150.0,
        total_pnl: 50.0,
        total_pnl_pct: 50.0,
        invested_card_count: 5,
      },
      errors: [],
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [], errors: [] });

    render(<PortfolioDashboard />);

    // Initially visible
    await waitFor(() => {
      expect(screen.getByText("Total Invested")).toBeInTheDocument();
    });

    // Toggle off
    fireEvent.click(screen.getByTestId("portfolio-toggle"));
    expect(localStorage.getItem("portfolio_dashboard_visible")).toBe("false");
    expect(screen.queryByText("Total Invested")).not.toBeInTheDocument();

    // Toggle on
    fireEvent.click(screen.getByTestId("portfolio-toggle"));
    expect(localStorage.getItem("portfolio_dashboard_visible")).toBe("true");
  });
});
