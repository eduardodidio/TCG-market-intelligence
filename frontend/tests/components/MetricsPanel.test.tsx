import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MetricsPanel } from "../../src/components/MetricsPanel";
import type { ApiResponse, CardMetricsResponse } from "../../src/types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function mockMetrics(overrides?: Partial<CardMetricsResponse>): CardMetricsResponse {
  return {
    entry_id: 1,
    card_id: 42,
    period: "30d",
    currency: "BRL",
    moving_averages: [
      { period: 7, value: 10.5 },
      { period: 30, value: 11.2 },
    ],
    extremes: {
      ath_price: 15.0,
      ath_date: "2026-08-01",
      atl_price: 5.0,
      atl_date: "2026-01-15",
    },
    volatility: {
      period_days: 30,
      std_dev: 1.5,
      coefficient_of_variation: 0.15,
    },
    momentum: {
      period_days: 30,
      rate_of_change: 12.5,
      trend_direction: "up",
    },
    performance: {
      score: 75,
      label: "strong",
      period_days: 30,
    },
    period_comparison: {
      current_avg: 12.0,
      previous_avg: 10.0,
      delta: 2.0,
      delta_pct: 20.0,
      period_days: 30,
    },
    data_points: 30,
    ...overrides,
  };
}

function mockFetch(response: ApiResponse<CardMetricsResponse>) {
  return vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(response),
    }),
  );
}

function renderPanel(props?: { entryId?: number; period?: string; currency?: string }) {
  return render(
    <MemoryRouter>
      <MetricsPanel
        entryId={props?.entryId ?? 1}
        period={props?.period ?? "30d"}
        currency={props?.currency ?? "BRL"}
      />
    </MemoryRouter>,
  );
}

