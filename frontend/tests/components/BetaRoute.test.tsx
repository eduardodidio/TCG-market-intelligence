import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { BetaRoute } from "../../src/components/BetaRoute";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";

function renderWithAuth(
  auth: Partial<AuthContextValue>,
  initialPath = "/beta",
  requiresAuth = true,
) {
  const mockAuth: AuthContextValue = {
    user: null,
    loading: false,
    error: null,
    isAuthenticated: false,
    hasBetaAccess: true,
    login: vi.fn().mockResolvedValue(null),
    register: vi.fn().mockResolvedValue(null),
    logout: vi.fn().mockResolvedValue(undefined),
    mustChangePassword: false,
    changePassword: vi.fn().mockResolvedValue(null),
    ...auth,
  };

  return render(
    <AuthContext.Provider value={mockAuth}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route
            path="/beta"
            element={
              <BetaRoute requiresAuth={requiresAuth}>
                <div data-testid="beta-content">Beta content</div>
              </BetaRoute>
            }
          />
          <Route
            path="/login"
            element={<div data-testid="login-page">Login Page</div>}
          />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  );
}

const adminUser = {
  id: 1,
  email: "admin@example.com",
  display_name: "Admin",
  avatar_url: null,
  auth_provider: "email",
  preferred_language: null,
  is_active: true,
  is_admin: true,
  role: "admin",
};

const guestUser = {
  id: 99,
  email: "guest@example.com",
  display_name: "Guest",
  avatar_url: null,
  auth_provider: "email",
  preferred_language: null,
  is_active: true,
  is_admin: false,
  role: "guest",
};

describe("BetaRoute", () => {
  it("renders children for admin user", () => {
    renderWithAuth({
      isAuthenticated: true,
      hasBetaAccess: true,
      user: adminUser,
    });

    expect(screen.getByTestId("beta-content")).toBeDefined();
    expect(screen.getByText("Beta content")).toBeDefined();
  });

  it("shows blocked message for guest user", () => {
    renderWithAuth({
      isAuthenticated: true,
      hasBetaAccess: false,
      user: guestUser,
    });

    expect(screen.getByTestId("beta-blocked-message")).toBeDefined();
    expect(
      screen.getByText("This feature is not available for the current profile"),
    ).toBeDefined();
    expect(screen.queryByTestId("beta-content")).toBeNull();
  });

  it("redirects to login for unauthenticated user on auth-required route", () => {
    renderWithAuth({
      isAuthenticated: false,
      hasBetaAccess: true,
    });

    expect(screen.getByTestId("login-page")).toBeDefined();
    expect(screen.queryByTestId("beta-content")).toBeNull();
  });

  it("allows anonymous access on public beta route (requiresAuth=false)", () => {
    renderWithAuth(
      {
        isAuthenticated: false,
        hasBetaAccess: true,
      },
      "/beta",
      false,
    );

    expect(screen.getByTestId("beta-content")).toBeDefined();
    expect(screen.getByText("Beta content")).toBeDefined();
  });

  it("blocks guest user even on public beta route", () => {
    renderWithAuth(
      {
        isAuthenticated: true,
        hasBetaAccess: false,
        user: guestUser,
      },
      "/beta",
      false,
    );

    expect(screen.getByTestId("beta-blocked-message")).toBeDefined();
    expect(screen.queryByTestId("beta-content")).toBeNull();
  });

  it("shows loading spinner while auth is loading", () => {
    renderWithAuth({ loading: true });

    expect(screen.getByText("Checking access...")).toBeDefined();
    expect(screen.queryByTestId("beta-content")).toBeNull();
  });

  it("renders children for regular (non-guest) authenticated user", () => {
    renderWithAuth({
      isAuthenticated: true,
      hasBetaAccess: true,
      user: {
        ...adminUser,
        is_admin: false,
        role: "admin",
      },
    });

    expect(screen.getByTestId("beta-content")).toBeDefined();
  });
});
