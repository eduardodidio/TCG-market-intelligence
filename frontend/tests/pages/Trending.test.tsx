import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Trending } from "../../src/pages/Trending";
import type { ApiResponse, TrendingResponse } from "../../src/types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function mockTrendingResponse(
  direction: "up" | "down" = "up",
): TrendingResponse {
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
    const direction = url.includes("losers") ? "down" : "up";
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(envelope(mockTrendingResponse(direction as "up" | "down"))),
    });
  });
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/market/trending"]}>
      <Trending />
    </MemoryRouter>,
  );
}

describe("Trending page", () => {
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("renders page title", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    expect(screen.getByText("Trending Cards")).toBeTruthy();
  });

  it("renders both trending sections", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("trending-section-gainers")).toBeTruthy();
      expect(screen.getByTestId("trending-section-losers")).toBeTruthy();
    });
  });

  it("renders period selector buttons", () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    expect(screen.getByText("7d")).toBeTruthy();
    expect(screen.getByText("30d")).toBeTruthy();
    expect(screen.getByText("90d")).toBeTruthy();
  });

  it("period selector changes on click", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();

    const btn7d = screen.getByText("7d");
    fireEvent.click(btn7d);

    // 7d button should now be active (indigo)
    expect(btn7d).toHaveClass("bg-indigo-500");
  });

  it("renders limit selector", () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    const select = screen.getByRole("combobox", { name: "Results limit" });
    expect(select).toBeTruthy();
  });

  it("has page testid", () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    expect(screen.getByTestId("page-trending")).toBeTruthy();
  });

  it("renders two sections in side-by-side grid layout", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("trending-section-gainers")).toBeTruthy();
      expect(screen.getByTestId("trending-section-losers")).toBeTruthy();
    });

    // The parent container should use grid layout
    const gainersSection = screen.getByTestId("trending-section-gainers");
    const gridContainer = gainersSection.parentElement;
    expect(gridContainer?.className).toContain("grid");
    expect(gridContainer?.className).toContain("md:grid-cols-2");
  });

  it("renders list variant (not card variant) for trending sections", async () => {
    global.fetch = mockFetch() as unknown as typeof fetch;
    renderPage();
    await waitFor(() => {
      // Should render list items, not card tiles
      const listContainers = screen.getAllByTestId("trending-list");
      expect(listContainers.length).toBe(2);
    });
    expect(screen.queryByTestId("trending-card")).toBeNull();
  });
});
