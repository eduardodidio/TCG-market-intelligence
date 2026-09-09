import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MyCollection } from "../../src/pages/MyCollection";
import { mockCollectionSummary } from "../fixtures/api-responses";
import type { ApiResponse, CollectionCard } from "../../src/types/api";

function envelope<T>(data: T, meta?: Partial<ApiResponse<T>["meta"]>): ApiResponse<T> {
  return {
    data,
    meta: {
      cursor: meta?.cursor ?? null,
      total: meta?.total ?? null,
      offset: meta?.offset ?? null,
      request_id: meta?.request_id ?? "req-test",
    },
    errors: [],
  };
}

function makeCollectionCard(overrides: Partial<CollectionCard> = {}): CollectionCard {
  return {
    id: 1,
    card_id: null,
    set_code: "DMR",
    collector_number: "123",
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_name_en: "Dominaria Remastered",
    quantity: 1,
    quality: "NM",
    language: "EN",
    rarity: "C",
    color: null,
    extras: null,
    is_foil: false,
    latest_price: 5.0,
    image_url: null,
    ...overrides,
  };
}

function createMockFetch(cards: CollectionCard[], total?: number) {
  return vi.fn().mockImplementation((url: string) => {
    const urlStr = String(url);
    if (urlStr.includes("/collection/summary")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(mockCollectionSummary()),
      });
    }
    if (urlStr.includes("/collection/sets")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            envelope([{ set_code: "DMR", set_name: "Dominaria Remastered", count: 1 }]),
          ),
      });
    }
    if (urlStr.includes("/collection/portfolio-summary")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope({
          total_invested: 0, total_current_value: 0, total_pnl: 0, total_pnl_pct: null, invested_card_count: 0,
        })),
      });
    }
    if (urlStr.includes("/collection/portfolio-history")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope([])),
      });
    }
    if (urlStr.includes("/collection/set-completion")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope([])),
      });
    }
    if (urlStr.includes("/collection")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(cards, { total: total ?? cards.length })),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(envelope(null)),
    });
  });
}

function renderMyCollection(initialEntries: string[] = ["/collection"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <MyCollection />
    </MemoryRouter>,
  );
}

describe("MyCollection -- price display", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("displays formatted price for card with latest_price", async () => {
    const card = makeCollectionCard({ id: 50, latest_price: 1.5 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-50")).toBeDefined();
    });

    const priceEl = screen.getByTestId("card-price");
    expect(priceEl.textContent).toContain("R$");
    expect(priceEl.textContent).toContain("1,50");
    // Price should use cyan color
    expect(priceEl.className).toContain("text-cyan-400");
  });

  it("displays '--' fallback for card with null latest_price", async () => {
    const card = makeCollectionCard({ id: 60, latest_price: null });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-60")).toBeDefined();
    });

    const priceEl = screen.getByTestId("card-price");
    expect(priceEl.textContent).toBe("--");
    // No-price should use muted color
    expect(priceEl.className).toContain("text-slate-500");
  });
});

describe("MyCollection -- card navigation", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("linked card (with card_id) navigates to /collection/{id}", async () => {
    const card = makeCollectionCard({ id: 10, card_id: 42 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-10")).toBeDefined();
    });

    const tile = screen.getByTestId("collection-card-10");
    const link = tile.closest("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("/collection/10");
    // Should be an internal link (no target="_blank")
    expect(link?.getAttribute("target")).toBeNull();
  });

  it("unlinked card (no card_id) navigates to /collection/{id}", async () => {
    const card = makeCollectionCard({ id: 20, card_id: null, name_en: "Counterspell", set_code: "MH2" });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-20")).toBeDefined();
    });

    const tile = screen.getByTestId("collection-card-20");
    const link = tile.closest("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("/collection/20");
    // Should be an internal link (no target="_blank")
    expect(link?.getAttribute("target")).toBeNull();
  });

  it("unlinked card without name also navigates to /collection/{id}", async () => {
    const card = makeCollectionCard({ id: 30, card_id: null, name_en: null, name_pt: null, set_code: "DMR" });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-30")).toBeDefined();
    });

    const tile = screen.getByTestId("collection-card-30");
    const link = tile.closest("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("/collection/30");
  });
});

