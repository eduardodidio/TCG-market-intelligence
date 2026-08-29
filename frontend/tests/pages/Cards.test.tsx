import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Cards } from "../../src/pages/Cards";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";
import {
  mockCardSummaries,
  mockSetSummaries,
  mockApiError,
} from "../fixtures/api-responses";

// Default auth context (not authenticated)
const defaultAuth: AuthContextValue = {
  user: null,
  loading: false,
  error: null,
  isAuthenticated: false,
  mustChangePassword: false,
  login: async () => null,
  register: async () => null,
  logout: async () => {},
  changePassword: async () => null,
};

const authenticatedAuth: AuthContextValue = {
  ...defaultAuth,
  user: { id: 1, email: "test@test.com", display_name: "Test", is_admin: false, is_active: true, preferred_currency: "BRL", preferred_language: "en" },
  isAuthenticated: true,
};

// Helper to render Cards inside a MemoryRouter with optional auth
function renderCards(initialPath = "/cards", auth: AuthContextValue = defaultAuth) {
  return render(
    <AuthContext.Provider value={auth}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Cards />
      </MemoryRouter>
    </AuthContext.Provider>,
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

  it("renders scroll sentinel when cursor exists", async () => {
    const cardsWithCursor = mockCardSummaries(24); // cursor is set when n >= 24
    globalThis.fetch = createMockFetch({ cards: cardsWithCursor }) as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("scroll-sentinel")).toBeDefined();
    });
  });

  it("renders scroll sentinel even when cursor is null (disabled observer)", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch; // 3 cards, no cursor
    renderCards();

    await waitFor(() => {
      expect(screen.getByText("Test Card 1")).toBeDefined();
    });

    // Sentinel is always rendered when cards exist; observer just won't fire
    expect(screen.getByTestId("scroll-sentinel")).toBeDefined();
    // No load-more button should exist
    expect(screen.queryByTestId("load-more-button")).toBeNull();
  });

  it("does not show load-more button (replaced by infinite scroll)", async () => {
    const cardsWithCursor = mockCardSummaries(24);
    globalThis.fetch = createMockFetch({ cards: cardsWithCursor }) as unknown as typeof fetch;
    renderCards();

    await waitFor(() => {
      expect(screen.getByTestId("cards-grid")).toBeDefined();
    });

    expect(screen.queryByTestId("load-more-button")).toBeNull();
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

  it("does not show mode toggle when not authenticated", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards("/cards", defaultAuth);

    await waitFor(() => {
      expect(screen.getByText("Explore Cards")).toBeDefined();
    });
    expect(screen.queryByTestId("mode-toggle")).toBeNull();
  });

  it("shows mode toggle when authenticated", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCards("/cards", authenticatedAuth);

    await waitFor(() => {
      expect(screen.getByTestId("mode-toggle")).toBeDefined();
    });
    expect(screen.getByTestId("mode-local")).toBeDefined();
    expect(screen.getByTestId("mode-web")).toBeDefined();
  });
});

