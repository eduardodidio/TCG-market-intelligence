import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Cards } from "../../src/pages/Cards";
import {
  mockCardSummaries,
  mockSetSummaries,
  mockApiError,
} from "../fixtures/api-responses";

// Helper to render Cards inside a MemoryRouter
function renderCards(initialPath = "/cards") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Cards />
    </MemoryRouter>,
  );
}

// Helper to create a mock fetch that responds based on URL patterns
function createMockFetch(overrides?: {
  cards?: ReturnType<typeof mockCardSummaries>;
  sets?: ReturnType<typeof mockSetSummaries>;
  cardsPage2?: ReturnType<typeof mockCardSummaries>;
}) {
  const cardsResponse = overrides?.cards ?? mockCardSummaries();
  const setsResponse = overrides?.sets ?? mockSetSummaries();
  const cardsPage2Response = overrides?.cardsPage2 ?? mockCardSummaries(3);

  return vi.fn().mockImplementation((url: string) => {
    const urlStr = typeof url === "string" ? url : String(url);

    if (urlStr.includes("/api/v1/sets")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(setsResponse),
      });
    }

    if (urlStr.includes("/api/v1/cards")) {
      // If request includes cursor param, return page 2
      if (urlStr.includes("cursor=")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(cardsPage2Response),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(cardsResponse),
      });
    }

    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
    });
  });
}

describe("Cards page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders the page title", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards();
    expect(screen.getByText("Explore Cards")).toBeDefined();
  });

  it("shows skeleton loading during initial fetch", () => {
    // Use a fetch that never resolves
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise(() => {}),
    ) as unknown as typeof fetch;
    renderCards();
    expect(screen.getByTestId("skeleton-grid")).toBeDefined();
    const skeletons = screen.getAllByTestId("skeleton-card");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders card tiles after fetching", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByText("Test Card 1")).toBeDefined();
    });
    expect(screen.getByText("Test Card 2")).toBeDefined();
    expect(screen.getByText("Test Card 3")).toBeDefined();
  });

  it("renders cards in a grid container", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("cards-grid")).toBeDefined();
    });
  });

  it("renders filter chips from sets API", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("filter-chips")).toBeDefined();
    });
    expect(screen.getByTestId("filter-chip-all")).toBeDefined();
    expect(screen.getByTestId("filter-chip-DMR")).toBeDefined();
    expect(screen.getByTestId("filter-chip-MH2")).toBeDefined();
  });

  it("renders search input", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards();
    expect(screen.getByTestId("search-input")).toBeDefined();
  });

  it("shows empty state when no cards are returned", async () => {
    const emptyCards = mockCardSummaries(0);
    // Manually fix: mockCardSummaries(0) returns empty array
    globalThis.fetch = createMockFetch({ cards: emptyCards }) as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeDefined();
    });
    expect(screen.getByText("No cards with price data yet. Run a collection sync to fetch prices.")).toBeDefined();
  });

  it("shows error message on API error", async () => {
    const errorResponse = mockApiError("SERVER_ERROR", "Internal server error");
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/api/v1/sets")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSetSummaries()),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(errorResponse),
      });
    }) as unknown as typeof fetch;

    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeDefined();
    });
    expect(screen.getByText("Internal server error")).toBeDefined();
  });

  it("search term update triggers new fetch after debounce", async () => {
    vi.useFakeTimers();
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards();

    // Wait for initial fetch
    await act(async () => {
      vi.advanceTimersByTime(1);
      await Promise.resolve();
    });

    const fetchCallsBefore = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.length;

    // Type in search
    const input = screen.getByTestId("search-input");
    await act(async () => {
      fireEvent.change(input, { target: { value: "Bolt" } });
    });

    // Advance past the debounce delay
    await act(async () => {
      vi.advanceTimersByTime(350);
      await Promise.resolve();
    });

    const fetchCallsAfter = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.length;
    expect(fetchCallsAfter).toBeGreaterThan(fetchCallsBefore);

    // Verify the search term was included in the API call
    const lastCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[fetchCallsAfter - 1];
    expect(String(lastCall[0])).toContain("name=Bolt");

    vi.useRealTimers();
  });

  it("shows 'Load more' button when cursor exists", async () => {
    const cardsWithCursor = mockCardSummaries(24); // cursor is set when n >= 24
    globalThis.fetch = createMockFetch({ cards: cardsWithCursor }) as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("load-more-button")).toBeDefined();
    });
  });

  it("does not show 'Load more' when cursor is null", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch; // 3 cards, no cursor
    renderCards();

    await waitFor(() => {
      expect(screen.getByText("Test Card 1")).toBeDefined();
    });

    expect(screen.queryByTestId("load-more-button")).toBeNull();
  });

  it("clicking 'Load more' appends next page of results", async () => {
    const page1 = mockCardSummaries(24);
    const page2Response = {
      data: [
        {
          id: 100,
          game: "magic",
          name_en: "Page Two Card",
          name_pt: null,
          set_code: "MH2",
          collector_number: "001",
          latest_price: 10.0,
        },
      ],
      meta: { cursor: null, total: 1, request_id: "req-002" },
      errors: [],
    };

    globalThis.fetch = createMockFetch({
      cards: page1,
      cardsPage2: page2Response as ReturnType<typeof mockCardSummaries>,
    }) as unknown as typeof fetch;

    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("load-more-button")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("load-more-button"));

    await waitFor(() => {
      expect(screen.getByText("Page Two Card")).toBeDefined();
    });

    // Original cards should still be visible
    expect(screen.getByText("Test Card 1")).toBeDefined();
  });

  it("selecting a set chip triggers a new fetch with set param", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("filter-chip-DMR")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("filter-chip-DMR"));

    await waitFor(() => {
      // Verify a fetch was made with set=DMR
      const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
      const lastCardCall = calls.filter((c: string[]) =>
        String(c[0]).includes("/api/v1/cards"),
      ).pop();
      expect(String(lastCardCall?.[0])).toContain("set=DMR");
    });
  });
});
