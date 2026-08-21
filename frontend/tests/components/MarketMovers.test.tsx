import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MarketMovers } from "../../src/pages/MarketMovers";
import {
  mockMoversResponse,
  mockApiError,
} from "../fixtures/api-responses";
import type { ApiResponse, MoversResponse } from "../../src/types/api";

function renderMarketMovers() {
  return render(
    <MemoryRouter>
      <MarketMovers />
    </MemoryRouter>,
  );
}

describe("MarketMovers page", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockFetchSuccess(response?: ApiResponse<MoversResponse>) {
    const moversResponse = response ?? mockMoversResponse();
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(moversResponse),
    });
  }

  function mockFetchEmpty() {
    const emptyResponse: ApiResponse<MoversResponse> = {
      data: { gainers: [], losers: [] },
      meta: { cursor: null, total: null, request_id: "req-test-empty" },
      errors: [],
    };
    (fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(emptyResponse),
    });
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
    (fetch as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
    renderMarketMovers();

    expect(screen.getByTestId("skeleton-movers")).toBeDefined();
    const skeletons = screen.getAllByTestId("skeleton-table");
    expect(skeletons.length).toBe(2);
  });

  it("renders page title", async () => {
    mockFetchSuccess();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-movers")).toBeNull();
    });

    expect(screen.getByText("Market Movers")).toBeDefined();
  });

  it("renders both gainers and losers tables", async () => {
    mockFetchSuccess();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.getByTestId("movers-table-gainers")).toBeDefined();
    });

    expect(screen.getByTestId("movers-table-losers")).toBeDefined();
    expect(screen.getByText("Top Gainers")).toBeDefined();
    expect(screen.getByText("Top Losers")).toBeDefined();

    // Card names from fixture
    expect(screen.getByText("Card Gainer 1")).toBeDefined();
    expect(screen.getByText("Card Loser 1")).toBeDefined();
  });

  it("renders period selector with 30d active by default", async () => {
    mockFetchSuccess();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-movers")).toBeNull();
    });

    const btn7d = screen.getByText("7d");
    const btn30d = screen.getByText("30d");
    const btn90d = screen.getByText("90d");

    expect(btn30d.className).toContain("bg-indigo-500");
    expect(btn7d.className).toContain("bg-slate-800");
    expect(btn90d.className).toContain("bg-slate-800");
  });

  it("changes period and triggers refetch on period button click", async () => {
    mockFetchSuccess();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-movers")).toBeNull();
    });

    // Initial fetch with period=30d
    const initialCallCount = (fetch as ReturnType<typeof vi.fn>).mock.calls.length;

    // Click 7d
    fireEvent.click(screen.getByText("7d"));

    await waitFor(() => {
      const newCallCount = (fetch as ReturnType<typeof vi.fn>).mock.calls.length;
      expect(newCallCount).toBeGreaterThan(initialCallCount);
    });

    // Verify 7d button is now active
    expect(screen.getByText("7d").className).toContain("bg-indigo-500");
    expect(screen.getByText("30d").className).toContain("bg-slate-800");
  });

  it("passes period parameter to API call", async () => {
    mockFetchSuccess();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-movers")).toBeNull();
    });

    // Check initial call includes period=30d
    const firstCallUrl = (fetch as ReturnType<typeof vi.fn>).mock.calls[0][0] as string;
    expect(firstCallUrl).toContain("period=30d");

    // Click 90d
    fireEvent.click(screen.getByText("90d"));

    await waitFor(() => {
      const calls = (fetch as ReturnType<typeof vi.fn>).mock.calls;
      const lastCallUrl = calls[calls.length - 1][0] as string;
      expect(lastCallUrl).toContain("period=90d");
    });
  });

  it("shows empty state when no movers data available", async () => {
    mockFetchEmpty();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-movers")).toBeNull();
    });

    expect(screen.getByTestId("empty-state")).toBeDefined();
    expect(
      screen.getByText("Not enough price history for movers. Run a sync and check back."),
    ).toBeDefined();

    // Tables should not render
    expect(screen.queryByTestId("movers-table-gainers")).toBeNull();
    expect(screen.queryByTestId("movers-table-losers")).toBeNull();
  });

  it("shows error banner when API fails", async () => {
    mockFetchError();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeDefined();
    });

    expect(screen.getByText("Internal server error")).toBeDefined();
  });

  it("shows retry button that refetches on error", async () => {
    mockFetchError();
    renderMarketMovers();

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

  it("renders limit selector with default value 25", async () => {
    mockFetchSuccess();
    renderMarketMovers();

    await waitFor(() => {
      expect(screen.queryByTestId("skeleton-movers")).toBeNull();
    });

    const select = screen.getByLabelText("Results limit") as HTMLSelectElement;
    expect(select.value).toBe("25");
  });
});