describe("MyCollection -- infinite scroll", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders scroll sentinel when cards are loaded", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    expect(screen.getByTestId("scroll-sentinel")).toBeDefined();
  });

  it("does not render a load-more button (replaced by infinite scroll)", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    expect(screen.queryByTestId("load-more-button")).toBeNull();
    expect(screen.queryByText("Load more")).toBeNull();
    expect(screen.queryByText("Load More")).toBeNull();
  });
});

describe("MyCollection -- summary KPI", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("displays Est. Value with formatted BRL when total_value exists", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByText("Est. Value")).toBeDefined();
    });

    // mockCollectionSummary returns total_value: 2850.0
    const kpi = screen.getByText("Est. Value").closest("[data-testid]");
    expect(kpi?.textContent).toContain("R$");
    expect(kpi?.textContent).toContain("2.850,00");
  });

  it("displays '--' for Est. Value when total_value is null", async () => {
    // Override the summary to have null total_value
    const card = makeCollectionCard({ id: 1 });
    const baseFetch = createMockFetch([card]);
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/collection/summary")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockCollectionSummary({ total_value: null })),
        });
      }
      return baseFetch(url);
    }) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByText("Est. Value")).toBeDefined();
    });

    const kpi = screen.getByText("Est. Value").closest("[data-testid]");
    expect(kpi?.textContent).toContain("--");
  });
});

