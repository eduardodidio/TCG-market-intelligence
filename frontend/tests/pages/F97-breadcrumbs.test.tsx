import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext } from "../../src/contexts/AuthContext";
import { CurrencyProvider } from "../../src/contexts/CurrencyContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";

// Import all pages that received breadcrumbs in T01
import { MarketPage } from "../../src/pages/MarketPage";
import { Trending } from "../../src/pages/Trending";
import { BanList } from "../../src/pages/BanList";
import { BanHistory } from "../../src/pages/BanHistory";
import { Settings } from "../../src/pages/Settings";
import { AdminPanel } from "../../src/pages/AdminPanel";
import { Evaluations } from "../../src/pages/Evaluations";
import { TopDecksPage } from "../../src/pages/TopDecksPage";
import { Marketplace } from "../../src/pages/Marketplace";
import { ChangePassword } from "../../src/pages/ChangePassword";
import { DeckList } from "../../src/pages/DeckList";

// Mock recharts to avoid jsdom SVG issues
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
  user: { id: 1, email: "u@t.com", display_name: "T", avatar_url: null, auth_provider: "local", preferred_language: "en", is_active: true, is_admin: true },
  loading: false,
  error: null,
  isAuthenticated: true,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
  changePassword: vi.fn(),
};

function emptyEnvelope() {
  return { data: [], meta: { cursor: null, total: 0, offset: null, request_id: "t" }, errors: [] };
}

function createMockFetch() {
  return vi.fn().mockImplementation((url: string) => {
    const u = String(url);
    // Market summary
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
    // Trending
    if (u.includes("/market/trending")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          data: { cards: [], period: "30d", direction: "gainers", computed_at: "2026-01-01", cached: false },
          meta: { request_id: "t" }, errors: [],
        }),
      });
    }
    // Volatile
    if (u.includes("/market/volatile")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
    }
    // Deck ranking
    if (u.includes("/decks/ranking")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          data: { decks: [], total: 0, period: "30d", currency: "BRL" },
          meta: { request_id: "t" }, errors: [],
        }),
      });
    }
    // Banlist formats
    if (u.includes("/banlist/formats")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: ["standard"], meta: { request_id: "t" }, errors: [] }) });
    }
    // Banlist entries
    if (u.includes("/banlist/history")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({
          data: { items: [], total: 0 },
          meta: { request_id: "t" }, errors: [],
        }),
      });
    }
    if (u.includes("/banlist")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
    }
    // Admin
    if (u.includes("/admin/users")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
    }
    if (u.includes("/admin/dashboard")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: null, meta: {}, errors: [] }) });
    }
    // Evaluations
    if (u.includes("/evaluations")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
    }
    // Marketplace
    if (u.includes("/marketplace")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ listings: [] }) });
    }
    // Decks
    if (u.includes("/decks")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
    }
    // Credits balance
    if (u.includes("/credits/balance")) {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({ data: { balance: 100, is_admin: true }, meta: {}, errors: [] }) });
    }
    // Default
    return Promise.resolve({ ok: true, json: () => Promise.resolve(emptyEnvelope()) });
  });
}

function wrap(component: React.ReactNode, path = "/") {
  return render(
    <LanguageProvider>
      <AuthContext.Provider value={mockAuth as never}>
        <CurrencyProvider>
          <MemoryRouter initialEntries={[path]}>
            {component}
          </MemoryRouter>
        </CurrencyProvider>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("F97-T01: Breadcrumbs on secondary pages", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    globalThis.fetch = createMockFetch() as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("MarketPage has breadcrumb with Dashboard parent", async () => {
    wrap(<MarketPage />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    expect(bc.textContent).toContain("Dashboard");
    const link = bc.querySelector("a");
    expect(link?.getAttribute("href")).toBe("/");
  });

  it("Trending has breadcrumb with Dashboard parent", async () => {
    wrap(<Trending />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    expect(bc.textContent).toContain("Dashboard");
  });

  it("BanList has breadcrumb with Dashboard parent", async () => {
    wrap(<BanList />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    expect(bc.textContent).toContain("Dashboard");
  });

  it("BanHistory has breadcrumb with Ban List parent", async () => {
    wrap(<BanHistory />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    const link = bc.querySelector("a");
    expect(link?.getAttribute("href")).toBe("/banlist");
  });

  it("Settings has breadcrumb with Dashboard parent", () => {
    wrap(<Settings />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    expect(bc.textContent).toContain("Dashboard");
  });

  it("AdminPanel has breadcrumb with Dashboard parent", async () => {
    wrap(<AdminPanel />);
    await waitFor(() => {
      const bc = screen.getByTestId("breadcrumb");
      expect(bc).toBeDefined();
      expect(bc.textContent).toContain("Dashboard");
    });
  });

  it("Evaluations has breadcrumb with Dashboard parent", async () => {
    wrap(<Evaluations />);
    await waitFor(() => {
      const bc = screen.getByTestId("breadcrumb");
      expect(bc).toBeDefined();
      expect(bc.textContent).toContain("Dashboard");
    });
  });

  it("TopDecksPage has breadcrumb with My Decks parent", async () => {
    wrap(<TopDecksPage />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    const link = bc.querySelector("a");
    expect(link?.getAttribute("href")).toBe("/decks");
  });

  it("Marketplace has breadcrumb with Dashboard parent", async () => {
    wrap(<Marketplace />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    expect(bc.textContent).toContain("Dashboard");
  });

  it("ChangePassword has breadcrumb with Settings parent", () => {
    wrap(
      <Routes>
        <Route path="*" element={<ChangePassword />} />
      </Routes>,
    );
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    const link = bc.querySelector("a");
    expect(link?.getAttribute("href")).toBe("/settings");
  });

  it("DeckList has breadcrumb with Dashboard parent", async () => {
    wrap(<DeckList />);
    const bc = screen.getByTestId("breadcrumb");
    expect(bc).toBeDefined();
    expect(bc.textContent).toContain("Dashboard");
  });
});
