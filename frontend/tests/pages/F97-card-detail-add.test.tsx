import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AuthContext } from "../../src/contexts/AuthContext";
import { CurrencyProvider } from "../../src/contexts/CurrencyContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";
import { CardDetail } from "../../src/pages/CardDetail";

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

const mockAuthAuthenticated = {
  user: { id: 1, email: "u@t.com", display_name: "T", avatar_url: null, auth_provider: "local", preferred_language: "en", is_active: true, is_admin: false },
  loading: false,
  error: null,
  isAuthenticated: true,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
};

const mockAuthUnauthenticated = {
  ...mockAuthAuthenticated,
  user: null,
  isAuthenticated: false,
};

function makeCardResponse(overrides?: Record<string, unknown>) {
  return {
    data: {
      id: 42,
      game: "magic",
      name_en: "Lightning Bolt",
      name_pt: "Raio",
      set_code: "lea",
      collector_number: "161",
      latest_price: 15.0,
      currency: "BRL",
      source_cards: [],
      collection_entry_id: null,
      created_at: "2026-01-01T00:00:00",
      updated_at: "2026-08-01T00:00:00",
      ...overrides,
    },
    meta: { request_id: "t" },
    errors: [],
  };
}

function createMockFetch(cardOverrides?: Record<string, unknown>) {
  return vi.fn().mockImplementation((url: string) => {
    const u = String(url);
    if (u.includes("/cards/")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve(makeCardResponse(cardOverrides)),
      });
    }
    if (u.includes("/collection")) {
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ data: [], meta: { cursor: null, total: 0, offset: null, request_id: "t" }, errors: [] }),
      });
    }
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ data: null, meta: { request_id: "t" }, errors: [] }),
    });
  });
}

function wrap(component: React.ReactNode, auth: typeof mockAuthAuthenticated) {
  return render(
    <LanguageProvider>
      <AuthContext.Provider value={auth as never}>
        <CurrencyProvider>
          <MemoryRouter initialEntries={["/cards/42"]}>
            <Routes>
              <Route path="/cards/:id" element={component} />
            </Routes>
          </MemoryRouter>
        </CurrencyProvider>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("F97-T04: Add to Collection CTA on CardDetail", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("shows add-to-collection button when card is not owned and user is authenticated", async () => {
    globalThis.fetch = createMockFetch({ collection_entry_id: null }) as unknown as typeof fetch;
    wrap(<CardDetail />, mockAuthAuthenticated);
    const btn = await screen.findByTestId("add-to-collection-btn");
    expect(btn).toBeDefined();
  });

  it("does not show add button when card is already in collection", async () => {
    globalThis.fetch = createMockFetch({ collection_entry_id: 99 }) as unknown as typeof fetch;
    wrap(<CardDetail />, mockAuthAuthenticated);
    // Wait for card data to load by checking for the set code badge
    await screen.findByText("lea");
    expect(screen.queryByTestId("add-to-collection-btn")).toBeNull();
    expect(screen.queryByTestId("add-to-collection-section")).toBeNull();
  });

  it("shows sign-in link when unauthenticated", async () => {
    globalThis.fetch = createMockFetch({ collection_entry_id: null }) as unknown as typeof fetch;
    wrap(<CardDetail />, mockAuthUnauthenticated);
    const link = await screen.findByTestId("sign-in-to-add-link");
    expect(link).toBeDefined();
    expect(link.getAttribute("href")).toBe("/login");
  });

  it("opens BatchAddModal when add button is clicked", async () => {
    globalThis.fetch = createMockFetch({ collection_entry_id: null }) as unknown as typeof fetch;
    wrap(<CardDetail />, mockAuthAuthenticated);
    const btn = await screen.findByTestId("add-to-collection-btn");
    fireEvent.click(btn);
    const modal = await screen.findByTestId("batch-add-modal");
    expect(modal).toBeDefined();
    // Verify textarea is pre-filled
    const textarea = screen.getByTestId("batch-textarea") as HTMLTextAreaElement;
    expect(textarea.value).toContain("Lightning Bolt");
    expect(textarea.value).toContain("[lea]");
  });
});
