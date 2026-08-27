import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { LanguageSelector } from "../../src/components/LanguageSelector";
import { LanguageProvider } from "../../src/contexts/LanguageContext";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";

// Mock fetch for apiPatch calls
beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
    ok: true,
    json: () => Promise.resolve({ data: {}, meta: {}, errors: [] }),
  }));
  vi.stubGlobal("localStorage", {
    getItem: vi.fn().mockReturnValue(null),
    setItem: vi.fn(),
    removeItem: vi.fn(),
  });
});

const mockAuthUnauthenticated: AuthContextValue = {
  user: null,
  loading: false,
  error: null,
  isAuthenticated: false,
  login: vi.fn().mockResolvedValue(null),
  register: vi.fn().mockResolvedValue(null),
  logout: vi.fn().mockResolvedValue(undefined),
  mustChangePassword: false,
  changePassword: vi.fn().mockResolvedValue(null),
};

const mockAuthAuthenticated: AuthContextValue = {
  user: {
    id: 1,
    email: "test@example.com",
    display_name: "Test User",
    avatar_url: null,
    auth_provider: "email",
    preferred_language: "en",
    is_active: true,
    is_admin: false,
  },
  loading: false,
  error: null,
  isAuthenticated: true,
  login: vi.fn().mockResolvedValue(null),
  register: vi.fn().mockResolvedValue(null),
  logout: vi.fn().mockResolvedValue(undefined),
  mustChangePassword: false,
  changePassword: vi.fn().mockResolvedValue(null),
};

function renderSelector(
  variant: "compact" | "full" = "compact",
  auth: AuthContextValue = mockAuthUnauthenticated,
) {
  return render(
    <AuthContext.Provider value={auth}>
      <LanguageProvider>
        <LanguageSelector variant={variant} />
      </LanguageProvider>
    </AuthContext.Provider>,
  );
}

describe("LanguageSelector", () => {
  it("renders EN and PT-BR buttons", () => {
    renderSelector();
    expect(screen.getByTestId("language-btn-en")).toBeDefined();
    expect(screen.getByTestId("language-btn-pt-BR")).toBeDefined();
  });

  it("EN is selected by default", () => {
    renderSelector();
    expect(
      screen.getByTestId("language-btn-en").getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      screen.getByTestId("language-btn-pt-BR").getAttribute("aria-pressed"),
    ).toBe("false");
  });

  it("clicking PT-BR selects it", () => {
    renderSelector();
    fireEvent.click(screen.getByTestId("language-btn-pt-BR"));
    expect(
      screen.getByTestId("language-btn-pt-BR").getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      screen.getByTestId("language-btn-en").getAttribute("aria-pressed"),
    ).toBe("false");
  });

  it("clicking EN selects it after switching", () => {
    renderSelector();
    fireEvent.click(screen.getByTestId("language-btn-pt-BR"));
    fireEvent.click(screen.getByTestId("language-btn-en"));
    expect(
      screen.getByTestId("language-btn-en").getAttribute("aria-pressed"),
    ).toBe("true");
  });

  it("renders with compact variant by default", () => {
    renderSelector("compact");
    const selector = screen.getByTestId("language-selector");
    expect(selector).toBeDefined();
  });

  it("renders with full variant", () => {
    renderSelector("full");
    const selector = screen.getByTestId("language-selector");
    expect(selector).toBeDefined();
  });

  it("has proper aria-label", () => {
    renderSelector();
    const selector = screen.getByTestId("language-selector");
    expect(selector.getAttribute("role")).toBe("group");
  });

  it("calls apiPatch when authenticated and language changes", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: {}, meta: {}, errors: [] }),
    });
    vi.stubGlobal("fetch", fetchMock);

    renderSelector("compact", mockAuthAuthenticated);
    fireEvent.click(screen.getByTestId("language-btn-pt-BR"));

    // Wait for the async PATCH call
    await vi.waitFor(() => {
      const patchCall = fetchMock.mock.calls.find(
        (call: unknown[]) =>
          typeof call[0] === "string" &&
          call[0].includes("preferences") &&
          (call[1] as RequestInit)?.method === "PATCH",
      );
      expect(patchCall).toBeDefined();
    });
  });

  it("does not call apiPatch when unauthenticated", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);

    renderSelector("compact", mockAuthUnauthenticated);
    fireEvent.click(screen.getByTestId("language-btn-pt-BR"));

    // No PATCH call should be made
    const patchCalls = fetchMock.mock.calls.filter(
      (call: unknown[]) =>
        (call[1] as RequestInit)?.method === "PATCH",
    );
    expect(patchCalls).toHaveLength(0);
  });
});
