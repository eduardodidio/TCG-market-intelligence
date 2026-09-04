import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CatalogPage } from "../../src/pages/CatalogPage";
import type { ApiResponse } from "../../src/types/api";
import type { CatalogCardsResponse } from "../../src/hooks/useCatalogCards";
import type { CatalogSet } from "../../src/hooks/useCatalogSets";
import type { CatalogStats } from "../../src/hooks/useCatalogStats";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function mockCatalogCards(n = 3, offset = 0, total = 3): CatalogCardsResponse {
  return {
    items: Array.from({ length: n }, (_, i) => ({
      id: offset + i + 1,
      name_en: `Catalog Card ${offset + i + 1}`,
      name_pt: `Carta Catalogo ${offset + i + 1}`,
      set_code: "DMR",
      collector_number: String(offset + i + 1).padStart(3, "0"),
      rarity: i % 2 === 0 ? "rare" : "common",
      color_identity: "W,U",
      mana_cost: "{2}{W}",
      type_line: "Creature",
      image_uri: `https://example.com/card-${offset + i + 1}.jpg`,
      liga_price: i === 0 ? 15.5 : null,
      liga_price_date: i === 0 ? "2026-09-01" : null,
    })),
    total,
    limit: 50,
    offset,
  };
}

function mockCatalogSets(): CatalogSet[] {
  return [
    { set_code: "DMR", card_count: 300, priced_count: 150 },
    { set_code: "MH2", card_count: 250, priced_count: 100 },
  ];
}

function mockCatalogStatsData(): CatalogStats {
  return {
    total_cards: 5000,
    total_sets: 120,
    cards_with_price: 3000,
    cards_without_price: 2000,
  };
}

function createMockFetch(overrides?: {
  cards?: CatalogCardsResponse;
  sets?: CatalogSet[];
  stats?: CatalogStats;
  cardsError?: boolean;
}) {
  const cardsResponse = overrides?.cards ?? mockCatalogCards();
  const setsResponse = overrides?.sets ?? mockCatalogSets();
  const statsResponse = overrides?.stats ?? mockCatalogStatsData();
  const cardsError = overrides?.cardsError ?? false;

  return vi.fn().mockImplementation((url: string) => {
    const urlStr = typeof url === "string" ? url : String(url);

    if (urlStr.includes("/catalog/stats")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(statsResponse)),
      });
    }

    if (urlStr.includes("/catalog/sets")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(setsResponse)),
      });
    }

    if (urlStr.includes("/catalog/cards")) {
      if (cardsError) {
        return Promise.resolve({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
          json: () => Promise.resolve({ detail: "Server error" }),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(cardsResponse)),
      });
    }

    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({ data: null, meta: { cursor: null, total: null, offset: null, request_id: "" }, errors: [] }),
    });
  });
}

function renderCatalog(initialPath = "/catalog") {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <CatalogPage />
    </MemoryRouter>,
  );
}

