import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthContext } from "../../src/contexts/AuthContext";
import { CurrencyProvider } from "../../src/contexts/CurrencyContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";
import { MarketPage } from "../../src/pages/MarketPage";
import { Trending } from "../../src/pages/Trending";

// Mock recharts
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

const mockAuth = {
  user: { id: 1, email: "u@t.com", display_name: "T", avatar_url: null, auth_provider: "local", preferred_language: "en", is_active: true, is_admin: false },
  loading: false,
  error: null,
  isAuthenticated: true,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
};

function emptyEnvelope() {
  return { data: [], meta: { cursor: null, total: 0, offset: null, request_id: "t" }, errors: [] };
}

function createMockFetch() {
  return vi.fn().mockImplementation((url: string) => {
    const u = String(url);
    if (u.includes("/market/summary")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          data: {
            total_cards_tracked: 10, total_observations: 100, avg_price: 5,
            avg_price_change_pct: 1, gainers_count: 5, losers_count: 3,
            unchanged_count: 2, market_direction: "up", period: "30d",
            currency: "BRL", computed_at: "2026-01-01T00:00:00",
          },
          meta: { request_id: "t" }, errors: [],
        }),
      });
    }
    if (u.includes("/market/trending")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          data: { cards: [], period: "30d", direction: "gainers", computed_at: "2026-01-01", cached: false },
          meta: { request_id: "t" }, errors: [],
        }),
      });
    }
    if (u.includes("/collection")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
    }
    return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
  });
}

function wrap(component: React.ReactNode) {
  return render(
    <LanguageProvider>
      <AuthContext.Provider value={mockAuth as never}>
        <CurrencyProvider>
          <MemoryRouter>
            {component}
          </MemoryRouter>
        </CurrencyProvider>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("F97-T02: Market-Trending cross-links", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("MarketPage has 'View All Trending' link to /market/trending", () => {
    wrap(<MarketPage />);
    const link = screen.getByTestId("view-all-trending-link");
    expect(link).toBeDefined();
    expect(link.getAttribute("href")).toBe("/market/trending");
  });

  it("Trending has 'Back to Market' link to /market", () => {
    wrap(<Trending />);
    const link = screen.getByTestId("back-to-market-link");
    expect(link).toBeDefined();
    expect(link.getAttribute("href")).toBe("/market");
  });
});
