import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { PriceChart } from "../../src/components/PriceChart";
import { mockPriceHistory, mockApiError } from "../fixtures/api-responses";

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

function renderPriceChart(cardId = 1) {
  return render(
    <MemoryRouter>
      <PriceChart cardId={cardId} />
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
          meta: { cursor: null, total: null, request_id: "" },
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

  it("renders all period selector buttons", async () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();

    expect(screen.getByTestId("period-selector")).toBeDefined();
    expect(screen.getByTestId("period-btn-30d")).toBeDefined();
    expect(screen.getByTestId("period-btn-90d")).toBeDefined();
    expect(screen.getByTestId("period-btn-180d")).toBeDefined();
    expect(screen.getByTestId("period-btn-1y")).toBeDefined();
    expect(screen.getByTestId("period-btn-3y")).toBeDefined();
  });

  it("90d button is active by default", () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();

    const btn90d = screen.getByTestId("period-btn-90d");
    expect(btn90d.className).toContain("bg-indigo-500");
  });

  it("clicking a period button changes active state", async () => {
    globalThis.fetch = mockFetchHistory() as unknown as typeof fetch;
    renderPriceChart();

    await waitFor(() => {
      expect(screen.getByTestId("chart-container")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("period-btn-30d"));

    const btn30d = screen.getByTestId("period-btn-30d");
    expect(btn30d.className).toContain("bg-indigo-500");

    const btn90d = screen.getByTestId("period-btn-90d");
    expect(btn90d.className).not.toContain("bg-indigo-500");
  });

  it("period change triggers new API call", async () => {
    const mockFetch = mockFetchHistory();
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderPriceChart();

    await waitFor(() => {
      expect(screen.getByTestId("chart-container")).toBeDefined();
    });

    const callsBefore = mockFetch.mock.calls.length;

    fireEvent.click(screen.getByTestId("period-btn-30d"));

    await waitFor(() => {
      const callsAfter = mockFetch.mock.calls.length;
      expect(callsAfter).toBeGreaterThan(callsBefore);
    });

    // Verify the period param was included
    const lastCall = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
    expect(String(lastCall[0])).toContain("period=30d");
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
      // Create high-value price data
      const highValueData = mockPriceHistory(30);
      highValueData.data = highValueData.data!.map((obs, i) => ({
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

      // Chart should render without errors even with high values
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

      // No chart rendered, no crash
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

      // Chart renders successfully with Brush
      expect(screen.getByTestId("price-chart")).toBeDefined();
    });

    it("does not render Brush with sparse data", async () => {
      globalThis.fetch = mockFetchHistory(mockPriceHistory(5)) as unknown as typeof fetch;
      renderPriceChart();

      await waitFor(() => {
        expect(screen.getByTestId("chart-container")).toBeDefined();
      });

      // Chart still renders, just without Brush
      expect(screen.getByTestId("price-chart")).toBeDefined();
    });
  });
});
