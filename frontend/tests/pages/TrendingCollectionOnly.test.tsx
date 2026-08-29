import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Trending } from "../../src/pages/Trending";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";
import type { ApiResponse, TrendingResponse } from "../../src/types/api";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

function mockTrendingResponse(direction: "up" | "down" = "up"): TrendingResponse {
  return {
    cards: [
      {
        card_id: 1,
        name_en: "Lightning Bolt",
        name_pt: null,
        set_code: "lea",
        collector_number: "161",
        image_url: null,
        price_start: 10,
        price_end: 15,
        change_pct: 50,
        change_abs: 5,
        consistency: 0.9,
        composite_score: 75,
        observation_count: 5,
        currency: "BRL",
      },
    ],
    period: "30d",
    direction,
    computed_at: "2026-08-22T12:00:00",
    cached: false,
  };
}

function mockAuth(overrides: Partial<AuthContextValue> = {}): AuthContextValue {
  return {
    user: null,
    loading: false,
    error: null,
    isAuthenticated: false,
    mustChangePassword: false,
    login: vi.fn().mockResolvedValue(null),
    register: vi.fn().mockResolvedValue(null),
    logout: vi.fn().mockResolvedValue(undefined),
    changePassword: vi.fn().mockResolvedValue(null),
    ...overrides,
  };
}

function renderPage(auth: Partial<AuthContextValue> = {}) {
  return render(
    <AuthContext.Provider value={mockAuth(auth)}>
      <MemoryRouter initialEntries={["/market/trending"]}>
        <Trending />
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

describe("Trending page collection-only toggle", () => {
  let originalFetch: typeof global.fetch;
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    originalFetch = global.fetch;
    fetchSpy = vi.fn().mockImplementation((url: string) => {
      const direction = url.includes("losers") ? "down" : "up";
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            envelope(mockTrendingResponse(direction as "up" | "down")),
          ),
      });
    });
    global.fetch = fetchSpy as unknown as typeof fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("shows collection-only toggle when authenticated", async () => {
    renderPage({
      isAuthenticated: true,
      user: { id: 1, email: "test@test.com", display_name: null, avatar_url: null, preferred_currency: "BRL", preferred_language: "en", is_admin: false, is_active: true },
    });
    await waitFor(() => {
      expect(screen.getByTestId("collection-only-toggle")).toBeTruthy();
    });
  });

  it("hides collection-only toggle when not authenticated", () => {
    renderPage({ isAuthenticated: false });
    expect(screen.queryByTestId("collection-only-toggle")).toBeNull();
  });

  it("toggle is checked by default when authenticated", async () => {
    renderPage({
      isAuthenticated: true,
      user: { id: 1, email: "test@test.com", display_name: null, avatar_url: null, preferred_currency: "BRL", preferred_language: "en", is_admin: false, is_active: true },
    });
    await waitFor(() => {
      const checkbox = screen.getByTestId("collection-only-toggle").querySelector("input[type='checkbox']") as HTMLInputElement;
      expect(checkbox.checked).toBe(true);
    });
  });

  it("sends collection_only=true when authenticated and toggle is on", async () => {
    renderPage({
      isAuthenticated: true,
      user: { id: 1, email: "test@test.com", display_name: null, avatar_url: null, preferred_currency: "BRL", preferred_language: "en", is_admin: false, is_active: true },
    });
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalled();
    });
    // Check that fetch was called with collection_only=true in the URL
    const calls = fetchSpy.mock.calls.map((c: [string]) => c[0]);
    const hasCollectionOnly = calls.some((url: string) => url.includes("collection_only=true"));
    expect(hasCollectionOnly).toBe(true);
  });

  it("does not send collection_only when not authenticated", async () => {
    renderPage({ isAuthenticated: false });
    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalled();
    });
    const calls = fetchSpy.mock.calls.map((c: [string]) => c[0]);
    const hasCollectionOnly = calls.some((url: string) => url.includes("collection_only"));
    expect(hasCollectionOnly).toBe(false);
  });

  it("unchecking toggle removes collection_only param", async () => {
    renderPage({
      isAuthenticated: true,
      user: { id: 1, email: "test@test.com", display_name: null, avatar_url: null, preferred_currency: "BRL", preferred_language: "en", is_admin: false, is_active: true },
    });

    await waitFor(() => {
      expect(screen.getByTestId("collection-only-toggle")).toBeTruthy();
    });

    // Clear call history
    fetchSpy.mockClear();

    const checkbox = screen.getByTestId("collection-only-toggle").querySelector("input[type='checkbox']") as HTMLInputElement;
    fireEvent.click(checkbox);

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalled();
    });

    const calls = fetchSpy.mock.calls.map((c: [string]) => c[0]);
    const hasCollectionOnly = calls.some((url: string) => url.includes("collection_only"));
    expect(hasCollectionOnly).toBe(false);
  });
});
