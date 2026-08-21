import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Layout } from "../../src/components/Layout";
import { AuthContext } from "../../src/contexts/AuthContext";
import type { AuthContextValue } from "../../src/contexts/AuthContext";
import { CurrencyProvider } from "../../src/contexts/CurrencyContext";
import { LanguageProvider } from "../../src/contexts/LanguageContext";

// Mock localStorage for CurrencyContext
beforeEach(() => {
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
};

const mockAuthAuthenticated: AuthContextValue = {
  user: {
    id: 1,
    email: "test@example.com",
    display_name: "Test User",
    avatar_url: null,
    auth_provider: "email",
    is_active: true,
  },
  loading: false,
  error: null,
  isAuthenticated: true,
  login: vi.fn().mockResolvedValue(null),
  register: vi.fn().mockResolvedValue(null),
  logout: vi.fn().mockResolvedValue(undefined),
};

function renderLayout(
  initialPath = "/",
  auth: AuthContextValue = mockAuthAuthenticated,
) {
  return render(
    <LanguageProvider>
      <AuthContext.Provider value={auth}>
        <CurrencyProvider>
          <MemoryRouter initialEntries={[initialPath]}>
            <Layout />
          </MemoryRouter>
        </CurrencyProvider>
      </AuthContext.Provider>
    </LanguageProvider>,
  );
}

describe("Layout", () => {
  it("renders the sidebar with navigation links when authenticated", () => {
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    expect(nav).toBeDefined();

    const links = nav.querySelectorAll("a");
    expect(links).toHaveLength(6);

    const linkTexts = Array.from(links).map((a) => a.textContent);
    expect(linkTexts).toContain("Dashboard");
    expect(linkTexts).toContain("My Collection");
    expect(linkTexts).toContain("Explore Cards");
    expect(linkTexts).toContain("Market Movers");
    expect(linkTexts).toContain("My Decks");
    expect(linkTexts).toContain("Price Scans");
  });

  it("hides protected nav items when unauthenticated", () => {
    renderLayout("/", mockAuthUnauthenticated);

    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");
    // Only public items: Dashboard, Explore Cards, Market Movers
    expect(links).toHaveLength(3);

    const linkTexts = Array.from(links).map((a) => a.textContent);
    expect(linkTexts).toContain("Dashboard");
    expect(linkTexts).toContain("Explore Cards");
    expect(linkTexts).toContain("Market Movers");
    expect(linkTexts).not.toContain("My Collection");
    expect(linkTexts).not.toContain("Price Scans");
  });

  it("renders the main content area (Outlet)", () => {
    renderLayout();
    const main = screen.getByTestId("main-content");
    expect(main).toBeDefined();
  });

  it("renders the sidebar element", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar).toBeDefined();
  });

  it("renders a hamburger button for mobile", () => {
    renderLayout();
    const hamburger = screen.getByTestId("hamburger-button");
    expect(hamburger).toBeDefined();
    expect(hamburger.getAttribute("aria-label")).toBe("Toggle navigation");
  });

  it("renders the app title", () => {
    renderLayout();
    // Title appears in both sidebar and mobile header
    const titles = screen.getAllByText("TCG Market");
    expect(titles.length).toBeGreaterThanOrEqual(1);
  });

  it("links have correct href attributes when authenticated", () => {
    renderLayout();
    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");

    const hrefs = Array.from(links).map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/collection");
    expect(hrefs).toContain("/cards");
    expect(hrefs).toContain("/market/movers");
    expect(hrefs).toContain("/scans");
  });

  // --- F07-T07: Responsive toggle tests ---

  it("hamburger button toggles sidebar visibility", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    const hamburger = screen.getByTestId("hamburger-button");

    // Initially sidebar is hidden (has -translate-x-full)
    expect(sidebar.className).toContain("-translate-x-full");

    // Click hamburger to open
    fireEvent.click(hamburger);
    expect(sidebar.className).toContain("translate-x-0");
    expect(sidebar.className).not.toContain("-translate-x-full");

    // Click hamburger again to close
    fireEvent.click(hamburger);
    expect(sidebar.className).toContain("-translate-x-full");
  });

  it("clicking overlay closes sidebar", () => {
    renderLayout();
    const hamburger = screen.getByTestId("hamburger-button");

    // Open sidebar
    fireEvent.click(hamburger);
    const overlay = screen.getByTestId("sidebar-overlay");
    expect(overlay).toBeDefined();

    // Click overlay to close
    fireEvent.click(overlay);
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("-translate-x-full");
  });

  it("nav links have focus-visible ring classes", () => {
    renderLayout();
    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");

    links.forEach((link) => {
      expect(link.className).toContain("focus-visible:ring-2");
      expect(link.className).toContain("focus-visible:ring-cyan-400");
    });
  });

  // --- Auth-aware user section tests ---

  it("shows sign-in link when unauthenticated", () => {
    renderLayout("/", mockAuthUnauthenticated);
    const signInLink = screen.getByTestId("sign-in-link");
    expect(signInLink).toBeDefined();
    expect(signInLink.textContent).toContain("Sign in");
  });

  it("shows user name and logout when authenticated", () => {
    renderLayout();
    const userSection = screen.getByTestId("user-section");
    expect(userSection.textContent).toContain("Test User");

    const logoutBtn = screen.getByTestId("logout-button");
    expect(logoutBtn).toBeDefined();
    expect(logoutBtn.textContent).toContain("Sign out");
  });

  it("contains a language selector in the sidebar", () => {
    renderLayout();
    expect(screen.getByTestId("sidebar-language-selector")).toBeDefined();
    expect(screen.getByTestId("language-selector")).toBeDefined();
  });
});
