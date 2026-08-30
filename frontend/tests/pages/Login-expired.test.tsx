import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Login } from "../../src/pages/Login";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";
import { forceLogout, _resetForTest } from "../../src/api/authRefresh";

function renderLogin(
  authOverrides: Partial<AuthContextValue> = {},
  initialEntry = "/login",
) {
  const mockAuth: AuthContextValue = {
    user: null,
    loading: false,
    error: null,
    isAuthenticated: false,
    mustChangePassword: false,
    login: vi.fn().mockResolvedValue(null),
    register: vi.fn().mockResolvedValue(null),
    logout: vi.fn().mockResolvedValue(undefined),
    changePassword: vi.fn().mockResolvedValue(null),
    ...authOverrides,
  };

  return render(
    <LanguageProvider>
      <AuthContext.Provider value={mockAuth}>
        <MemoryRouter initialEntries={[initialEntry]}>
          <Login />
        </MemoryRouter>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("Login — session expired banner", () => {
  it("shows expired banner when expired=1 is present", () => {
    renderLogin({}, "/login?expired=1");
    const banner = screen.getByTestId("session-expired-banner");
    expect(banner).toBeDefined();
    expect(banner.textContent).toBe(
      "Your session has expired. Please log in again.",
    );
  });

  it("does NOT show expired banner on normal login", () => {
    renderLogin({}, "/login");
    expect(screen.queryByTestId("session-expired-banner")).toBeNull();
  });

  it("does NOT show expired banner when expired param is absent but returnTo is present", () => {
    renderLogin({}, "/login?returnTo=%2Fcollection");
    expect(screen.queryByTestId("session-expired-banner")).toBeNull();
  });

  it("shows expired banner alongside returnTo param", () => {
    renderLogin({}, "/login?returnTo=%2Fdecks&expired=1");
    expect(screen.getByTestId("session-expired-banner")).toBeDefined();
  });
});

describe("forceLogout — redirect with returnTo and expired", () => {
  let originalPathname: string;
  let originalHref: string;

  beforeEach(() => {
    _resetForTest();
    originalPathname = window.location.pathname;
    originalHref = window.location.href;
    localStorage.setItem("tcg_access_token", "tok");
    localStorage.setItem("tcg_refresh_token", "ref");
  });

  afterEach(() => {
    localStorage.clear();
    // Restore location — jsdom doesn't reset between tests automatically
    // but we use Object.defineProperty so we need to be careful
  });

  it("builds redirect URL with returnTo and expired=1", () => {
    // Mock pathname to simulate being on /collection
    Object.defineProperty(window, "location", {
      value: { pathname: "/collection", href: "" },
      writable: true,
      configurable: true,
    });

    forceLogout();

    expect(window.location.href).toBe(
      "/login?returnTo=%2Fcollection&expired=1",
    );
    expect(localStorage.getItem("tcg_access_token")).toBeNull();
    expect(localStorage.getItem("tcg_refresh_token")).toBeNull();

    // Restore
    Object.defineProperty(window, "location", {
      value: { pathname: originalPathname, href: originalHref },
      writable: true,
      configurable: true,
    });
  });

  it("does NOT redirect when already on /login", () => {
    Object.defineProperty(window, "location", {
      value: { pathname: "/login", href: "/login" },
      writable: true,
      configurable: true,
    });

    forceLogout();

    // href should remain unchanged (still /login, not redirected)
    expect(window.location.href).toBe("/login");

    // Restore
    Object.defineProperty(window, "location", {
      value: { pathname: originalPathname, href: originalHref },
      writable: true,
      configurable: true,
    });
  });

  it("encodes complex pathnames correctly", () => {
    Object.defineProperty(window, "location", {
      value: { pathname: "/collection/42", href: "" },
      writable: true,
      configurable: true,
    });

    forceLogout();

    expect(window.location.href).toBe(
      "/login?returnTo=%2Fcollection%2F42&expired=1",
    );

    // Restore
    Object.defineProperty(window, "location", {
      value: { pathname: originalPathname, href: originalHref },
      writable: true,
      configurable: true,
    });
  });
});
