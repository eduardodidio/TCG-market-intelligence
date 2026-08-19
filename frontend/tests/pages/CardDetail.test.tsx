import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CardDetail } from "../../src/pages/CardDetail";
import {
  mockCardDetail,
  mockPriceHistory,
  mockApiError,
} from "../fixtures/api-responses";

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