describe("CatalogPage", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  it("renders without crash and shows the page heading", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    expect(screen.getByTestId("page-catalog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 2, name: "Card Catalog" })).toBeInTheDocument();
  });

  it("shows stats summary when data loads", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-stats")).toBeInTheDocument();
    });

    // toLocaleString() format varies by environment, so check for digits
    expect(screen.getByTestId("catalog-stats")).toHaveTextContent(/5.?000/);
    expect(screen.getByTestId("catalog-stats")).toHaveTextContent("120");
    expect(screen.getByTestId("catalog-stats")).toHaveTextContent(/3.?000/);
  });

  it("shows card grid with prices", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    // Check card with price shows the price
    const prices = screen.getAllByTestId("card-price");
    expect(prices[0]).toHaveTextContent("R$ 15.50");
    // Card without price shows fallback
    expect(prices[1]).toHaveTextContent("No price data");
  });

  it("shows card names and set codes", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    expect(screen.getByText("Catalog Card 1")).toBeInTheDocument();
    expect(screen.getByText("Catalog Card 2")).toBeInTheDocument();
  });

  it("shows empty state when API returns 0 results", async () => {
    const emptyCards = mockCatalogCards(0, 0, 0);
    globalThis.fetch = createMockFetch({ cards: emptyCards }) as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });

    expect(screen.getByTestId("empty-state-title")).toHaveTextContent("No cards found");
  });

  it("shows empty state with clear filters action when filters are active", async () => {
    const emptyCards = mockCatalogCards(0, 0, 0);
    globalThis.fetch = createMockFetch({ cards: emptyCards }) as unknown as typeof fetch;
    renderCatalog("/catalog?rarity=mythic");

    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeInTheDocument();
    });

    expect(screen.getByTestId("empty-state-description")).toHaveTextContent(
      "No cards match the current filters",
    );
    expect(screen.getByTestId("empty-state-actions")).toBeInTheDocument();
  });

  it("search input triggers query with debounce", async () => {
    const mockFetch = createMockFetch();
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    const searchInput = screen.getByTestId("search-input");
    await act(async () => {
      fireEvent.change(searchInput, { target: { value: "Lightning" } });
    });

    // Advance past the 300ms debounce
    await act(async () => {
      vi.advanceTimersByTime(350);
    });

    // Verify fetch was called with the name param
    await waitFor(() => {
      const calls = mockFetch.mock.calls.map((c: unknown[]) => String(c[0]));
      const cardCalls = calls.filter((u: string) => u.includes("/catalog/cards"));
      const lastCardCall = cardCalls[cardCalls.length - 1];
      expect(lastCardCall).toContain("name=Lightning");
    });
  });

  it("filter section toggles when button is clicked", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    // Filter section should not be visible initially
    expect(screen.queryByTestId("filter-section")).not.toBeInTheDocument();

    // Click the filters button
    fireEvent.click(screen.getByTestId("toggle-filters-btn"));

    // Filter section should now be visible
    expect(screen.getByTestId("filter-section")).toBeInTheDocument();
    expect(screen.getByTestId("set-select")).toBeInTheDocument();
  });

  it("rarity chips toggle on click", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    // Open filters
    fireEvent.click(screen.getByTestId("toggle-filters-btn"));

    const rarityChip = screen.getByTestId("rarity-chip-R");
    expect(rarityChip).toBeInTheDocument();

    // Click to select
    fireEvent.click(rarityChip);
    expect(rarityChip).toHaveClass("bg-cyan-500");

    // Click again to deselect
    fireEvent.click(rarityChip);
    expect(rarityChip).toHaveClass("bg-slate-700");
  });

  it("color identity chips toggle on click", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    // Open filters
    fireEvent.click(screen.getByTestId("toggle-filters-btn"));

    const colorChip = screen.getByTestId("color-chip-W");
    expect(colorChip).toBeInTheDocument();

    // Click to select
    fireEvent.click(colorChip);
    expect(colorChip).toHaveClass("ring-2");
  });

  it("shows load more button when there are more results", async () => {
    const cardsWithMore = mockCatalogCards(3, 0, 100);
    globalThis.fetch = createMockFetch({ cards: cardsWithMore }) as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    expect(screen.getByTestId("load-more-btn")).toBeInTheDocument();
    expect(screen.getByTestId("load-more-btn")).toHaveTextContent("Load More");
  });

  it("does not show load more button when all results are loaded", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("load-more-btn")).not.toBeInTheDocument();
  });

  it("cards link to detail page", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    const firstCard = screen.getByTestId("catalog-card-1");
    expect(firstCard).toBeInTheDocument();
    // The CatalogCardTile is a Link (a tag) itself
    expect(firstCard).toHaveAttribute("href", "/cards/1");
  });

  it("shows rarity badges on cards", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    const rarityBadges = screen.getAllByTestId("rarity-badge");
    expect(rarityBadges.length).toBeGreaterThan(0);
  });

  it("uses lazy loading on card images", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    const images = screen.getAllByRole("img");
    images.forEach((img) => {
      expect(img).toHaveAttribute("loading", "lazy");
    });
  });

  it("shows breadcrumb with Home > Catalog", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    const breadcrumb = screen.getByTestId("breadcrumb");
    expect(breadcrumb).toBeInTheDocument();
    expect(breadcrumb).toHaveTextContent("Dashboard");
    expect(breadcrumb).toHaveTextContent("Card Catalog");
  });

  it("has price filter toggle buttons", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("catalog-grid")).toBeInTheDocument();
    });

    // Open filters
    fireEvent.click(screen.getByTestId("toggle-filters-btn"));

    expect(screen.getByTestId("has-price-btn")).toBeInTheDocument();
    expect(screen.getByTestId("no-price-btn")).toBeInTheDocument();
  });

  it("shows results count", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCatalog();

    await waitFor(() => {
      expect(screen.getByTestId("results-count")).toBeInTheDocument();
    });

    expect(screen.getByTestId("results-count")).toHaveTextContent("3 results");
  });
});