describe("MetricsPanel", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    localStorage.setItem("tcg_access_token", "test-token");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("renders metrics-panel data-testid", async () => {
    globalThis.fetch = mockFetch(envelope(mockMetrics()));
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId("metrics-panel")).toBeInTheDocument();
    });
  });

  it("shows skeleton loading state initially", () => {
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise(() => {}), // never resolves
    );
    renderPanel();
    expect(screen.getByTestId("metrics-panel")).toBeInTheDocument();
    // Skeleton cards should have animate-pulse
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows error banner on API failure", async () => {
    globalThis.fetch = vi.fn().mockImplementation(() =>
      Promise.resolve({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.resolve({ detail: "Server error" }),
      }),
    );
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/Server error|Internal Server Error/)).toBeInTheDocument();
    });
  });

  it("renders all 6 metric cards with full data", async () => {
    globalThis.fetch = mockFetch(envelope(mockMetrics()));
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId("metric-trend")).toBeInTheDocument();
      expect(screen.getByTestId("metric-moving-averages")).toBeInTheDocument();
      expect(screen.getByTestId("metric-ath-atl")).toBeInTheDocument();
      expect(screen.getByTestId("metric-volatility")).toBeInTheDocument();
      expect(screen.getByTestId("metric-performance")).toBeInTheDocument();
      expect(screen.getByTestId("metric-period-comparison")).toBeInTheDocument();
    });
  });

  it("hides individual cards when metric is null", async () => {
    const data = mockMetrics({
      momentum: null,
      performance: null,
      period_comparison: null,
    });
    globalThis.fetch = mockFetch(envelope(data));
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId("metrics-panel")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("metric-trend")).not.toBeInTheDocument();
    expect(screen.queryByTestId("metric-performance")).not.toBeInTheDocument();
    expect(screen.queryByTestId("metric-period-comparison")).not.toBeInTheDocument();
    // These should still be present
    expect(screen.getByTestId("metric-moving-averages")).toBeInTheDocument();
    expect(screen.getByTestId("metric-ath-atl")).toBeInTheDocument();
    expect(screen.getByTestId("metric-volatility")).toBeInTheDocument();
  });

  it("shows green arrow for uptrend", async () => {
    globalThis.fetch = mockFetch(envelope(mockMetrics()));
    renderPanel();
    await waitFor(() => {
      const trendCard = screen.getByTestId("metric-trend");
      // Up arrow character
      expect(trendCard.textContent).toContain("\u2191");
    });
  });

  it("shows red arrow for downtrend", async () => {
    const data = mockMetrics({
      momentum: { period_days: 30, rate_of_change: -8.5, trend_direction: "down" },
    });
    globalThis.fetch = mockFetch(envelope(data));
    renderPanel();
    await waitFor(() => {
      const trendCard = screen.getByTestId("metric-trend");
      expect(trendCard.textContent).toContain("\u2193");
    });
  });

  it("shows gray arrow for flat trend", async () => {
    const data = mockMetrics({
      momentum: { period_days: 30, rate_of_change: 0.5, trend_direction: "flat" },
    });
    globalThis.fetch = mockFetch(envelope(data));
    renderPanel();
    await waitFor(() => {
      const trendCard = screen.getByTestId("metric-trend");
      expect(trendCard.textContent).toContain("\u2192");
    });
  });

  it("performance badge shows correct label for strong", async () => {
    globalThis.fetch = mockFetch(envelope(mockMetrics()));
    renderPanel();
    await waitFor(() => {
      const badge = screen.getByTestId("performance-badge");
      expect(badge.textContent).toContain("Strong");
      expect(badge.className).toContain("green");
    });
  });

  it("performance badge shows correct color for declining", async () => {
    const data = mockMetrics({
      performance: { score: 15, label: "declining", period_days: 30 },
    });
    globalThis.fetch = mockFetch(envelope(data));
    renderPanel();
    await waitFor(() => {
      const badge = screen.getByTestId("performance-badge");
      expect(badge.className).toContain("red");
    });
  });

  it("volatility bar shows green for low", async () => {
    const data = mockMetrics({
      volatility: { period_days: 30, std_dev: 0.5, coefficient_of_variation: 0.05 },
    });
    globalThis.fetch = mockFetch(envelope(data));
    renderPanel();
    await waitFor(() => {
      const bar = screen.getByTestId("volatility-bar");
      expect(bar.className).toContain("green");
    });
  });

  it("volatility bar shows amber for medium", async () => {
    globalThis.fetch = mockFetch(envelope(mockMetrics()));
    renderPanel();
    await waitFor(() => {
      const bar = screen.getByTestId("volatility-bar");
      expect(bar.className).toContain("amber");
    });
  });

  it("volatility bar shows red for high", async () => {
    const data = mockMetrics({
      volatility: { period_days: 30, std_dev: 5.0, coefficient_of_variation: 0.5 },
    });
    globalThis.fetch = mockFetch(envelope(data));
    renderPanel();
    await waitFor(() => {
      const bar = screen.getByTestId("volatility-bar");
      expect(bar.className).toContain("red");
    });
  });

  it("shows insufficient data message when data_points is 0", async () => {
    const data = mockMetrics({ data_points: 0 });
    globalThis.fetch = mockFetch(envelope(data));
    renderPanel();
    await waitFor(() => {
      expect(screen.getByTestId("metrics-panel")).toBeInTheDocument();
      expect(screen.getByText(/Not enough data/i)).toBeInTheDocument();
    });
  });

  it("displays the analytics title", async () => {
    globalThis.fetch = mockFetch(envelope(mockMetrics()));
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText("Analytics")).toBeInTheDocument();
    });
  });

  it("re-fetches when period changes", async () => {
    const fetchMock = mockFetch(envelope(mockMetrics()));
    globalThis.fetch = fetchMock;

    const { rerender } = render(
      <MemoryRouter>
        <MetricsPanel entryId={1} period="30d" currency="BRL" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("metrics-panel")).toBeInTheDocument();
    });

    rerender(
      <MemoryRouter>
        <MetricsPanel entryId={1} period="7d" currency="BRL" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      // Should have been called at least twice (initial + re-render)
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
  });

  it("re-fetches when currency changes", async () => {
    const fetchMock = mockFetch(envelope(mockMetrics()));
    globalThis.fetch = fetchMock;

    const { rerender } = render(
      <MemoryRouter>
        <MetricsPanel entryId={1} period="30d" currency="BRL" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("metrics-panel")).toBeInTheDocument();
    });

    rerender(
      <MemoryRouter>
        <MetricsPanel entryId={1} period="30d" currency="USD" />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2);
    });
  });
});
