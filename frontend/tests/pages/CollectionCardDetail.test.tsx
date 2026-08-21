import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CollectionCardDetail } from "../../src/pages/CollectionCardDetail";
import type { ApiResponse, CollectionCardDetail as CollectionCardDetailType } from "../../src/types/api";

// Mock Recharts to avoid jsdom SVG rendering issues
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container" style={{ width: 500, height: 300 }}>
        {children}
      </div>
    ),
  };
});

function makeLinkedEntry(
  overrides?: Partial<CollectionCardDetailType>,
): ApiResponse<CollectionCardDetailType> {
  return {
    data: {
      id: 1,
      card_id: 42,
      set_code: "DMR",
      collector_number: "123",
      name_en: "Lightning Bolt",
      name_pt: "Raio",
      set_name_en: "Dominaria Remastered",
      quantity: 3,
      quality: "NM",
      language: "EN",
      rarity: "R",
      color: "R",
      extras: "Foil",
      latest_price: 8.5,
      image_url: "https://api.scryfall.com/cards/dmr/123?format=image&version=normal",
      price_history: [],
      source_cards: [
        {
          source: "myp",
          external_id: "99999",
          sku: "magic_dmr_123",
          url: "https://mypcards.com/magic/99999/lightning-bolt",
        },
      ],
      scryfall_url: "https://scryfall.com/search?q=Lightning+Bolt+set:DMR",
      ligamagic_url: "https://www.ligamagic.com.br/?view=cards/card&card=Lightning+Bolt",
      ...overrides,
    },
    meta: { cursor: null, total: null, request_id: "test-001" },
    errors: [],
  };
}

function makeUnlinkedEntry(): ApiResponse<CollectionCardDetailType> {
  return makeLinkedEntry({
    card_id: null,
    latest_price: null,
    source_cards: [],
    price_history: [],
  });
}

function make404Response(): ApiResponse<null> {
  return {
    data: null,
    meta: { cursor: null, total: null, request_id: "err-001" },
    errors: [{ code: "HTTP_404", message: "Collection entry not found" }],
  };
}

function renderDetail(id = "1") {
  return render(
    <MemoryRouter initialEntries={[`/collection/${id}`]}>
      <Routes>
        <Route path="/collection/:id" element={<CollectionCardDetail />} />
        <Route path="/collection" element={<div data-testid="collection-list">Collection</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function createMockFetch(response: unknown) {
  return vi.fn().mockImplementation((url: string) => {
    const urlStr = String(url);

    // Price chart history call
    if (urlStr.includes("/history")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: [],
            meta: { cursor: null, total: null, request_id: "" },
            errors: [],
          }),
      });
    }

    // Collection detail call
    if (urlStr.includes("/api/v1/collection/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(response),
      });
    }

    return Promise.resolve({
      ok: true,
      json: () =>
        Promise.resolve({
          data: null,
          meta: { cursor: null, total: null, request_id: "" },
          errors: [],
        }),
    });
  });
}

describe("CollectionCardDetail page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders card name, set code, and collector number", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    const panel = screen.getByTestId("card-info-panel");
    expect(panel.textContent).toContain("Lightning Bolt");
    expect(panel.textContent).toContain("Raio");
    expect(panel.textContent).toContain("DMR");
    expect(panel.textContent).toContain("#123");
  });

  it("renders quantity badge when quantity > 1", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("quantity-badge")).toBeDefined();
    });

    expect(screen.getByTestId("quantity-badge").textContent).toBe("x3");
  });

  it("does not render quantity badge when quantity is 1", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry({ quantity: 1 })) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    expect(screen.queryByTestId("quantity-badge")).toBeNull();
  });

  it("renders quality and language badges", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("quality-badge")).toBeDefined();
    });

    expect(screen.getByTestId("quality-badge").textContent).toBe("NM");
    expect(screen.getByTestId("language-badge").textContent).toBe("EN");
  });

  it("renders extras badge", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("extras-badge")).toBeDefined();
    });

    expect(screen.getByTestId("extras-badge").textContent).toBe("Foil");
  });

  it("renders 'Not linked' state for unlinked cards", async () => {
    globalThis.fetch = createMockFetch(makeUnlinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("unlinked-notice")).toBeDefined();
    });

    expect(screen.getByTestId("unlinked-notice").textContent).toContain("Not yet linked");
    expect(screen.getByTestId("no-price-chart")).toBeDefined();
  });

  it("renders price chart for linked cards", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("price-chart")).toBeDefined();
    });
  });

  it("breadcrumb links back to /collection", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("breadcrumb")).toBeDefined();
    });

    const breadcrumb = screen.getByTestId("breadcrumb");
    expect(breadcrumb.textContent).toContain("Collection");
    expect(breadcrumb.textContent).toContain("Lightning Bolt");

    const link = breadcrumb.querySelector("a");
    expect(link?.getAttribute("href")).toBe("/collection");
  });

  it("renders external links (Scryfall and LigaMagic)", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("external-links")).toBeDefined();
    });

    const scryfallLink = screen.getByTestId("scryfall-link");
    expect(scryfallLink.getAttribute("href")).toContain("scryfall.com");
    expect(scryfallLink.getAttribute("target")).toBe("_blank");

    const ligamagicLink = screen.getByTestId("ligamagic-link");
    expect(ligamagicLink.getAttribute("href")).toContain("ligamagic.com.br");
    expect(ligamagicLink.getAttribute("target")).toBe("_blank");
  });

  it("shows 404 state for nonexistent entry", async () => {
    globalThis.fetch = createMockFetch(make404Response()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("entry-not-found")).toBeDefined();
    });

    expect(screen.getByText("Collection entry not found")).toBeDefined();
    const backLink = screen.getByText("Back to Collection");
    expect(backLink.getAttribute("href")).toBe("/collection");
  });

  it("renders latest price formatted as BRL", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("latest-price")).toBeDefined();
    });

    const priceEl = screen.getByTestId("latest-price");
    expect(priceEl.textContent).toContain("8,50");
  });

  it("renders '--' for price when unlinked", async () => {
    globalThis.fetch = createMockFetch(makeUnlinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("latest-price")).toBeDefined();
    });

    expect(screen.getByTestId("latest-price").textContent).toContain("--");
  });
});
