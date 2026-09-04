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
    preferred_language: null,
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

const mockAuthAdmin: AuthContextValue = {
  user: {
    id: 1,
    email: "admin@example.com",
    display_name: "Admin User",
    avatar_url: null,
    auth_provider: "email",
    preferred_language: null,
    is_active: true,
    is_admin: true,
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

/** Helper: expand beta nav section */
function expandBeta() {
  const toggle = screen.getByTestId("beta-nav-toggle");
  fireEvent.click(toggle);
}

/** Helper: get all visible link texts in the sidebar nav */
function getNavLinkTexts() {
  const nav = screen.getByTestId("sidebar-nav");
  return Array.from(nav.querySelectorAll("a")).map((a) => a.textContent);
}

describe("Layout", () => {
  // --- Primary nav items (always visible) ---

  it("renders primary nav items when authenticated (non-admin)", () => {
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");
    // Non-admin primary: Dashboard, My Collection, Explore Cards, Card Catalog, Settings (no Admin)
    expect(links).toHaveLength(5);

    const linkTexts = Array.from(links).map((a) => a.textContent);
    expect(linkTexts).toContain("Dashboard");
    expect(linkTexts).toContain("My Collection");
    expect(linkTexts).toContain("Explore Cards");
    expect(linkTexts).toContain("Card Catalog");
    expect(linkTexts).toContain("Settings");
    expect(linkTexts).not.toContain("Admin");
  });

  it("shows all nav items (primary + beta) when beta is expanded", () => {
    renderLayout();
    expandBeta();

    const linkTexts = getNavLinkTexts();
    // Primary (5) + Beta (8) = 13
    expect(linkTexts).toHaveLength(13);
    expect(linkTexts).toContain("Dashboard");
    expect(linkTexts).toContain("My Collection");
    expect(linkTexts).toContain("Explore Cards");
    expect(linkTexts).toContain("Market");
    expect(linkTexts).toContain("Trending");
    expect(linkTexts).toContain("Ban List");
    expect(linkTexts).toContain("Ban History");
    expect(linkTexts).toContain("My Decks");
    expect(linkTexts).toContain("Top Decks");
    expect(linkTexts).toContain("Marketplace");
    expect(linkTexts).toContain("Evaluations");
    expect(linkTexts).toContain("Settings");
    expect(linkTexts).not.toContain("Admin");
  });

  it("hides beta items when collapsed (default)", () => {
    renderLayout();

    const linkTexts = getNavLinkTexts();
    expect(linkTexts).not.toContain("Market");
    expect(linkTexts).not.toContain("Trending");
    expect(linkTexts).not.toContain("Ban List");
    expect(linkTexts).not.toContain("My Decks");
    expect(linkTexts).not.toContain("Marketplace");
  });

  it("hides protected nav items when unauthenticated", () => {
    renderLayout("/", mockAuthUnauthenticated);

    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");
    // Only public primary items: Dashboard, Explore Cards, Card Catalog
    expect(links).toHaveLength(3);

    const linkTexts = Array.from(links).map((a) => a.textContent);
    expect(linkTexts).toContain("Dashboard");
    expect(linkTexts).toContain("Explore Cards");
    expect(linkTexts).toContain("Card Catalog");
    expect(linkTexts).not.toContain("My Collection");
    expect(linkTexts).not.toContain("Settings");
  });

  it("shows public beta items when unauthenticated and expanded", () => {
    renderLayout("/", mockAuthUnauthenticated);
    expandBeta();

    const linkTexts = getNavLinkTexts();
    expect(linkTexts).toContain("Market");
    expect(linkTexts).toContain("Trending");
    expect(linkTexts).toContain("Ban List");
    expect(linkTexts).toContain("Ban History");
    // Auth-required beta items should be hidden
    expect(linkTexts).not.toContain("My Decks");
    expect(linkTexts).not.toContain("Top Decks");
    expect(linkTexts).not.toContain("Marketplace");
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
    const titles = screen.getAllByText("TEDHC Market");
    expect(titles.length).toBeGreaterThanOrEqual(1);
  });

  it("links have correct href attributes when authenticated", () => {
    renderLayout();
    expandBeta();

    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");

    const hrefs = Array.from(links).map((a) => a.getAttribute("href"));
    expect(hrefs).toContain("/");
    expect(hrefs).toContain("/collection");
    expect(hrefs).toContain("/cards");
    expect(hrefs).toContain("/market");
    expect(hrefs).toContain("/decks");
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
    expandBeta();

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

  // --- F48-T01: Nav active state uses exact match ---

  it("on /market, Market is active and Trending is NOT active", () => {
    renderLayout("/market");
    expandBeta();

    const nav = screen.getByTestId("sidebar-nav");
    const links = Array.from(nav.querySelectorAll("a"));
    const marketLink = links.find((a) => a.textContent === "Market");
    const trendingLink = links.find((a) => a.textContent === "Trending");
    expect(marketLink?.className).toContain("bg-indigo-500");
    expect(trendingLink?.className).not.toContain("bg-indigo-500");
  });

  it("on /market/trending, Trending is active and Market is NOT active", () => {
    renderLayout("/market/trending");
    expandBeta();

    const nav = screen.getByTestId("sidebar-nav");
    const links = Array.from(nav.querySelectorAll("a"));
    const marketLink = links.find((a) => a.textContent === "Market");
    const trendingLink = links.find((a) => a.textContent === "Trending");
    expect(trendingLink?.className).toContain("bg-indigo-500");
    expect(marketLink?.className).not.toContain("bg-indigo-500");
  });

  it("on /banlist, Ban List is active and Ban History is NOT active", () => {
    renderLayout("/banlist");
    expandBeta();

    const nav = screen.getByTestId("sidebar-nav");
    const links = Array.from(nav.querySelectorAll("a"));
    const banlistLink = links.find((a) => a.textContent === "Ban List");
    const banHistoryLink = links.find((a) => a.textContent === "Ban History");
    expect(banlistLink?.className).toContain("bg-indigo-500");
    expect(banHistoryLink?.className).not.toContain("bg-indigo-500");
  });

  it("on /decks, My Decks is active and Top Decks is NOT active", () => {
    renderLayout("/decks");
    expandBeta();

    const nav = screen.getByTestId("sidebar-nav");
    const links = Array.from(nav.querySelectorAll("a"));
    const decksLink = links.find((a) => a.textContent === "My Decks");
    const topDecksLink = links.find((a) => a.textContent === "Top Decks");
    expect(decksLink?.className).toContain("bg-indigo-500");
    expect(topDecksLink?.className).not.toContain("bg-indigo-500");
  });

  it("on /, only Dashboard is active", () => {
    renderLayout("/");
    const nav = screen.getByTestId("sidebar-nav");
    const links = Array.from(nav.querySelectorAll("a"));
    const dashboardLink = links.find((a) => a.textContent === "Dashboard");
    const otherLinks = links.filter((a) => a.textContent !== "Dashboard");
    expect(dashboardLink?.className).toContain("bg-indigo-500");
    otherLinks.forEach((link) => {
      expect(link.className).not.toContain("bg-indigo-500");
    });
  });

  it("on /collection, only My Collection is active", () => {
    renderLayout("/collection");
    const nav = screen.getByTestId("sidebar-nav");
    const links = Array.from(nav.querySelectorAll("a"));
    const collectionLink = links.find((a) => a.textContent === "My Collection");
    const otherLinks = links.filter((a) => a.textContent !== "My Collection");
    expect(collectionLink?.className).toContain("bg-indigo-500");
    otherLinks.forEach((link) => {
      expect(link.className).not.toContain("bg-indigo-500");
    });
  });

  // --- Admin nav visibility tests ---

  it("shows Admin link for admin users", () => {
    renderLayout("/", mockAuthAdmin);
    expandBeta();

    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a");
    // Admin sees 6 primary (Dashboard, My Collection, Explore Cards, Card Catalog, Settings, Admin)
    // + 8 beta = 14 total
    expect(links).toHaveLength(14);

    const linkTexts = Array.from(links).map((a) => a.textContent);
    expect(linkTexts).toContain("Admin");
  });

  it("hides Admin link for non-admin authenticated users", () => {
    renderLayout();
    const nav = screen.getByTestId("sidebar-nav");
    const linkTexts = Array.from(nav.querySelectorAll("a")).map(
      (a) => a.textContent,
    );
    expect(linkTexts).not.toContain("Admin");
  });

  it("hides Liga Status link for non-admin authenticated users", () => {
    renderLayout();
    expandBeta();
    const linkTexts = getNavLinkTexts();
    expect(linkTexts).not.toContain("Liga Status");
  });

  it("hides admin links for unauthenticated users", () => {
    renderLayout("/", mockAuthUnauthenticated);
    expandBeta();
    const linkTexts = getNavLinkTexts();
    expect(linkTexts).not.toContain("Admin");
    expect(linkTexts).not.toContain("Liga Status");
  });

  // --- Beta Test disclosure section ---

  it("renders Beta Test toggle button", () => {
    renderLayout();
    const toggle = screen.getByTestId("beta-nav-toggle");
    expect(toggle).toBeDefined();
    expect(toggle.textContent).toContain("Beta Test");
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
  });

  it("toggles beta section open and closed", () => {
    renderLayout();
    const toggle = screen.getByTestId("beta-nav-toggle");

    // Initially collapsed
    expect(screen.queryByTestId("beta-nav-items")).toBeNull();
    expect(toggle.getAttribute("aria-expanded")).toBe("false");

    // Open
    fireEvent.click(toggle);
    expect(screen.getByTestId("beta-nav-items")).toBeDefined();
    expect(toggle.getAttribute("aria-expanded")).toBe("true");

    // Close
    fireEvent.click(toggle);
    expect(screen.queryByTestId("beta-nav-items")).toBeNull();
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
  });

  it("persists beta open state to localStorage", () => {
    renderLayout();
    const toggle = screen.getByTestId("beta-nav-toggle");

    fireEvent.click(toggle);
    expect(localStorage.setItem).toHaveBeenCalledWith(
      "tcg_beta_nav_open",
      "true",
    );

    fireEvent.click(toggle);
    expect(localStorage.setItem).toHaveBeenCalledWith(
      "tcg_beta_nav_open",
      "false",
    );
  });

  it("restores beta open state from localStorage", () => {
    (localStorage.getItem as ReturnType<typeof vi.fn>).mockImplementation(
      (key: string) => (key === "tcg_beta_nav_open" ? "true" : null),
    );

    renderLayout();
    // Beta section should be open because localStorage returned "true"
    expect(screen.getByTestId("beta-nav-items")).toBeDefined();
  });

  it("chevron rotates when beta is expanded", () => {
    renderLayout();
    const toggle = screen.getByTestId("beta-nav-toggle");
    const svg = toggle.querySelector("svg");

    // Collapsed: no rotate-90
    expect(svg?.getAttribute("class")).not.toContain("rotate-90");

    // Expanded: rotate-90
    fireEvent.click(toggle);
    expect(svg?.getAttribute("class")).toContain("rotate-90");
  });
});
