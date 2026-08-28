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
      is_foil: true,
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
    meta: { cursor: null, total: null, offset: null, request_id: "test-001" },
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
    meta: { cursor: null, total: null, offset: null, request_id: "err-001" },
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

    // Legality endpoint (F42)
    if (urlStr.includes("/legality")) {
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

    // Metrics endpoint
    if (urlStr.includes("/metrics")) {
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve({
            data: null,
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

  it("renders ban history section when card_id is present", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-section")).toBeDefined();
    });

    expect(screen.getByTestId("ban-history-toggle")).toBeDefined();
  });

  it("hides ban history section when card_id is null", async () => {
    globalThis.fetch = createMockFetch(makeUnlinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("page-collection-detail")).toBeDefined();
    });

    expect(screen.queryByTestId("ban-history-section")).toBeNull();
  });

  it("ban history section is collapsed by default", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-section")).toBeDefined();
    });

    expect(screen.queryByTestId("ban-history-content")).toBeNull();
  });

  it("expanding ban history section triggers fetch", async () => {
    const mockBanHistory = {
      data: [
        {
          id: 1,
          format: "standard",
          old_status: "legal",
          new_status: "banned",
          changed_at: "2026-08-01T00:00:00",
          source: "scryfall_sync",
        },
      ],
      meta: { cursor: null, total: null, offset: null, request_id: "bh1" },
      errors: [],
    };

    const emptyArrayResponse = {
      data: [],
      meta: { cursor: null, total: null, request_id: "" },
      errors: [],
    };

    const mockFetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/card/42/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBanHistory),
        });
      }
      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(emptyArrayResponse),
        });
      }
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(emptyArrayResponse),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              data: null,
              meta: { cursor: null, total: null, request_id: "" },
              errors: [],
            }),
        });
      }
      if (urlStr.includes("/api/v1/collection/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(makeLinkedEntry()),
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

    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-toggle")).toBeDefined();
    });

    // Click to expand
    screen.getByTestId("ban-history-toggle").click();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-content")).toBeDefined();
    });

    // Verify ban event card is rendered
    expect(screen.getByTestId("ban-event-card")).toBeDefined();
  });

  it("shows empty message when card has no ban history", async () => {
    const emptyResponse = {
      data: [],
      meta: { cursor: null, total: null, request_id: "" },
      errors: [],
    };
    const nullResponse = {
      data: null,
      meta: { cursor: null, total: null, request_id: "" },
      errors: [],
    };

    const mockFetch = vi.fn().mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr.includes("/card/42/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(emptyResponse),
        });
      }
      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(emptyResponse),
        });
      }
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(emptyResponse),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(nullResponse),
        });
      }
      if (urlStr.includes("/api/v1/collection/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(makeLinkedEntry()),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(nullResponse),
      });
    });

    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-toggle")).toBeDefined();
    });

    screen.getByTestId("ban-history-toggle").click();

    await waitFor(() => {
      expect(screen.getByTestId("ban-history-empty-card")).toBeDefined();
    });
  });

  it("canonize partial success shows amber warning message", async () => {
    // First call returns unlinked entry, second (refetch) returns linked
    const unlinkedResponse = makeUnlinkedEntry();
    const linkedResponse = makeLinkedEntry();

    let callCount = 0;
    const mockFetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      const urlStr = String(url);

      // Canonize POST returns data + errors (partial success)
      if (urlStr.includes("/canonize") && options?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              data: linkedResponse.data,
              meta: { cursor: null, total: null, offset: null, request_id: "c1" },
              errors: [{ code: "myp_fetch_warning", message: "MYP timeout" }],
            }),
        });
      }

      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }

      // Collection detail: first call unlinked, subsequent linked
      if (urlStr.includes("/api/v1/collection/")) {
        callCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(callCount <= 1 ? unlinkedResponse : linkedResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
      });
    });

    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderDetail();

    // Wait for unlinked state
    await waitFor(() => {
      expect(screen.getByTestId("canonize-btn")).toBeDefined();
    });

    // Click canonize
    screen.getByTestId("canonize-btn").click();

    // Should show amber warning
    await waitFor(() => {
      const msg = screen.getByTestId("refresh-message");
      expect(msg).toBeDefined();
      expect(msg.className).toContain("text-amber-400");
    });
  });

  it("canonize failure triggers refetch and shows error", async () => {
    const unlinkedResponse = makeUnlinkedEntry();

    const mockFetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      const urlStr = String(url);

      // Canonize POST fails with 500
      if (urlStr.includes("/canonize") && options?.method === "POST") {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () =>
            Promise.resolve({
              data: null,
              meta: { cursor: null, total: null, offset: null, request_id: "err" },
              errors: [{ code: "internal", message: "Server error" }],
            }),
        });
      }

      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }

      if (urlStr.includes("/api/v1/collection/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(unlinkedResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
      });
    });

    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("canonize-btn")).toBeDefined();
    });

    screen.getByTestId("canonize-btn").click();

    // Should show red error
    await waitFor(() => {
      const msg = screen.getByTestId("refresh-message");
      expect(msg).toBeDefined();
      expect(msg.className).toContain("text-red-400");
    });
  });

  it("renders PriceSourceBadge when price_source is manual", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry({ price_source: "manual" })) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("price-source-badge")).toBeDefined();
    });

    expect(screen.getByTestId("price-source-badge").textContent).toContain("Manual Price");
  });

  it("renders amber MYP badge for source='myp'", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry({ price_source: "myp" })) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    const badge = screen.getByTestId("price-source-badge");
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain("MYP");
    expect(badge.className).toContain("text-amber-400");
  });

  it("does not render PriceSourceBadge when price_source is null", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry({ price_source: undefined })) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("card-info-panel")).toBeDefined();
    });

    expect(screen.queryByTestId("price-source-badge")).toBeNull();
  });

  it("renders ManualPriceInput section on card detail page", async () => {
    globalThis.fetch = createMockFetch(makeLinkedEntry()) as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-input")).toBeDefined();
    });

    expect(screen.getByTestId("manual-price-field")).toBeDefined();
    expect(screen.getByTestId("manual-price-save")).toBeDefined();
  });

  it("manual price input calls PATCH and refreshes on success", async () => {
    const linkedEntry = makeLinkedEntry();
    const updatedEntry = makeLinkedEntry({ latest_price: 25.5, price_source: "manual" });

    let callCount = 0;
    const mockFetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      const urlStr = String(url);

      // PATCH price endpoint
      if (urlStr.includes("/price") && options?.method === "PATCH") {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(updatedEntry),
        });
      }

      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }

      if (urlStr.includes("/api/v1/collection/")) {
        callCount++;
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(callCount <= 1 ? linkedEntry : updatedEntry),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
      });
    });

    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-field")).toBeDefined();
    });

    const { fireEvent } = await import("@testing-library/react");
    fireEvent.change(screen.getByTestId("manual-price-field"), { target: { value: "25.50" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-success")).toBeDefined();
    });

    // Verify PATCH was called
    const patchCall = mockFetch.mock.calls.find(
      ([u, o]: [string, RequestInit | undefined]) => String(u).includes("/price") && o?.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
  });

  it("manual price input shows error on API failure", async () => {
    const mockFetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      const urlStr = String(url);

      if (urlStr.includes("/price") && options?.method === "PATCH") {
        return Promise.resolve({
          ok: false,
          status: 500,
          json: () => Promise.resolve({
            data: null,
            meta: { cursor: null, total: null, offset: null, request_id: "e1" },
            errors: [{ code: "internal", message: "Server error" }],
          }),
        });
      }

      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }

      if (urlStr.includes("/api/v1/collection/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(makeLinkedEntry()),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
      });
    });

    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-field")).toBeDefined();
    });

    const { fireEvent } = await import("@testing-library/react");
    fireEvent.change(screen.getByTestId("manual-price-field"), { target: { value: "10" } });
    screen.getByTestId("manual-price-save").click();

    await waitFor(() => {
      expect(screen.getByTestId("manual-price-error")).toBeDefined();
    });
  });

  it("canonize full success shows green message", async () => {
    const unlinkedResponse = makeUnlinkedEntry();
    const linkedResponse = makeLinkedEntry();

    const mockFetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      const urlStr = String(url);

      // Canonize POST succeeds fully (no errors)
      if (urlStr.includes("/canonize") && options?.method === "POST") {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              data: linkedResponse.data,
              meta: { cursor: null, total: null, offset: null, request_id: "c1" },
              errors: [],
            }),
        });
      }

      if (urlStr.includes("/history")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/legality")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: [], meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }
      if (urlStr.includes("/metrics")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
        });
      }

      if (urlStr.includes("/api/v1/collection/")) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(unlinkedResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: null, meta: { cursor: null, total: null, request_id: "" }, errors: [] }),
      });
    });

    globalThis.fetch = mockFetch as unknown as typeof fetch;
    renderDetail();

    await waitFor(() => {
      expect(screen.getByTestId("canonize-btn")).toBeDefined();
    });

    screen.getByTestId("canonize-btn").click();

    await waitFor(() => {
      const msg = screen.getByTestId("refresh-message");
      expect(msg).toBeDefined();
      expect(msg.className).toContain("text-green-400");
    });
  });
});
