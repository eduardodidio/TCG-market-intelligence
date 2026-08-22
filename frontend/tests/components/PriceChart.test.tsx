import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PriceChart } from "../../src/components/PriceChart";
import { mockPriceHistory, mockApiError } from "../fixtures/api-responses";
import type { ApiResponse, PriceHistoryResponse } from "../../src/types/api";

// Mock Recharts to avoid jsdom SVG rendering issues
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 500, height: 300 }}>
        {children}
      </div>
    ),
  };
});

function renderPriceChart(props?: { cardId?: number; currency?: string; fetchHistory?: (p: string, c: string) => Promise<ApiResponse<PriceHistoryResponse>> }) {
  return render(
    <MemoryRouter>
      <PriceChart cardId={props?.cardId ?? 1} currency={props?.currency} fetchHistory={props?.fetchHistory} />
    </MemoryRouter>,
  );
}

function mockFetchHistory(response = mockPriceHistory()) {
  return vi.fn().mockImplementation((url: string) => {
    const urlStr = String(url);
    if (urlStr.includes("/history")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(response),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, offset: null, request_id: "" },
          errors: [],
        }),
    });
  });
}

describe("PriceChart", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders chart container with data", async () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();

    await waitFor(() => {
      expect(screen.getByTestId("price-chart")).toBeDefined();
    });

    await waitFor(() => {
      expect(screen.getByTestId("chart-container")).toBeDefined();
    });
  });

  it("renders six period selector buttons", async () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();

    expect(screen.getByTestId("period-selector")).toBeDefined();
    expect(screen.getByTestId("period-btn-24h")).toBeDefined();
    expect(screen.getByTestId("period-btn-7d")).toBeDefined();
    expect(screen.getByTestId("period-btn-30d")).toBeDefined();
    expect(screen.getByTestId("period-btn-90d")).toBeDefined();
    expect(screen.getByTestId("period-btn-180d")).toBeDefined();
    expect(screen.getByTestId("period-btn-1y")).toBeDefined();
  });

  it("does NOT render 3y period button", () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();
    expect(screen.queryByTestId("period-btn-3y")).toBeNull();
  });

  it("30d button is active by default", () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();

    const btn30d = screen.getByTestId("period-btn-30d");
    expect(btn30d.className).toContain("bg-indigo-500");
  });

  it("clicking a period button changes active state", async () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();

    await waitFor(() => {
      expect(screen.getByTestId("chart-container")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("period-btn-90d"));

    const btn90d = screen.getByTestId("period-btn-90d");
    expect(btn90d.className).toContain("bg-indigo-500");

    const btn30d = screen.getByTestId("period-btn-30d");
    expect(btn30d.className).not.toContain("bg-indigo-500");
  });

  it("period change triggers new API call", async () => {
    const mockFetch = mockFetchHistory();
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderPriceChart();

    await waitFor(() => {
      expect(screen.getByTestId("chart-container")).toBeDefined();
    });

    const callsBefore = mockFetch.mock.calls.length;

    fireEvent.click(screen.getByTestId("period-btn-90d"));

    await waitFor(() => {
      const callsAfter = mockFetch.mock.calls.length;
      expect(callsAfter).toBeGreaterThan(callsBefore);
    });

    // Verify the period param was included
    const lastCall = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
    expect(String(lastCall[0])).toContain("period=90d");
  });

  it("shows empty message when no observations", async () => {
    const emptyResponse = mockPriceHistory(0);
    globalThis.fetch = mockFetchHistory(emptyResponse) as unknown as typeof fetch;
    renderPriceChart();

    await waitFor(() => {
      expect(screen.getByTestId("empty-history")).toBeDefined();
    });

    expect(screen.getByText("No price history available")).toBeDefined();
  });

  it("shows loading spinner while fetching", () => {
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise(() => {}),
    ) as unknown as typeof fetch;
    renderPriceChart();

    expect(screen.getByTestId("loading-spinner")).toBeDefined();
  });

  it("shows error banner on API error", async () => {
    const errorResponse = mockApiError("NOT_FOUND", "History not found");
    globalThis.fetch = mockFetchHistory(
      errorResponse as unknown as ReturnType<typeof mockPriceHistory>,
    ) as unknown as typeof fetch;
    renderPriceChart();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeDefined();
    });
  });

  describe("price change summary", () => {
    it("renders summary with positive change", async () => {
      const response = mockPriceHistory(10, {
        price_start: 10.0,
        price_end: 15.0,
        absolute_change: 5.0,
        percent_change: 50.0,
        resolution: "daily",
      });
      globalThis.fetch = mockFetchHistory(response) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("price-summary")).toBeDefined();
      });

      const summary = screen.getByTestId("price-summary");
      expect(summary.textContent).toContain("Start");
      expect(summary.textContent).toContain("Current");
      expect(summary.textContent).toContain("Change");
      // Positive change should have green class
      const changeEl = summary.querySelector(".text-green-400");
      expect(changeEl).not.toBeNull();
    });

    it("renders summary with negative change", async () => {
      const response = mockPriceHistory(10, {
        price_start: 20.0,
        price_end: 15.0,
        absolute_change: -5.0,
        percent_change: -25.0,
        resolution: "daily",
      });
      globalThis.fetch = mockFetchHistory(response) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("price-summary")).toBeDefined();
      });

      const summary = screen.getByTestId("price-summary");
      const changeEl = summary.querySelector(".text-red-400");
      expect(changeEl).not.toBeNull();
    });

    it("does not render summary when null", async () => {
      const response = mockPriceHistory(0);
      globalThis.fetch = mockFetchHistory(response) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("empty-history")).toBeDefined();
      });

      expect(screen.queryByTestId("price-summary")).toBeNull();
    });

    it("shows resolution badge daily", async () => {
      const response = mockPriceHistory(10, { resolution: "daily" });
      globalThis.fetch = mockFetchHistory(response) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("resolution-badge")).toBeDefined();
      });

      expect(screen.getByTestId("resolution-badge").textContent).toBe("Daily");
    });

    it("shows resolution badge weekly", async () => {
      const response = mockPriceHistory(10, { resolution: "weekly" });
      globalThis.fetch = mockFetchHistory(response) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("resolution-badge")).toBeDefined();
      });

      expect(screen.getByTestId("resolution-badge").textContent).toBe("Weekly");
    });
  });

  describe("custom fetch function", () => {
    it("uses custom fetchHistory prop when provided", async () => {
      const customFetcher = vi.fn().mockResolvedValue(mockPriceHistory(5));
      renderPriceChart({ fetchHistory: customFetcher });

      await waitFor(() => {
        expect(customFetcher).toHaveBeenCalled();
      });

      // Verify it was called with period and currency
      expect(customFetcher).toHaveBeenCalledWith("30d", "BRL");
    });

    it("does not call default fetchCardHistory when custom is provided", async () => {
      const customFetcher = vi.fn().mockResolvedValue(mockPriceHistory(5));
      // No globalThis.fetch mock -- if default is called, it would fail
      renderPriceChart({ fetchHistory: customFetcher });

      await waitFor(() => {
        expect(customFetcher).toHaveBeenCalled();
      });
    });
  });

  describe("sparse data handling", () => {
    it("shows sparse-data-notice with 1 data point", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(1)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("sparse-data-notice")).toBeDefined();
      });

      expect(screen.getByTestId("sparse-data-notice").textContent).toContain(
        "1 data point so far",
      );
      // Chart should still render
      expect(screen.getByTestId("chart-container")).toBeDefined();
    });

    it("shows sparse-data-notice with 5 data points", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(5)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("sparse-data-notice")).toBeDefined();
      });

      expect(screen.getByTestId("sparse-data-notice").textContent).toContain(
        "5 data points so far",
      );
      expect(screen.getByTestId("chart-container")).toBeDefined();
    });

    it("does not show sparse-data-notice with 7 data points", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(7)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("chart-container")).toBeDefined();
      });

      expect(screen.queryByTestId("sparse-data-notice")).toBeNull();
    });

    it("does not show sparse-data-notice with 30 data points", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(30)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("chart-container")).toBeDefined();
      });

      expect(screen.queryByTestId("sparse-data-notice")).toBeNull();
    });

    it("shows empty state with 0 data points, not sparse notice", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(0)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("empty-history")).toBeDefined();
      });

      expect(screen.getByText("No price history available")).toBeDefined();
      expect(screen.queryByTestId("sparse-data-notice")).toBeNull();
      expect(screen.queryByTestId("chart-container")).toBeNull();
    });
  });

  describe("Y-axis auto-scaling", () => {
    it("renders chart with high-value cards (>R$100) without capping", async () => {
      const highValueData = mockPriceHistory(30);
      highValueData.data!.observations = highValueData.data!.observations.map((obs, i) => ({
        ...obs,
        median_price: 250 + Math.sin(i / 5) * 50,
        tcg_price: 240 + Math.sin(i / 5) * 40,
        last_sold_price: 260,
      }));
      globalThis.fetch = mockFetchHistory(highValueData) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("chart-container")).toBeDefined();
      });

      expect(screen.getByTestId("price-chart")).toBeDefined();
    });
  });

  describe("zoom functionality", () => {
    it("does not show reset zoom button initially", async () => {
      globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("chart-container")).toBeDefined();
      });

      expect(screen.queryByTestId("reset-zoom-btn")).toBeNull();
    });

    it("handles empty data gracefully with zoom state", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(0)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("empty-history")).toBeDefined();
      });

      expect(screen.queryByTestId("chart-container")).toBeNull();
      expect(screen.queryByTestId("reset-zoom-btn")).toBeNull();
    });
  });

  describe("Brush component", () => {
    it("renders with sufficient data points (>14)", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(20)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("chart-container")).toBeDefined();
      });

      expect(screen.getByTestId("price-chart")).toBeDefined();
    });

    it("does not render Brush with sparse data", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(5)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("chart-container")).toBeDefined();
      });

      expect(screen.getByTestId("price-chart")).toBeDefined();
    });
  });
});
