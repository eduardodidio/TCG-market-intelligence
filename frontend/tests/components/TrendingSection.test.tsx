import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TrendingSection } from "../../src/components/TrendingSection";
import type { ApiResponse, TrendingResponse } from "../../src/types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function errorEnvelope(): ApiResponse<TrendingResponse> {
  return {
    data: null,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [{ code: "ERR", message: "Server error" }],
  };
}

function mockTrendingResponse(
  overrides?: Partial<TrendingResponse>,
): TrendingResponse {
  return {
    cards: [
      {
        card_id: 1,
        name_en: "Lightning Bolt",
        name_pt: "Raio",
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
    direction: "up",
    computed_at: "2026-08-22T12:00:00",
    cached: false,
    ...overrides,
  };
}

function mockFetch(response: ApiResponse<TrendingResponse>) {
  return vi.fn().mockImplementation(() =>
    Promise.resolve({
      ok: true,
      json: () => Promise.resolve(response),
    }),
  );
}

function renderSection(direction: "gainers" | "losers" = "gainers") {
  return render(
    <MemoryRouter>
      <TrendingSection
        direction={direction}
        period="30d"
        currency="BRL"
        limit={20}
      />
    </MemoryRouter>,
  );
}

describe("TrendingSection", () => {
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("renders section header for gainers", async () => {
    global.fetch = mockFetch(envelope(mockTrendingResponse())) as unknown as typeof fetch;
    renderSection("gainers");
    await waitFor(() => {
      expect(screen.getByTestId("trending-section-gainers")).toBeTruthy();
    });
  });

  it("renders section header for losers", async () => {
    global.fetch = mockFetch(envelope(mockTrendingResponse({ direction: "down" }))) as unknown as typeof fetch;
    renderSection("losers");
    await waitFor(() => {
      expect(screen.getByTestId("trending-section-losers")).toBeTruthy();
    });
  });

  it("shows loading skeletons while fetching", () => {
    global.fetch = vi.fn().mockReturnValue(new Promise(() => {})) as unknown as typeof fetch;
    renderSection();
    expect(screen.getByTestId("trending-loading")).toBeTruthy();
    expect(screen.getAllByTestId("skeleton-card").length).toBe(4);
  });

  it("shows error banner on fetch failure", async () => {
    global.fetch = mockFetch(errorEnvelope()) as unknown as typeof fetch;
    renderSection();
    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeTruthy();
    });
  });

  it("shows empty state when no cards", async () => {
    global.fetch = mockFetch(
      envelope(mockTrendingResponse({ cards: [] })),
    ) as unknown as typeof fetch;
    renderSection();
    await waitFor(() => {
      expect(screen.getByText("No trending cards found for this period")).toBeTruthy();
    });
  });

  it("renders trending card tiles", async () => {
    global.fetch = mockFetch(envelope(mockTrendingResponse())) as unknown as typeof fetch;
    renderSection();
    await waitFor(() => {
      expect(screen.getByText("Lightning Bolt")).toBeTruthy();
    });
  });

  it("shows cached badge when response is cached", async () => {
    global.fetch = mockFetch(
      envelope(mockTrendingResponse({ cached: true })),
    ) as unknown as typeof fetch;
    renderSection();
    await waitFor(() => {
      expect(screen.getByTestId("cached-badge")).toBeTruthy();
    });
  });
});
