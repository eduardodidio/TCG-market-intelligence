import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { AuthContext } from "../../src/contexts/AuthContext";
import { useOwnedCardIds } from "../../src/hooks/useOwnedCardIds";

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

function wrapper(auth: typeof mockAuthAuthenticated) {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <AuthContext.Provider value={auth as never}>
        {children}
      </AuthContext.Provider>
    );
  };
}

describe("useOwnedCardIds", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("returns empty Set when unauthenticated", () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], meta: {}, errors: [] }),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useOwnedCardIds(), {
      wrapper: wrapper(mockAuthUnauthenticated),
    });
    expect(result.current.size).toBe(0);
  });

  it("returns Set of card_ids from collection when authenticated", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        data: [
          { card_id: 10, id: 1, name_en: "A" },
          { card_id: 20, id: 2, name_en: "B" },
          { card_id: null, id: 3, name_en: "C" },
        ],
        meta: { cursor: null, total: 3, offset: null, request_id: "t" },
        errors: [],
      }),
    }) as unknown as typeof fetch;

    const { result } = renderHook(() => useOwnedCardIds(), {
      wrapper: wrapper(mockAuthAuthenticated),
    });

    await waitFor(() => {
      expect(result.current.size).toBe(2);
    });
    expect(result.current.has(10)).toBe(true);
    expect(result.current.has(20)).toBe(true);
    // card_id: null should not be included
    expect(result.current.has(0)).toBe(false);
  });
});
