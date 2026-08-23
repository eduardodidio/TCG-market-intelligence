import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Settings } from "../../src/pages/Settings";
import { AuthContext } from "../../src/contexts/AuthContext";
import { CurrencyProvider } from "../../src/contexts/CurrencyContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";

const mockUser = {
  id: 1,
  email: "user@test.com",
  display_name: "Test User",
  avatar_url: null,
  auth_provider: "local",
  preferred_language: "en",
  is_active: true,
};

const mockAuth = {
  user: mockUser,
  loading: false,
  error: null,
  isAuthenticated: true,
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
};

function renderSettings() {
  return render(
    <LanguageProvider>
      <AuthContext.Provider value={mockAuth}>
        <CurrencyProvider>
          <MemoryRouter>
            <Settings />
          </MemoryRouter>
        </CurrencyProvider>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("Settings page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: null, meta: {}, errors: [] }),
    }) as unknown as typeof fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("renders settings page sections", () => {
    renderSettings();

    expect(screen.getByTestId("page-settings")).toBeDefined();
    expect(screen.getByTestId("settings-account")).toBeDefined();
    expect(screen.getByTestId("settings-preferences")).toBeDefined();
    expect(screen.getByTestId("settings-api-keys")).toBeDefined();
    expect(screen.getByTestId("settings-export")).toBeDefined();
  });

  it("shows user email and display name", () => {
    renderSettings();

    expect(screen.getByText("user@test.com")).toBeDefined();
    expect(screen.getByText("Test User")).toBeDefined();
  });
});
