import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CardDetail } from "../../src/pages/CardDetail";
import { fireEvent } from "@testing-library/react";
import {
  mockCardDetail,
  mockPriceHistory,
  mockApiError,
} from "../fixtures/api-responses";
import type { CardDetail as CardDetailType } from "../../src/types/api";

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

function renderCardDetail(id = "1") {
  return render(
    <MemoryRouter initialEntries={[`/cards/${id}`]}>
      <Routes>
        <Route path="/cards/:id" element={<CardDetail />} />
        <Route path="/cards" element={<div data-testid="cards-list">Cards List</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

function createMockFetch(overrides?: {
  detail?: ReturnType<typeof mockCardDetail>;
  history?: ReturnType<typeof mockPriceHistory>;
}) {
  const detailResponse = overrides?.detail ?? mockCardDetail();
  const historyResponse = overrides?.history ?? mockPriceHistory();

  return vi.fn().mockImplementation((url: string) => {
    const urlStr = String(url);

    if (urlStr.includes("/history")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(historyResponse),
      });
    }

    if (urlStr.includes("/api/v1/cards/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(detailResponse),
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

describe("CardDetail page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("shows skeleton loading while fetching", () => {
    globalThis.fetch = vi.fn().mockImplementation(
      () => new Promise(() => {}),
    ) as unknown as typeof fetch;
    renderCardDetail();

    expect(screen.getByTestId("skeleton-info")).toBeDefined();
    expect(screen.getByTestId("skeleton-chart")).toBeDefined();
  });

  it("renders card info panel with correct data", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    const infoPanel = screen.getByTestId("card-info-panel");
    // Card name (EN) — appears in both breadcrumb and info panel
    expect(infoPanel.textContent).toContain("Lightning Bolt");
    // Card name (PT)
    expect(infoPanel.textContent).toContain("Raio");
    // Set code
    expect(infoPanel.textContent).toContain("DMR");
    // Collector number
    expect(infoPanel.textContent).toContain("#123");
    // Game badge
    expect(infoPanel.textContent).toContain("magic");
  });

  it("renders latest price formatted as BRL", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("latest-price")).toBeDefined();
    });

    // 8.5 formatted as BRL
    const priceEl = screen.getByTestId("latest-price");
    expect(priceEl.textContent).toContain("8,50");
  });

  it("renders source links that open in new tab", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("source-link")).toBeDefined();
    });

    const link = screen.getByTestId("source-link");
    expect(link.getAttribute("href")).toBe(
      "https://mypcards.com/magic/12345/lightning-bolt",
    );
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toContain("noopener");
    expect(link.textContent).toContain("MYP Cards");
  });

  it("renders breadcrumb with card name", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("breadcrumb")).toBeDefined();
    });

    const breadcrumb = screen.getByTestId("breadcrumb");
    expect(breadcrumb.textContent).toContain("Cards");
    expect(breadcrumb.textContent).toContain("Lightning Bolt");

    // Cards link navigates to /cards
    const cardsLink = breadcrumb.querySelector("a");
    expect(cardsLink?.getAttribute("href")).toBe("/cards");
  });

  it("renders timestamps", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByText("First tracked")).toBeDefined();
    });

    expect(screen.getByText("01/01/2026")).toBeDefined();
    expect(screen.getByText("18/08/2026")).toBeDefined();
  });

  it("renders the price chart component", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("price-chart")).toBeDefined();
    });
  });

  it("shows 'Card not found' on 404 error", async () => {
    const errorResponse = mockApiError("NOT_FOUND", "Card not found");
    globalThis.fetch = createMockFetch({
      detail: errorResponse as unknown as ReturnType<typeof mockCardDetail>,
    }) as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-not-found")).toBeDefined();
    });

    expect(screen.getByText("Card not found")).toBeDefined();
    // Back link to cards
    const backLink = screen.getByText("Back to Cards");
    expect(backLink.getAttribute("href")).toBe("/cards");
  });

  it("renders Scryfall image when set_code and collector_number exist", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeDefined();
    });

    const img = screen.getByTestId("card-image") as HTMLImageElement;
    expect(img.src).toContain("api.scryfall.com/cards/dmr/123");
    expect(img.src).toContain("version=normal");
    expect(img.alt).toBe("Lightning Bolt");
    expect(img.getAttribute("loading")).toBe("eager");
    expect(img.className).toContain("max-w-[250px]");
  });

  it("renders fallback image by name when set_code is null", async () => {
    const detailNoSet = mockCardDetail();
    (detailNoSet.data as CardDetailType).set_code = null;
    (detailNoSet.data as CardDetailType).collector_number = null;

    globalThis.fetch = createMockFetch({ detail: detailNoSet }) as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    // Should show name-based fallback image (no primary URL available)
    const img = screen.getByTestId("card-image") as HTMLImageElement;
    expect(img.src).toContain("api.scryfall.com/cards/named");
    expect(img.src).toContain("Lightning%20Bolt");
  });

  it("falls back to name-based image when primary URL fails", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeDefined();
    });

    const img = screen.getByTestId("card-image") as HTMLImageElement;
    // Primary URL uses set/number
    expect(img.src).toContain("api.scryfall.com/cards/dmr/123");

    // Trigger error on primary
    fireEvent.error(img);

    // Should now use name-based fallback
    const fallbackImg = screen.getByTestId("card-image") as HTMLImageElement;
    expect(fallbackImg.src).toContain("api.scryfall.com/cards/named");
    expect(fallbackImg.src).toContain("Lightning%20Bolt");
  });

  it("shows placeholder when both primary and fallback images fail", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeDefined();
    });

    const img = screen.getByTestId("card-image") as HTMLImageElement;
    // Trigger primary error
    fireEvent.error(img);
    // Now on fallback — trigger fallback error
    fireEvent.error(screen.getByTestId("card-image"));

    // Should show placeholder
    expect(screen.getByTestId("card-image-placeholder")).toBeDefined();
    expect(screen.queryByTestId("card-image")).toBeNull();
  });

  it("shows updated 404 message with sync hint", async () => {
    const errorResponse = mockApiError("NOT_FOUND", "Card not found");
    globalThis.fetch = createMockFetch({
      detail: errorResponse as unknown as ReturnType<typeof mockCardDetail>,
    }) as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-not-found")).toBeDefined();
    });

    expect(screen.getByText("Card not found. It may not have been synced yet.")).toBeDefined();
  });

  it("renders Scryfall external link with correct URL", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("external-links")).toBeDefined();
    });

    const link = screen.getByTestId("scryfall-link");
    expect(link.getAttribute("href")).toBe(
      `https://scryfall.com/search?q=${encodeURIComponent("Lightning Bolt")}+set:DMR`,
    );
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.textContent).toContain("View on Scryfall");
  });

  it("renders LigaMagic external link with correct URL", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("external-links")).toBeDefined();
    });

    const link = screen.getByTestId("ligamagic-link");
    expect(link.getAttribute("href")).toBe(
      `https://www.ligamagic.com.br/?view=cards/card&card=${encodeURIComponent("Lightning Bolt")}`,
    );
    expect(link.getAttribute("target")).toBe("_blank");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(link.textContent).toContain("View on LigaMagic");
  });

  it("renders Scryfall link without set code when set_code is null", async () => {
    const detailNoSet = mockCardDetail();
    (detailNoSet.data as CardDetailType).set_code = null;
    (detailNoSet.data as CardDetailType).collector_number = null;

    globalThis.fetch = createMockFetch({ detail: detailNoSet }) as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("scryfall-link")).toBeDefined();
    });

    const link = screen.getByTestId("scryfall-link");
    expect(link.getAttribute("href")).toBe(
      `https://scryfall.com/search?q=${encodeURIComponent("Lightning Bolt")}`,
    );
  });

  it("shows 'No price data' when latest_price is null", async () => {
    const detailNoPrice = mockCardDetail();
    (detailNoPrice.data as CardDetailType).latest_price = null;

    globalThis.fetch = createMockFetch({ detail: detailNoPrice }) as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("latest-price")).toBeDefined();
    });

    const priceEl = screen.getByTestId("latest-price");
    expect(priceEl.textContent).toBe("No price data");
    expect(priceEl.className).toContain("text-slate-500");
  });

  it("shows formatted price with currency indicator when price exists", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("latest-price")).toBeDefined();
    });

    const priceEl = screen.getByTestId("latest-price");
    expect(priceEl.textContent).toContain("8,50");
    // Currency indicator should be present
    expect(priceEl.querySelector("[data-testid='currency-indicator-brl']")).toBeDefined();
  });

  it("shows refresh button when collection_entry_id is present", async () => {
    const detailWithEntry = mockCardDetail();
    (detailWithEntry.data as CardDetailType).collection_entry_id = 42;

    globalThis.fetch = createMockFetch({ detail: detailWithEntry }) as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-price-btn")).toBeDefined();
    });
  });

  it("hides refresh button when collection_entry_id is null", async () => {
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    expect(screen.queryByTestId("refresh-price-btn")).toBeNull();
  });

  it("triggers refresh API call and updates price on success", async () => {
    const detailWithEntry = mockCardDetail();
    (detailWithEntry.data as CardDetailType).collection_entry_id = 42;

    globalThis.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      const urlStr = String(url);

      // POST to collection refresh endpoint
      if (urlStr.includes("/collection/42/refresh") && options?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            data: {
              id: 42,
              card_id: 1,
              set_code: "DMR",
              collector_number: "123",
              name_en: "Lightning Bolt",
              name_pt: "Raio",
              quantity: 1,
              quality: null,
              language: null,
              rarity: null,
              color: null,
              extras: null,
              is_foil: false,
              latest_price: 12.50,
              currency: "BRL",
              image_url: null,
              price_history: [],
              source_cards: [],
              scryfall_url: null,
              ligamagic_url: null,
              set_name_en: null,
            },
            meta: { cursor: null, total: null, offset: null, request_id: "req-test" },
            errors: [],
          }),
        });
      }

      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPriceHistory()),
        });
      }

      if (urlStr.includes("/api/v1/cards/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(detailWithEntry),
        });
      }

      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
      });
    }) as unknown as typeof fetch;

    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("refresh-price-btn")).toBeDefined();
    });

    // Click refresh
    fireEvent.click(screen.getByTestId("refresh-price-btn"));

    // Should show success message after refresh
    await waitFor(() => {
      expect(screen.getByTestId("refresh-message")).toBeDefined();
    });

    const msg = screen.getByTestId("refresh-message");
    expect(msg.className).toContain("text-green-400");
  });

  it("shows error banner on non-404 error", async () => {
    const errorResponse = mockApiError("SERVER_ERROR", "Internal server error");
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockPriceHistory()),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(errorResponse),
      });
    }) as unknown as typeof fetch;
    renderCardDetail();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeDefined();
    });

    expect(screen.getByText("Internal server error")).toBeDefined();
  });
});
