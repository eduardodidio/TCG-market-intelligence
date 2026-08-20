import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MyCollection } from "../../src/pages/MyCollection";
import { mockCollectionSummary } from "../fixtures/api-responses";
import type { ApiResponse, CollectionCard } from "../../src/types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, request_id: "req-test" },
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
    latest_price: 5.0,
    image_url: null,
    ...overrides,
  };
}

function createMockFetch(cards: CollectionCard[]) {
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
    if (urlStr.includes("/collection")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(envelope(cards)),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve(envelope(null)),
    });
  });
}

function renderMyCollection() {
  return render(
    <MemoryRouter initialEntries={["/collection"]}>
      <MyCollection />
    </MemoryRouter>,
  );
}

describe("MyCollection — price display", () => {
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

describe("MyCollection — card navigation", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("linked card (with card_id) navigates to /cards/{card_id}", async () => {
    const card = makeCollectionCard({ id: 10, card_id: 42 });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-10")).toBeDefined();
    });

    const tile = screen.getByTestId("collection-card-10");
    const link = tile.closest("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe("/cards/42");
    // Should be an internal link (no target="_blank")
    expect(link?.getAttribute("target")).toBeNull();
  });

  it("unlinked card (no card_id) navigates to internal Explore page with filters", async () => {
    const card = makeCollectionCard({ id: 20, card_id: null, name_en: "Counterspell", set_code: "MH2" });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-20")).toBeDefined();
    });

    const tile = screen.getByTestId("collection-card-20");
    const link = tile.closest("a");
    expect(link).not.toBeNull();
    expect(link?.getAttribute("href")).toBe(
      `/cards?name=${encodeURIComponent("Counterspell")}&set=MH2`,
    );
    // Should be an internal link (no target="_blank")
    expect(link?.getAttribute("target")).toBeNull();
  });

  it("unlinked card without name uses only set filter", async () => {
    const card = makeCollectionCard({ id: 30, card_id: null, name_en: null, name_pt: null, set_code: "DMR" });
    globalThis.fetch = createMockFetch([card]) as unknown as typeof fetch;
    renderMyCollection();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-30")).toBeDefined();
    });

    const tile = screen.getByTestId("collection-card-30");
    const link = tile.closest("a");
    expect(link).not.toBeNull();
    // "Unknown Card" should NOT be sent as the name filter
    expect(link?.getAttribute("href")).toBe("/cards?set=DMR");
  });
});

describe("MyCollection — infinite scroll", () => {
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

describe("MyCollection — summary KPI", () => {
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
