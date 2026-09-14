import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Dashboard } from "../Dashboard";
import type { CollectionSummary } from "../../types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));

const mockUseAuth = vi.fn();
vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../hooks/useWelcome", () => ({
  useWelcome: () => ({ showWelcome: false, dismiss: vi.fn() }),
}));

vi.mock("../../hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: "BRL", setCurrency: vi.fn() }),
}));

const mockFetchCollectionSummary = vi.fn();
vi.mock("../../api/collection", () => ({
  fetchCollectionSummary: (...args: unknown[]) => mockFetchCollectionSummary(...args),
}));

const mockFetchCollectionHealth = vi.fn();
vi.mock("../../api/collect", () => ({
  fetchCollectionHealth: () => mockFetchCollectionHealth(),
}));

const mockFetchMarketStats = vi.fn();
vi.mock("../../api/market", () => ({
  fetchMarketStats: (...args: unknown[]) => mockFetchMarketStats(...args),
}));

vi.mock("../../components/TrendingSection", () => ({
  TrendingSection: ({ direction, collectionOnly }: { direction: string; collectionOnly: boolean }) => (
    <div data-testid={`trending-section-${direction}`} data-collection-only={String(collectionOnly)} />
  ),
}));

vi.mock("../../components/CollectionMovers", () => ({
  CollectionMovers: () => <div data-testid="collection-movers-stub" />,
}));

vi.mock("../../components/DashboardInvestmentSummary", () => ({
  DashboardInvestmentSummary: () => <div data-testid="dashboard-investment-stub" />,
}));

vi.mock("../../components/ValuationBadge", () => ({
  ValuationBadge: () => <div data-testid="valuation-badge-stub" />,
}));

vi.mock("../../components/WelcomeBanner", () => ({
  WelcomeBanner: () => <div data-testid="welcome-banner-stub" />,
}));

vi.mock("../../components/FreshnessIndicator", () => ({
  FreshnessIndicator: () => <div data-testid="freshness-indicator-stub" />,
}));

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

function makeSummary(overrides: Partial<CollectionSummary> = {}): CollectionSummary {
  return {
    total_unique: 5,
    total_cards: 10,
    sets_count: 2,
    linked_count: 5,
    priced_count: 5,
    total_value: 100,
    banned_count: 0,
    recently_changed_count: 0,
    ...overrides,
  } as CollectionSummary;
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: 1 } });
    mockFetchCollectionHealth.mockResolvedValue({
      data: { status: "healthy", last_collection_at: null },
      errors: [],
      meta: {},
    });
  });

  it("renders collection KPIs, investment summary, movers and trending for an authenticated user with a collection", async () => {
    mockFetchCollectionSummary.mockResolvedValue({ data: makeSummary(), errors: [], meta: {} });
    renderDashboard();

    await waitFor(() => expect(screen.getByTestId("collection-kpis")).toBeInTheDocument());
    expect(screen.getByTestId("dashboard-investment-stub")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-movers")).toBeInTheDocument();
    expect(screen.getByTestId("trending-section-gainers")).toBeInTheDocument();
    expect(screen.getByTestId("trending-section-losers")).toBeInTheDocument();
    expect(screen.getByTestId("trending-view-all")).toBeInTheDocument();

    expect(screen.queryByTestId("market-summary-strip")).not.toBeInTheDocument();
    expect(screen.queryByTestId("market-empty")).not.toBeInTheDocument();
    expect(mockFetchMarketStats).not.toHaveBeenCalled();
  });

  it("does not mount investment summary and passes collectionOnly=false for an anonymous user", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, user: null });
    mockFetchCollectionSummary.mockResolvedValue({ data: makeSummary(), errors: [], meta: {} });
    renderDashboard();

    await waitFor(() => expect(screen.getByTestId("collection-kpis")).toBeInTheDocument());
    expect(screen.queryByTestId("dashboard-investment-stub")).not.toBeInTheDocument();
    expect(screen.getByTestId("trending-section-gainers")).toHaveAttribute("data-collection-only", "false");
    expect(screen.getByTestId("trending-section-losers")).toHaveAttribute("data-collection-only", "false");
  });

  it("shows collection-empty state and no investment summary when total_unique is 0", async () => {
    mockFetchCollectionSummary.mockResolvedValue({
      data: makeSummary({ total_unique: 0 }),
      errors: [],
      meta: {},
    });
    renderDashboard();

    await waitFor(() => expect(screen.getByTestId("collection-empty")).toBeInTheDocument());
    expect(screen.queryByTestId("dashboard-investment-stub")).not.toBeInTheDocument();
    expect(screen.getByTestId("trending-section-gainers")).toBeInTheDocument();
  });

  it("shows collection-error state with retry instead of a full-page error", async () => {
    mockFetchCollectionSummary.mockResolvedValue({
      data: null,
      errors: [{ message: "boom" }],
      meta: {},
    });
    renderDashboard();

    await waitFor(() => expect(screen.getByTestId("collection-error")).toBeInTheDocument());
    expect(screen.getByTestId("page-dashboard")).toBeInTheDocument();
    expect(screen.getByTestId("trending-section-gainers")).toBeInTheDocument();
  });

  it("shows the skeleton while the collection summary is loading", () => {
    mockFetchCollectionSummary.mockReturnValue(new Promise(() => {}));
    renderDashboard();

    expect(screen.getByTestId("page-dashboard")).toBeInTheDocument();
    expect(screen.queryByTestId("collection-kpis")).not.toBeInTheDocument();
    expect(screen.queryByTestId("trending-grid")).not.toBeInTheDocument();
  });
});
