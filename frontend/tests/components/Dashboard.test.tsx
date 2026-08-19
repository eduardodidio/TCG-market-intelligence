import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Dashboard } from "../../src/pages/Dashboard";
import {
  mockMarketStats,
  mockMoversResponse,
  mockApiError,
} from "../fixtures/api-responses";

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
    const moversResponse = mockMoversResponse();

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/market/stats")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(statsResponse),
          });
        }
        if (urlStr.includes("/market/movers")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(moversResponse),
          });
        }
        return Promise.reject(new Error(`Unexpected URL: ${urlStr}`));
      },
    );
  }

  function mockFetchError() {
    const errorResponse = mockApiError("SERVER_ERROR", "Internal server error");

    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve(errorResponse),
    });
  }

  it("shows skeleton loading while data is being fetched", () => {
    // Make fetch never resolve
    (fetch as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    renderDashboard();

    const skeletons = screen.getAllByTestId("skeleton-kpi");
    expect(skeletons.length).toBe(4);
  });

  it("renders 4 KPI cards with market statistics", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-kpi")).toBeNull();
    });

    const kpiCards = screen.getAllByTestId("kpi-card");
    expect(kpiCards).toHaveLength(4);

    expect(screen.getByText("Total Cards")).toBeDefined();
    expect(screen.getByText("150")).toBeDefined();

    expect(screen.getByText("Total Observations")).toBeDefined();
    expect(screen.getByText("4500")).toBeDefined();

    expect(screen.getByText("Average Price")).toBeDefined();

    expect(screen.getByText("Data Range")).toBeDefined();
    // Date range: 01/01/2026 - 18/08/2026
    expect(screen.getByText("01/01/2026 - 18/08/2026")).toBeDefined();
  });

  it("renders movers preview with gainers and losers", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("movers-preview")).toBeDefined();
    });

    expect(screen.getByText("Top Gainers")).toBeDefined();
    expect(screen.getByText("Top Losers")).toBeDefined();
    expect(screen.getByText("Card Gainer 1")).toBeDefined();
    expect(screen.getByText("Card Loser 1")).toBeDefined();
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

  it("renders page title", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByText("Market Overview")).toBeDefined();
    });
  });

  it("fetches movers with period=30d by default", async () => {
    mockFetchSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("movers-preview")).toBeDefined();
    });

    // Verify that at least one fetch call included period=30d
    const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
    const moversCalls = calls.filter((c: unknown[]) =>
      String(c[0]).includes("/market/movers"),
    );
    expect(moversCalls.length).toBeGreaterThan(0);
    expect(String(moversCalls[0][0])).toContain("period=30d");
  });
});