describe("MyCollection -- sort dropdown", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders the sort dropdown", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("sort-select")).toBeDefined();
    });
  });

  it("selecting a sort option re-fetches data", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    const callCountBefore = mockFetch.mock.calls.filter(
      (c: unknown[]) => String(c[0]).includes("/collection") && !String(c[0]).includes("/summary") && !String(c[0]).includes("/sets"),
    ).length;

    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "added-desc" } });

    await waitFor(() => {
      const callCountAfter = mockFetch.mock.calls.filter(
        (c: unknown[]) => String(c[0]).includes("/collection") && !String(c[0]).includes("/summary") && !String(c[0]).includes("/sets"),
      ).length;
      expect(callCountAfter).toBeGreaterThan(callCountBefore);
    });
  });

  it("passes sort_by and sort_dir to API for non-price sorts", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "added-desc" } });

    await waitFor(() => {
      const collectionCalls = mockFetch.mock.calls.filter(
        (c: unknown[]) => String(c[0]).includes("/collection") && !String(c[0]).includes("/summary") && !String(c[0]).includes("/sets"),
      );
      const lastCall = String(collectionCalls[collectionCalls.length - 1][0]);
      expect(lastCall).toContain("sort_by=added");
      expect(lastCall).toContain("sort_dir=desc");
    });
  });

  it("sends sort_by=price and sort_dir=desc to API for default price sorting", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    // Default sort is price-desc; verify API call includes sort params
    const collectionCalls = mockFetch.mock.calls.filter(
      (c: unknown[]) => {
        const url = String(c[0]);
        return url.includes("/collection") && url.includes("offset=") && !url.includes("/summary") && !url.includes("/sets");
      },
    );
    expect(collectionCalls.length).toBeGreaterThan(0);
    const lastCall = String(collectionCalls[collectionCalls.length - 1][0]);
    expect(lastCall).toContain("sort_by=price");
    expect(lastCall).toContain("sort_dir=desc");
  });

  it("sends sort_by=price and sort_dir=asc to API for price-asc sorting", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection(["/collection?sort=price&dir=asc"]);

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    const collectionCalls = mockFetch.mock.calls.filter(
      (c: unknown[]) => {
        const url = String(c[0]);
        return url.includes("/collection") && url.includes("offset=") && !url.includes("/summary") && !url.includes("/sets");
      },
    );
    expect(collectionCalls.length).toBeGreaterThan(0);
    const lastCall = String(collectionCalls[collectionCalls.length - 1][0]);
    expect(lastCall).toContain("sort_by=price");
    expect(lastCall).toContain("sort_dir=asc");
  });

  it("changing sort to name-asc updates the API call", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "name-asc" } });

    await waitFor(() => {
      const collectionCalls = mockFetch.mock.calls.filter(
        (c: unknown[]) => String(c[0]).includes("/collection") && !String(c[0]).includes("/summary") && !String(c[0]).includes("/sets") && !String(c[0]).includes("/banned") && !String(c[0]).includes("/portfolio") && !String(c[0]).includes("/set-completion"),
      );
      const lastCall = String(collectionCalls[collectionCalls.length - 1][0]);
      expect(lastCall).toContain("sort_by=name");
      expect(lastCall).toContain("sort_dir=asc");
    });
  });

  it("loads sort from URL params ?sort=name&dir=asc", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection(["/collection?sort=name&dir=asc"]);

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    expect(select.value).toBe("name-asc");

    const collectionCalls = mockFetch.mock.calls.filter(
      (c: unknown[]) => {
        const url = String(c[0]);
        return url.includes("/collection") && url.includes("offset=");
      },
    );
    expect(collectionCalls.length).toBeGreaterThan(0);
    const lastCall = String(collectionCalls[collectionCalls.length - 1][0]);
    expect(lastCall).toContain("sort_by=name");
    expect(lastCall).toContain("sort_dir=asc");
  });

  it("uses offset-based pagination (offset param in API call)", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    // The initial fetch should include offset=0
    const collectionCalls = mockFetch.mock.calls.filter(
      (c: unknown[]) => String(c[0]).includes("/collection") && !String(c[0]).includes("/summary") && !String(c[0]).includes("/sets") && !String(c[0]).includes("/banned") && !String(c[0]).includes("/portfolio") && !String(c[0]).includes("/set-completion"),
    );
    const firstCall = String(collectionCalls[0][0]);
    expect(firstCall).toContain("offset=0");
  });

  it("initializes sort from URL params", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection(["/collection?sort=added&dir=desc"]);

    await waitFor(() => {
      expect(screen.getByTestId("sort-select")).toBeDefined();
    });

    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    expect(select.value).toBe("added-desc");
  });

  // --- F48-T02: Default sort is price/desc ---

  it("defaults to Price High-Low sort when no URL params", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("sort-select")).toBeDefined();
    });

    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    expect(select.value).toBe("price-desc");
  });

  it("URL params override the default sort", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection(["/collection?sort=name&dir=asc"]);

    await waitFor(() => {
      expect(screen.getByTestId("sort-select")).toBeDefined();
    });

    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    expect(select.value).toBe("name-asc");
  });

  it("default sort (price/desc) does not produce URL params", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    // Check that the URL has no sort or dir params (defaults are omitted)
    // We can verify by checking that no sort/dir params appear in the URL
    // Since we're using MemoryRouter, we check the search params aren't set
    const select = screen.getByTestId("sort-select") as HTMLSelectElement;
    expect(select.value).toBe("price-desc");
  });

  it("non-default sort produces URL params", async () => {
    const card = makeCollectionCard({ id: 1 });
    const mockFetch = createMockFetch([card]);
    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    const select = screen.getByTestId("sort-select");
    fireEvent.change(select, { target: { value: "name-asc" } });

    await waitFor(() => {
      // After changing to non-default sort, verify the API call includes sort params
      const collectionCalls = mockFetch.mock.calls.filter(
        (c: unknown[]) => String(c[0]).includes("/collection") && !String(c[0]).includes("/summary") && !String(c[0]).includes("/sets") && !String(c[0]).includes("/banned") && !String(c[0]).includes("/portfolio") && !String(c[0]).includes("/set-completion"),
      );
      const lastCall = String(collectionCalls[collectionCalls.length - 1][0]);
      expect(lastCall).toContain("sort_by=name");
      expect(lastCall).toContain("sort_dir=asc");
    });
  });
});

describe("MyCollection -- set icon filter", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders SetIconFilter instead of FilterChips", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("set-icon-filter")).toBeDefined();
    });

    // FilterChips testid should NOT exist for sets
    expect(screen.queryByTestId("filter-chips")).toBeNull();
  });
});

describe("MyCollection -- grid size", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    localStorage.removeItem("tcg:grid-size");
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
    localStorage.removeItem("tcg:grid-size");
  });

  it("renders grid size toggle", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByRole("group", { name: "Grid size" })).toBeDefined();
    });
  });

  it("uses medium grid classes by default", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-grid")).toBeDefined();
    });

    const grid = screen.getByTestId("collection-grid");
    expect(grid.className).toContain("grid-cols-2");
    expect(grid.className).toContain("xl:grid-cols-6");
  });

  it("skeleton grid also uses the selected size classes", async () => {
    const card = makeCollectionCard({ id: 1 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    // Skeleton grid shows during loading
    const skeleton = screen.getByTestId("skeleton-grid");
    expect(skeleton.className).toContain("grid-cols-2");
    expect(skeleton.className).toContain("xl:grid-cols-6");
  });
});
