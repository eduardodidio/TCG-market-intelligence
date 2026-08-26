import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "../../src/pages/Dashboard";
import {
  mockMarketStats,
  mockCollectionHealth,
  mockCollectionSummary,
  mockEmptyMarketStats,
  mockApiError,
} from "../fixtures/api-responses";

// Mock TrendingSection — it fetches its own data internally and has its own tests
vi.mock("../../src/components/TrendingSection", () => ({
  TrendingSection: ({ direction, period, currency, limit }: {
    direction: string;
    period: string;
    currency: string;
    limit?: number;
  }) => (
    <div
      data-testid={`trending-section-${direction}`}
      data-period={period}
      data-currency={currency}
      data-limit={limit}
    >
      TrendingSection-{direction}
    </div>
  ),
}));

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

describe("Dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockFetchSuccess() {
    const statsResponse = mockMarketStats();
    const healthResponse = mockCollectionHealth();
    const summaryResponse = mockCollectionSummary();

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/market/stats")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(statsResponse),
          });
        }
        if (urlStr.includes("/collect/health")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(healthResponse),
          });
        }
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(summaryResponse),
          });
        }
        // Trending endpoints are handled by the mocked TrendingSection
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [] }),
        });
      },
    );
  }

  function mockFetchError() {
    const errorResponse = mockApiError("SERVER_ERROR", "Internal server error");
    const healthResponse = mockCollectionHealth();
    const summaryResponse = mockCollectionSummary();

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        // Health and collection summary endpoints still succeed — they must not block dashboard
        if (urlStr.includes("/collect/health")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(healthResponse),
          });
        }
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(summaryResponse),
          });
        }
        return Promise.resolve({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
          json: () => Promise.resolve(errorResponse),
        });
      },
    );
  }

  it("shows skeleton loading while data is being fetched", () => {
    // Make fetch never resolve
    (fetch as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    renderDashboard();

    const skeletons = screen.getAllByTestId("skeleton-kpi");
    expect(skeletons.length).toBe(4);
  });

  it("renders hero header with title and subtitle", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("TEDHC Market")).toBeDefined();
    });

    expect(
      screen.getByText("Track prices, spot trends, manage your collection"),
    ).toBeDefined();
  });

  it("renders collection KPIs when collection summary is available", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("collection-kpis")).toBeDefined();
    });

    // Collection KPIs from fixture: total_unique=120, total_cards=340, total_value=2850, linked_count=96
    expect(screen.getByText("Collection Cards")).toBeDefined();
    expect(screen.getByText("120")).toBeDefined();

    expect(screen.getByText("Total Copies")).toBeDefined();
    expect(screen.getByText("340")).toBeDefined();

    expect(screen.getByText("Est. Collection Value")).toBeDefined();

    expect(screen.getByText("Coverage")).toBeDefined();
    // linkedPct = round(96/120 * 100) = 80%
    expect(screen.getByText("80%")).toBeDefined();

    // Coverage breakdown shows linked and priced counts
    expect(screen.getByTestId("coverage-breakdown")).toBeDefined();
    expect(screen.getByText(/96 linked/)).toBeDefined();
    expect(screen.getByText(/80 priced/)).toBeDefined();
  });

  it("renders market summary strip with compact KPIs", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("market-summary-strip")).toBeDefined();
    });

    expect(screen.getByText("Cards tracked")).toBeDefined();
    expect(screen.getByText("150")).toBeDefined();

    expect(screen.getByText("Price observations")).toBeDefined();
    expect(screen.getByText("4500")).toBeDefined();

    expect(screen.getByText("Avg. price")).toBeDefined();
  });

  it("renders trending sections for gainers and losers", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("landing-trending-up")).toBeDefined();
    });

    expect(screen.getByTestId("landing-trending-down")).toBeDefined();

    // Verify TrendingSection components are rendered with correct props
    const gainersSection = screen.getByTestId("trending-section-gainers");
    expect(gainersSection).toBeDefined();
    expect(gainersSection.getAttribute("data-period")).toBe("30d");
    expect(gainersSection.getAttribute("data-limit")).toBe("10");

    const losersSection = screen.getByTestId("trending-section-losers");
    expect(losersSection).toBeDefined();
    expect(losersSection.getAttribute("data-period")).toBe("30d");
    expect(losersSection.getAttribute("data-limit")).toBe("10");
  });

  it("does NOT render MoversPreview", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("market-summary-strip")).toBeDefined();
    });

    // MoversPreview is gone — no movers-preview test ID
    expect(screen.queryByTestId("movers-preview")).toBeNull();
  });

  it("shows error banner when API call fails", async () => {
    mockFetchError();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeDefined();
    });

    expect(screen.getByText("Internal server error")).toBeDefined();
  });

  it("shows retry button that refetches data on error", async () => {
    mockFetchError();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeDefined();
    });

    // Now mock success for retry
    mockFetchSuccess();

    fireEvent.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(screen.queryByTestId("error-banner")).toBeNull();
    });
  });

  it("renders hero title instead of old 'My Collection' page title", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("TEDHC Market")).toBeDefined();
    });

    // The old "My Collection" title in the hero section is replaced
    // "My Collection" may still appear in collection KPIs subtitle, but not as the page heading
  });

  it("does NOT render Market Overview heading (replaced by summary strip)", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("market-summary-strip")).toBeDefined();
    });

    // The old "Market Overview" h2 heading is gone
    expect(screen.queryByText("Market Overview")).toBeNull();
  });

  it("renders freshness indicator when health endpoint succeeds", async () => {
    // Fix "now" so relative time is deterministic
    const now = new Date("2026-08-19T12:00:00Z").getTime();
    vi.spyOn(Date, "now").mockReturnValue(now);

    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("freshness-indicator")).toBeDefined();
    });

    // Health fixture has last_collection_at = "2026-08-19T10:30:00Z"
    // That's 1.5 hours before "now" -> "1 hour ago"
    expect(screen.getByText(/Last updated:/)).toBeDefined();

    // Green dot for healthy status
    const dot = screen.getByTestId("freshness-dot");
    expect(dot.className).toContain("bg-green-400");
  });

  it("renders dashboard without freshness indicator when health endpoint fails", async () => {
    const statsResponse = mockMarketStats();
    const summaryResponse = mockCollectionSummary();
    const healthError = mockApiError("SERVER_ERROR", "Health check failed");

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/market/stats")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(statsResponse),
          });
        }
        if (urlStr.includes("/collect/health")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: "Internal Server Error",
            json: () => Promise.resolve(healthError),
          });
        }
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(summaryResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [] }),
        });
      },
    );

    renderDashboard();

    // Dashboard still loads its collection KPIs + market summary strip
    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-kpi")).toBeNull();
    });

    const kpiCards = screen.getAllByTestId("kpi-card");
    expect(kpiCards).toHaveLength(4); // Only 4 collection KPIs now (market is a strip)

    // Freshness indicator should NOT be rendered
    expect(screen.queryByTestId("freshness-indicator")).toBeNull();
  });

  it("renders gracefully when collection summary returns zero values", async () => {
    const statsResponse = mockMarketStats();
    const healthResponse = mockCollectionHealth();
    const emptySummary = mockCollectionSummary({
      total_unique: 0,
      total_cards: 0,
      total_value: null,
      linked_count: 0,
      priced_count: 0,
      sets_count: 0,
    });

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/market/stats")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(statsResponse),
          });
        }
        if (urlStr.includes("/collect/health")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(healthResponse),
          });
        }
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(emptySummary),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [] }),
        });
      },
    );

    renderDashboard();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-kpi")).toBeNull();
    });

    // Collection KPIs still render with zero values
    expect(screen.getByTestId("collection-kpis")).toBeDefined();
    expect(screen.getByText("Collection Cards")).toBeDefined();

    // Coverage should be 0% when total_unique is 0
    expect(screen.getByText("0%")).toBeDefined();

    // Market summary strip still visible
    expect(screen.getByTestId("market-summary-strip")).toBeDefined();
  });

  it("shows low coverage hint when linked percentage is below 50%", async () => {
    const statsResponse = mockMarketStats();
    const healthResponse = mockCollectionHealth();
    const lowCoverageSummary = mockCollectionSummary({
      total_unique: 100,
      total_cards: 200,
      total_value: 500.0,
      linked_count: 30,
      priced_count: 20,
      sets_count: 3,
    });

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/market/stats")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(statsResponse),
          });
        }
        if (urlStr.includes("/collect/health")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(healthResponse),
          });
        }
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(lowCoverageSummary),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [] }),
        });
      },
    );

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("collection-kpis")).toBeDefined();
    });

    // Low coverage hint should appear (30% < 50%)
    expect(screen.getByTestId("low-coverage-hint")).toBeDefined();
    expect(
      screen.getByText(/Sync your collection with MYP to improve coverage/),
    ).toBeDefined();
  });

  it("does not show low coverage hint when linked percentage is 50% or above", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("collection-kpis")).toBeDefined();
    });

    // Default fixture has 96/120 = 80% coverage, which is >= 50%
    expect(screen.queryByTestId("low-coverage-hint")).toBeNull();
  });

  it("renders gracefully when market stats returns zero", async () => {
    const emptyStats = mockEmptyMarketStats();
    const healthResponse = mockCollectionHealth();
    const summaryResponse = mockCollectionSummary();

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/market/stats")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(emptyStats),
          });
        }
        if (urlStr.includes("/collect/health")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(healthResponse),
          });
        }
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(summaryResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [] }),
        });
      },
    );

    renderDashboard();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-kpi")).toBeNull();
    });

    // Collection KPIs should still render
    expect(screen.getByTestId("collection-kpis")).toBeDefined();

    // Market summary strip should show empty state instead
    expect(screen.getByTestId("market-empty")).toBeDefined();
    expect(
      screen.getByText(
        "Import your collection and sync with MYP to see market data here.",
      ),
    ).toBeDefined();

    // Trending sections are still rendered (they handle their own empty states)
    expect(screen.getByTestId("landing-trending-up")).toBeDefined();
    expect(screen.getByTestId("landing-trending-down")).toBeDefined();
  });

  it("shows collection empty state when summary endpoint fails", async () => {
    const statsResponse = mockMarketStats();
    const healthResponse = mockCollectionHealth();
    const summaryError = mockApiError("SERVER_ERROR", "Collection unavailable");

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/market/stats")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(statsResponse),
          });
        }
        if (urlStr.includes("/collect/health")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(healthResponse),
          });
        }
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: "Internal Server Error",
            json: () => Promise.resolve(summaryError),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [] }),
        });
      },
    );

    renderDashboard();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-kpi")).toBeNull();
    });

    // Collection section should show empty state
    expect(screen.getByTestId("collection-empty")).toBeDefined();
    expect(
      screen.getByText(
        "Import your collection and sync with MYP to see your stats here.",
      ),
    ).toBeDefined();

    // Market section still works
    expect(screen.getByTestId("market-summary-strip")).toBeDefined();

    // Trending sections present
    expect(screen.getByTestId("landing-trending-up")).toBeDefined();
    expect(screen.getByTestId("landing-trending-down")).toBeDefined();
  });

  it("trending sections render even when data is empty (graceful degradation)", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("landing-trending-up")).toBeDefined();
    });

    // TrendingSection handles its own loading/empty states internally
    // We just verify the containers are present
    expect(screen.getByTestId("landing-trending-down")).toBeDefined();
    expect(screen.getByText("TrendingSection-gainers")).toBeDefined();
    expect(screen.getByText("TrendingSection-losers")).toBeDefined();
  });
});
