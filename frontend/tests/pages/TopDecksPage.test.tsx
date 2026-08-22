import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TopDecksPage } from "../../src/pages/TopDecksPage";

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/decks/ranking"]}>
      <TopDecksPage />
    </MemoryRouter>,
  );
}

const MOCK_RANKING = {
  data: {
    decks: [
      {
        id: 1,
        name: "Expensive Deck",
        description: null,
        total_cards: 60,
        unique_cards: 20,
        owned_cards: 15,
        ownership_pct: 75.0,
        total_value: 500.0,
        priced_cards: 18,
        unpriced_cards: 2,
        value_change: 25.0,
        value_change_pct: 5.26,
        sparkline: [450, 460, 470, 490, 500],
        currency: "BRL",
        created_at: "2026-08-21T12:00:00",
        updated_at: "2026-08-21T12:00:00",
      },
      {
        id: 2,
        name: "Cheap Deck",
        description: "Budget build",
        total_cards: 40,
        unique_cards: 15,
        owned_cards: 15,
        ownership_pct: 100.0,
        total_value: 50.0,
        priced_cards: 15,
        unpriced_cards: 0,
        value_change: -2.5,
        value_change_pct: -4.76,
        sparkline: [55, 53, 51, 50],
        currency: "BRL",
        created_at: "2026-08-21T12:00:00",
        updated_at: "2026-08-21T12:00:00",
      },
    ],
    total: 2,
    sort_by: "total_value",
    period: "30d",
  },
  meta: { cursor: null, total: null, offset: null, request_id: "r1" },
  errors: [],
};

describe("TopDecksPage", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchSuccess(data: unknown = MOCK_RANKING) {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(data),
    }) as unknown as typeof fetch;
  }

  it("renders page title and controls", async () => {
    mockFetchSuccess();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("page-top-decks")).toBeDefined();
    });

    expect(screen.getByText("Top Decks by Value")).toBeDefined();
    expect(screen.getByTestId("sort-select")).toBeDefined();
    expect(screen.getByTestId("period-selector")).toBeDefined();
  });

  it("renders ranked deck list", async () => {
    mockFetchSuccess();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-list")).toBeDefined();
    });

    expect(screen.getByTestId("ranking-entry-1")).toBeDefined();
    expect(screen.getByTestId("ranking-entry-2")).toBeDefined();
    expect(screen.getByText("Expensive Deck")).toBeDefined();
    expect(screen.getByText("Cheap Deck")).toBeDefined();
  });

  it("shows loading skeletons", () => {
    mockFetchSuccess();
    renderPage();

    expect(screen.getAllByTestId("ranking-skeleton")).toHaveLength(3);
  });

  it("shows empty state when no decks", async () => {
    mockFetchSuccess({
      data: { decks: [], total: 0, sort_by: "total_value", period: "30d" },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-empty")).toBeDefined();
    });

    expect(screen.getByText("No decks to rank yet")).toBeDefined();
  });

  it("shows value with currency", async () => {
    mockFetchSuccess();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-entry-1")).toBeDefined();
    });

    const values = screen.getAllByTestId("deck-value");
    expect(values[0].textContent).toContain("R$ 500.00");
  });

  it("shows green change for positive value_change_pct", async () => {
    mockFetchSuccess();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-entry-1")).toBeDefined();
    });

    const changes = screen.getAllByTestId("value-change");
    expect(changes[0].textContent).toContain("+5.3%");
    expect(changes[0].className).toContain("text-green-400");
  });

  it("shows red change for negative value_change_pct", async () => {
    mockFetchSuccess();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-entry-2")).toBeDefined();
    });

    const changes = screen.getAllByTestId("value-change");
    expect(changes[1].textContent).toContain("-4.8%");
    expect(changes[1].className).toContain("text-red-400");
  });

  it("shows rank numbers", async () => {
    mockFetchSuccess();
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-list")).toBeDefined();
    });

    const ranks = screen.getAllByTestId("rank-number");
    expect(ranks[0].textContent).toBe("1");
    expect(ranks[1].textContent).toBe("2");
  });

  it("shows error on API failure", async () => {
    mockFetchSuccess({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [{ code: "ERR", message: "Server error" }],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-error")).toBeDefined();
    });
  });

  it("shows N/A for null total_value", async () => {
    mockFetchSuccess({
      data: {
        decks: [
          {
            ...MOCK_RANKING.data.decks[0],
            total_value: null,
            value_change_pct: null,
          },
        ],
        total: 1,
        sort_by: "total_value",
        period: "30d",
      },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("ranking-entry-1")).toBeDefined();
    });

    const values = screen.getAllByTestId("deck-value");
    expect(values[0].textContent).toContain("N/A");
  });
});