describe("Cards page — Web Search", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function createWebSearchFetch(webResults: unknown[] = [], webError?: { status: number; detail: string }) {
    return vi.fn().mockImplementation((url: string, init?: RequestInit) => {
      const urlStr = typeof url === "string" ? url : String(url);

      if (urlStr.includes("/api/v1/sets")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSetSummaries()),
        });
      }

      if (urlStr.includes("/api/v1/cards/search-web")) {
        if (webError) {
          return Promise.resolve({
            ok: false,
            status: webError.status,
            statusText: "Error",
            json: () => Promise.resolve({ detail: webError.detail }),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            data: webResults,
            meta: { cursor: null, total: null, offset: null, request_id: "test" },
            errors: [],
          }),
        });
      }

      if (urlStr.includes("/api/v1/cards")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockCardSummaries()),
        });
      }

      if (urlStr.includes("/api/v1/collection/batch")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            data: { added: 1, errors: [] },
            meta: { cursor: null, total: null, offset: null, request_id: "test" },
            errors: [],
          }),
        });
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
      });
    });
  }

  async function switchToWebMode() {
    // Wait for initial local mode load
    await waitFor(() => {
      expect(screen.getByTestId("mode-toggle")).toBeDefined();
    });
    fireEvent.click(screen.getByTestId("mode-web"));
    await waitFor(() => {
      expect(screen.getByTestId("web-search-section")).toBeDefined();
    });
  }

  it("toggles between Local and Web Search mode", async () => {
    globalThis.fetch = createWebSearchFetch() as unknown as typeof fetch;
    renderCards("/cards", authenticatedAuth);

    await waitFor(() => {
      expect(screen.getByTestId("mode-toggle")).toBeDefined();
    });

    // Default is local mode
    expect(screen.queryByTestId("web-search-section")).toBeNull();

    // Switch to web
    fireEvent.click(screen.getByTestId("mode-web"));
    await waitFor(() => {
      expect(screen.getByTestId("web-search-section")).toBeDefined();
    });

    // Switch back to local
    fireEvent.click(screen.getByTestId("mode-local"));
    await waitFor(() => {
      expect(screen.queryByTestId("web-search-section")).toBeNull();
    });
  });

  it("search calls API with query", async () => {
    const mockResults = [
      {
        card_name: "Lightning Bolt",
        set_name: null,
        liga_url: "https://ligamagic.com.br/?view=cards/card&card=Lightning+Bolt",
        normal_price: 2.5,
        foil_price: 10.0,
        image_url: null,
        local_card_id: null,
      },
    ];

    globalThis.fetch = createWebSearchFetch(mockResults) as unknown as typeof fetch;
    renderCards("/cards", authenticatedAuth);
    await switchToWebMode();

    // Type query
    const input = screen.getByTestId("web-search-input");
    fireEvent.change(input, { target: { value: "Lightning Bolt" } });

    // Click search
    fireEvent.click(screen.getByTestId("web-search-btn"));

    // Should call API
    await waitFor(() => {
      const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
      const searchCall = calls.find((c: unknown[]) =>
        String(c[0]).includes("search-web"),
      );
      expect(searchCall).toBeDefined();
      expect(String(searchCall![0])).toContain("q=Lightning+Bolt");
    });
  });

  it("results render with name and price", async () => {
    const mockResults = [
      {
        card_name: "Lightning Bolt",
        set_name: null,
        liga_url: "https://example.com",
        normal_price: 2.5,
        foil_price: 10.0,
        image_url: null,
        local_card_id: null,
      },
    ];

    globalThis.fetch = createWebSearchFetch(mockResults) as unknown as typeof fetch;
    renderCards("/cards", authenticatedAuth);
    await switchToWebMode();

    fireEvent.change(screen.getByTestId("web-search-input"), { target: { value: "Bolt" } });
    fireEvent.click(screen.getByTestId("web-search-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("web-results-grid")).toBeDefined();
    });

    expect(screen.getByText("Lightning Bolt")).toBeDefined();
    expect(screen.getByText("Normal: R$ 2.50")).toBeDefined();
    expect(screen.getByText("Foil: R$ 10.00")).toBeDefined();
  });

  it("cooldown disables search button for 3 seconds", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    globalThis.fetch = createWebSearchFetch([]) as unknown as typeof fetch;
    renderCards("/cards", authenticatedAuth);

    // Wait for mode toggle
    await act(async () => {
      vi.advanceTimersByTime(500);
    });

    // Switch to web mode
    await act(async () => {
      fireEvent.click(screen.getByTestId("mode-web"));
    });

    await act(async () => {
      fireEvent.change(screen.getByTestId("web-search-input"), { target: { value: "Test" } });
    });

    // Click search
    await act(async () => {
      fireEvent.click(screen.getByTestId("web-search-btn"));
    });

    // Wait for search to resolve
    await act(async () => {
      vi.advanceTimersByTime(100);
    });

    // Button should be disabled (cooldown)
    const btn = screen.getByTestId("web-search-btn");
    expect(btn).toHaveProperty("disabled", true);

    // Advance past cooldown
    await act(async () => {
      vi.advanceTimersByTime(3100);
    });

    // Button should be re-enabled (query still filled)
    expect(screen.getByTestId("web-search-btn")).toHaveProperty("disabled", false);

    vi.useRealTimers();
  });

  it("Add to Evaluation button is enabled and clickable", async () => {
    const mockResults = [
      {
        card_name: "Test Card",
        set_name: null,
        liga_url: null,
        normal_price: 5.0,
        foil_price: null,
        image_url: null,
        local_card_id: null,
      },
    ];

    globalThis.fetch = createWebSearchFetch(mockResults) as unknown as typeof fetch;
    renderCards("/cards", authenticatedAuth);

    // Wait for initial load, then switch to web mode
    await waitFor(() => expect(screen.getByTestId("mode-web")).toBeDefined());
    fireEvent.click(screen.getByTestId("mode-web"));
    await waitFor(() => expect(screen.getByTestId("web-search-section")).toBeDefined());

    fireEvent.change(screen.getByTestId("web-search-input"), { target: { value: "Test" } });
    fireEvent.click(screen.getByTestId("web-search-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("web-results-grid")).toBeDefined();
    });

    const evalBtn = screen.getByTestId("add-to-evaluation-btn");
    expect(evalBtn).toHaveProperty("disabled", false);
  });

  it("shows no results message when search returns empty", async () => {
    globalThis.fetch = createWebSearchFetch([]) as unknown as typeof fetch;
    renderCards("/cards", authenticatedAuth);

    await waitFor(() => expect(screen.getByTestId("mode-web")).toBeDefined());
    fireEvent.click(screen.getByTestId("mode-web"));
    await waitFor(() => expect(screen.getByTestId("web-search-section")).toBeDefined());

    fireEvent.change(screen.getByTestId("web-search-input"), { target: { value: "xyz123" } });
    fireEvent.click(screen.getByTestId("web-search-btn"));

    await waitFor(() => {
      expect(screen.getByText("No results found")).toBeDefined();
    });
  });
});
