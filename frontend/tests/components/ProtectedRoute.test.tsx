import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "../../src/components/ProtectedRoute";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";

function renderWithAuth(
  auth: Partial<AuthContextValue>,
  initialPath = "/protected",
) {
  const mockAuth: AuthContextValue = {
    user: null,
    loading: false,
    error: null,
    isAuthenticated: false,
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
            path="/protected"
            element={
              <ProtectedRoute>
                <div data-testid="protected-content">Secret content</div>
              </ProtectedRoute>
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

describe("ProtectedRoute", () => {
  it("renders children when authenticated", () => {
    renderWithAuth({
      isAuthenticated: true,
      user: {
        id: 1,
        email: "x@y.com",
        display_name: null,
        avatar_url: null,
        auth_provider: "email",
        preferred_language: null,
        is_active: true,
        is_admin: false,
      },
    });

    expect(screen.getByTestId("protected-content")).toBeDefined();
    expect(screen.getByText("Secret content")).toBeDefined();
  });

  it("redirects to /login when unauthenticated", () => {
    renderWithAuth({ isAuthenticated: false });

    expect(screen.getByTestId("login-page")).toBeDefined();
    expect(screen.queryByTestId("protected-content")).toBeNull();
  });

  it("shows loading spinner when auth is loading", () => {
    renderWithAuth({ loading: true });

    expect(screen.getByText("Checking authentication...")).toBeDefined();
    expect(screen.queryByTestId("protected-content")).toBeNull();
  });
});
