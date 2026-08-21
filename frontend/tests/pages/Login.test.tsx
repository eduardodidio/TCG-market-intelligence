import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Login } from "../../src/pages/Login";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";

function renderLogin(authOverrides: Partial<AuthContextValue> = {}) {
  const mockAuth: AuthContextValue = {
    user: null,
    loading: false,
    error: null,
    isAuthenticated: false,
    login: vi.fn().mockResolvedValue(null),
    register: vi.fn().mockResolvedValue(null),
    logout: vi.fn().mockResolvedValue(undefined),
    ...authOverrides,
  };

  return render(
    <LanguageProvider>
      <AuthContext.Provider value={mockAuth}>
        <MemoryRouter initialEntries={["/login"]}>
          <Login />
        </MemoryRouter>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("Login page", () => {
  it("renders sign-in form by default", () => {
    renderLogin();
    expect(screen.getByTestId("auth-form")).toBeDefined();
    expect(screen.getByTestId("email-input")).toBeDefined();
    expect(screen.getByTestId("password-input")).toBeDefined();
    expect(screen.getByTestId("submit-button").textContent).toBe("Sign In");
  });

  it("toggles between sign-in and register modes", () => {
    renderLogin();

    // Click toggle to switch to register
    fireEvent.click(screen.getByTestId("toggle-mode"));
    expect(screen.getByTestId("submit-button").textContent).toBe(
      "Create Account",
    );
    expect(screen.getByTestId("display-name-input")).toBeDefined();

    // Click toggle to switch back to sign-in
    fireEvent.click(screen.getByTestId("toggle-mode"));
    expect(screen.getByTestId("submit-button").textContent).toBe("Sign In");
  });

  it("renders OAuth buttons (disabled)", () => {
    renderLogin();
    expect(screen.getByTestId("oauth-google")).toBeDefined();
    expect(screen.getByTestId("oauth-microsoft")).toBeDefined();
    expect(screen.getByTestId("oauth-apple")).toBeDefined();

    // All should be disabled
    expect(
      (screen.getByTestId("oauth-google") as HTMLButtonElement).disabled,
    ).toBe(true);
  });

  it("shows error message when auth error exists", () => {
    renderLogin({ error: "Invalid credentials" });
    expect(screen.getByTestId("auth-error").textContent).toBe(
      "Invalid credentials",
    );
  });

  it("renders page title", () => {
    renderLogin();
    expect(screen.getByText("TCG Market")).toBeDefined();
  });

  it("contains a language selector", () => {
    renderLogin();
    expect(screen.getByTestId("login-language-selector")).toBeDefined();
    expect(screen.getByTestId("language-selector")).toBeDefined();
  });
});
