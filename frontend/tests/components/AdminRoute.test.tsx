import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { AdminRoute } from "../../src/components/AdminRoute";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";

function renderWithAuth(
  auth: Partial<AuthContextValue>,
  initialPath = "/admin",
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
            path="/admin"
            element={
              <AdminRoute>
                <div data-testid="admin-content">Admin content</div>
              </AdminRoute>
            }
          />
          <Route
            path="/login"
            element={<div data-testid="login-page">Login Page</div>}
          />
          <Route
            path="/"
            element={<div data-testid="home-page">Home Page</div>}
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
};

const regularUser = {
  id: 2,
  email: "user@example.com",
  display_name: "Regular User",
  avatar_url: null,
  auth_provider: "email",
  preferred_language: null,
  is_active: true,
  is_admin: false,
};

describe("AdminRoute", () => {
  it("renders children when user is admin", () => {
    renderWithAuth({
      isAuthenticated: true,
      user: adminUser,
    });

    expect(screen.getByTestId("admin-content")).toBeDefined();
    expect(screen.getByText("Admin content")).toBeDefined();
  });

  it("redirects to / when user is not admin", () => {
    renderWithAuth({
      isAuthenticated: true,
      user: regularUser,
    });

    expect(screen.getByTestId("home-page")).toBeDefined();
    expect(screen.queryByTestId("admin-content")).toBeNull();
  });

  it("redirects to /login when not authenticated", () => {
    renderWithAuth({ isAuthenticated: false });

    expect(screen.getByTestId("login-page")).toBeDefined();
    expect(screen.queryByTestId("admin-content")).toBeNull();
  });

  it("shows loading spinner while auth is loading", () => {
    renderWithAuth({ loading: true });

    expect(screen.getByText("Checking access...")).toBeDefined();
    expect(screen.queryByTestId("admin-content")).toBeNull();
  });
});
