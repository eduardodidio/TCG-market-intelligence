import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MarketPage } from "../../src/pages/MarketPage";
import type { ApiResponse, MarketSummaryResponse, TrendingResponse } from "../../src/types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function mockSummaryResponse(): MarketSummaryResponse {
  return {
    total_cards_tracked: 150,
    total_observations: 500,
    avg_price: 12.5,
    avg_price_change_pct: 3.75,
    gainers_count: 80,
    losers_count: 50,
    unchanged_count: 20,
    market_direction: "up",
    period: "30d",
    currency: "BRL",
    computed_at: "2026-08-22T12:00:00",
  };
}

function mockTrendingResponse(direction: string = "up"): TrendingResponse {
  return {
    cards: [
      {
        card_id: 1,
        name_en: "Lightning Bolt",
        name_pt: null,
        set_code: "lea",
        collector_number: "161",
        image_url: null,
        price_start: 10,
        price_end: 15,
        change_pct: 50,
        change_abs: 5,
        consistency: 0.9,
        composite_score: 75,
        observation_count: 5,
        currency: "BRL",
      },
    ],
    period: "30d",
    direction,
    computed_at: "2026-08-22T12:00:00",
    cached: false,
  };
}

function mockFetch() {
  return vi.fn().mockImplementation((url: string) => {
    if (url.includes("/market/summary")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockSummaryResponse())),
      });
    }
    if (url.includes("/market/volatile")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockTrendingResponse("volatile"))),
      });
    }
    if (url.includes("/market/trending/losers")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockTrendingResponse("down"))),
      });
    }
    if (url.includes("/market/trending/gainers")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(mockTrendingResponse("up"))),
      });
    }
    if (url.includes("/decks/ranking")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            envelope({ decks: [], period: "30d", currency: "BRL" }),
          ),
      });
    }
    // Default fallback
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(envelope(null)),
    });
  });
}

function mockFailingFetch() {
  return vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: false,
      status: 500,
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, offset: null, request_id: "test" },
          errors: [{ code: "ERR", message: "Server error" }],
        }),
    }),
  );
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/market"]}>
      <MarketPage />
    </MemoryRouter>,
  );
}

describe("MarketPage", () => {
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("renders page title", () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    expect(screen.getByText("Market Overview")).toBeTruthy();
  });

  it("has page-market testid", () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    expect(screen.getByTestId("page-market")).toBeTruthy();
  });

  it("renders PeriodSelector with default periods", () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    expect(screen.getByText("7d")).toBeTruthy();
    expect(screen.getByText("30d")).toBeTruthy();
    expect(screen.getByText("90d")).toBeTruthy();
  });

  it("renders MarketSummaryKpis section", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("market-summary-kpis")).toBeTruthy();
    });
  });

  it("renders trending sections", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("market-trending-up")).toBeTruthy();
      expect(screen.getByTestId("market-trending-down")).toBeTruthy();
    });
  });

  it("period change updates active button styling", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();

    const btn7d = screen.getByText("7d");
    const btn30d = screen.getByText("30d");

    // 30d is active by default
    expect(btn30d).toHaveClass("bg-indigo-500");
    expect(btn7d).not.toHaveClass("bg-indigo-500");

    // Click 7d
    fireEvent.click(btn7d);
    expect(btn7d).toHaveClass("bg-indigo-500");
  });

  it("does not crash when APIs fail", async () => {
    global.fetch = mockFailingFetch() as unknown as typeof fetch;
    renderPage();

    // Page should still render its basic structure
    expect(screen.getByText("Market Overview")).toBeTruthy();
    expect(screen.getByTestId("page-market")).toBeTruthy();
  });

  it("shows loading skeletons initially", () => {
    // Use a fetch that never resolves to keep loading state
    global.fetch = vi.fn().mockReturnValue(
      new Promise(() => {}),
    ) as unknown as typeof fetch;
    renderPage();

    expect(screen.getByTestId("market-summary-loading")).toBeTruthy();
  });
});
