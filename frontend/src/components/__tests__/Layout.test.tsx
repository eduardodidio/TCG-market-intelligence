import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Layout } from "../Layout";

// Mock all dependencies used by Layout
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: 1, display_name: "Test User", email: "test@test.com", is_admin: false },
    isAuthenticated: true,
    hasBetaAccess: true,
    logout: vi.fn(),
  }),
}));

vi.mock("../../hooks/useGauchoEasterEgg", () => ({
  useGauchoEasterEgg: () => ({
    showIcon: false,
    showDialog: false,
    dialogData: null,
    openDialog: vi.fn(),
    dismissDialog: vi.fn(),
  }),
}));

vi.mock("../../hooks/usePendingDelete", () => ({
  usePendingDelete: () => ({
    pendingDelete: null,
    clearPendingDelete: vi.fn(),
    executeDelete: vi.fn(),
  }),
}));

vi.mock("../AlertBell", () => ({
  AlertBell: () => <div data-testid="mock-alert-bell">AlertBell</div>,
}));

vi.mock("../CurrencyToggle", () => ({
  CurrencyToggle: () => <div data-testid="mock-currency-toggle">CurrencyToggle</div>,
}));

vi.mock("../ExchangeRateBanner", () => ({
  ExchangeRateBanner: () => null,
}));

vi.mock("../InstallPrompt", () => ({
  InstallPrompt: () => <div data-testid="mock-install-prompt">InstallPrompt</div>,
}));

vi.mock("../LanguageSelector", () => ({
  LanguageSelector: () => <div data-testid="mock-language-selector">LanguageSelector</div>,
}));

vi.mock("../MarketTicker", () => ({
  MarketTicker: () => null,
}));

vi.mock("../OfflineBanner", () => ({
  OfflineBanner: () => null,
}));

vi.mock("../ThemeToggle", () => ({
  ThemeToggle: () => <div data-testid="mock-theme-toggle">ThemeToggle</div>,
}));

vi.mock("../TreasureBalance", () => ({
  TreasureBalance: () => <div data-testid="mock-treasure-balance">TreasureBalance</div>,
}));

vi.mock("../UndoToast", () => ({
  UndoToast: () => null,
}));

vi.mock("../ChimarraoIcon", () => ({
  ChimarraoIcon: () => null,
}));

vi.mock("../GauchoDialog", () => ({
  GauchoDialog: () => null,
}));

function renderLayout() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <Layout />
    </MemoryRouter>,
  );
}

describe("Layout — collapsible sidebar", () => {
  beforeEach(() => {
    localStorage.removeItem("sidebar-collapsed");
  });

  it("renders sidebar expanded by default (no localStorage value)", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    // Default: not collapsed — should have w-64 class for md
    expect(sidebar.className).toContain("md:w-64");
    expect(sidebar.className).not.toContain("md:w-16");
    // Full logo visible
    expect(screen.getByTestId("logo-expanded")).toBeInTheDocument();
  });

  it("clicking toggle collapses the sidebar", () => {
    renderLayout();
    const toggle = screen.getByTestId("sidebar-collapse-toggle");

    fireEvent.click(toggle);

    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("md:w-16");
    // Collapsed logo
    expect(screen.getByTestId("logo-collapsed")).toBeInTheDocument();
  });

  it("clicking toggle again expands the sidebar", () => {
    renderLayout();
    const toggle = screen.getByTestId("sidebar-collapse-toggle");

    // Collapse
    fireEvent.click(toggle);
    expect(screen.getByTestId("logo-collapsed")).toBeInTheDocument();

    // Expand
    fireEvent.click(toggle);
    expect(screen.getByTestId("logo-expanded")).toBeInTheDocument();
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("md:w-64");
  });

  it("updates localStorage on toggle", () => {
    renderLayout();
    const toggle = screen.getByTestId("sidebar-collapse-toggle");

    // Initially no value set by the component (or "false")
    fireEvent.click(toggle);
    expect(localStorage.getItem("sidebar-collapsed")).toBe("true");

    fireEvent.click(toggle);
    expect(localStorage.getItem("sidebar-collapsed")).toBe("false");
  });

  it("initializes collapsed when localStorage has sidebar-collapsed=true", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();

    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("md:w-16");
    expect(screen.getByTestId("logo-collapsed")).toBeInTheDocument();
  });

  it("shows title tooltips on nav items in collapsed mode", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    const links = nav.querySelectorAll("a[title]");
    // Should have title attributes on nav links in collapsed mode
    expect(links.length).toBeGreaterThan(0);
    // The dashboard link should have its label key as title
    const dashboardLink = nav.querySelector('a[href="/"]');
    expect(dashboardLink).toHaveAttribute("title", "nav.dashboard");
  });

  it("does not show title tooltips when expanded", () => {
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    const dashboardLink = nav.querySelector('a[href="/"]');
    expect(dashboardLink).not.toHaveAttribute("title");
  });

  it("renders nav item icons", () => {
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    const svgs = nav.querySelectorAll("svg");
    // At least one SVG icon per visible primary nav item (non-auth items: dashboard, cards, catalog = 3 min)
    // Plus the beta toggle chevron if beta items are visible
    expect(svgs.length).toBeGreaterThanOrEqual(3);
  });

  it("hides nav item text when collapsed", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    // Text spans should be sr-only in collapsed mode (accessible but visually hidden)
    const spans = nav.querySelectorAll("a span");
    spans.forEach((span) => {
      expect(span.className).toContain("sr-only");
    });
  });

  it("shows nav item text when expanded", () => {
    renderLayout();

    const nav = screen.getByTestId("sidebar-nav");
    const spans = nav.querySelectorAll("a span");
    expect(spans.length).toBeGreaterThan(0);
  });

  it("hides InstallPrompt when collapsed", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();

    expect(screen.queryByTestId("mock-install-prompt")).not.toBeInTheDocument();
  });

  it("shows InstallPrompt when expanded", () => {
    renderLayout();

    expect(screen.getByTestId("mock-install-prompt")).toBeInTheDocument();
  });

  it("mobile hamburger button is unaffected by collapsed state", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();

    // Hamburger button should still be present
    expect(screen.getByTestId("hamburger-button")).toBeInTheDocument();
  });

  it("mobile overlay is unaffected by collapsed state", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();

    // Click hamburger to open mobile sidebar
    fireEvent.click(screen.getByTestId("hamburger-button"));

    // Overlay should appear
    expect(screen.getByTestId("sidebar-overlay")).toBeInTheDocument();

    // Sidebar should have the mobile w-64 class when open (translate-x-0 w-64)
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("w-64");
  });
});

describe("Layout — sidebar scroll fix (F134)", () => {
  beforeEach(() => {
    localStorage.removeItem("sidebar-collapsed");
  });

  it("sidebar aside has flex flex-col layout classes", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("flex");
    expect(sidebar.className).toContain("flex-col");
  });

  it("fixed header zone has flex-shrink-0 class", () => {
    renderLayout();
    const header = screen.getByTestId("sidebar-header");
    expect(header.className).toContain("flex-shrink-0");
  });

  it("nav container parent has overflow-y-auto for scrolling", () => {
    renderLayout();
    const navContainer = screen.getByTestId("sidebar-nav-container");
    expect(navContainer.className).toContain("overflow-y-auto");
  });

  it("nav container has flex-1 to fill remaining space", () => {
    renderLayout();
    const navContainer = screen.getByTestId("sidebar-nav-container");
    expect(navContainer.className).toContain("flex-1");
  });

  it("scrollbar styling classes are present on nav container", () => {
    renderLayout();
    const navContainer = screen.getByTestId("sidebar-nav-container");
    expect(navContainer.className).toContain("scrollbar-thin");
    expect(navContainer.className).toContain("scrollbar-thumb-slate-600");
    expect(navContainer.className).toContain("scrollbar-track-transparent");
  });

  it("sidebar-nav is inside the scrollable container", () => {
    renderLayout();
    const nav = screen.getByTestId("sidebar-nav");
    const navContainer = screen.getByTestId("sidebar-nav-container");
    expect(navContainer.contains(nav)).toBe(true);
  });

  it("InstallPrompt is outside the scrollable container", () => {
    renderLayout();
    const installPrompt = screen.getByTestId("mock-install-prompt");
    const navContainer = screen.getByTestId("sidebar-nav-container");
    expect(navContainer.contains(installPrompt)).toBe(false);
    // InstallPrompt should be a descendant of the sidebar
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.contains(installPrompt)).toBe(true);
  });

  it("sidebar structure is: header, scrollable nav, install prompt", () => {
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    const header = screen.getByTestId("sidebar-header");
    const navContainer = screen.getByTestId("sidebar-nav-container");
    const installPrompt = screen.getByTestId("mock-install-prompt");

    // All three are direct or nested children of sidebar
    expect(sidebar.contains(header)).toBe(true);
    expect(sidebar.contains(navContainer)).toBe(true);
    expect(sidebar.contains(installPrompt)).toBe(true);

    // Header comes before nav container in DOM order
    const headerIndex = Array.from(sidebar.children).indexOf(header);
    const navContainerIndex = Array.from(sidebar.children).indexOf(navContainer);
    expect(headerIndex).toBeLessThan(navContainerIndex);
  });

  it("dark mode scrollbar class is present on nav container", () => {
    renderLayout();
    const navContainer = screen.getByTestId("sidebar-nav-container");
    expect(navContainer.className).toContain("dark:scrollbar-thumb-slate-500");
  });

  it("flex layout persists when sidebar is collapsed", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();
    const sidebar = screen.getByTestId("sidebar");
    expect(sidebar.className).toContain("flex");
    expect(sidebar.className).toContain("flex-col");

    const header = screen.getByTestId("sidebar-header");
    expect(header.className).toContain("flex-shrink-0");

    const navContainer = screen.getByTestId("sidebar-nav-container");
    expect(navContainer.className).toContain("flex-1");
    expect(navContainer.className).toContain("overflow-y-auto");
  });
});

describe("Layout — deck builder & evaluator nav (F133)", () => {
  beforeEach(() => {
    localStorage.removeItem("sidebar-collapsed");
    localStorage.setItem("tcg_beta_nav_open", "true");
  });

  it("renders Build Deck nav item in beta section", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const buildLink = betaItems.querySelector('a[href="/decks/build"]');
    expect(buildLink).toBeInTheDocument();
  });

  it("renders Deck Evaluator nav item in beta section", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const evalLink = betaItems.querySelector('a[href="/decks/evaluate"]');
    expect(evalLink).toBeInTheDocument();
  });

  it("Build Deck nav item shows correct label key", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const buildLink = betaItems.querySelector('a[href="/decks/build"]');
    expect(buildLink?.textContent).toContain("nav.buildDeck");
  });

  it("Deck Evaluator nav item shows correct label key", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const evalLink = betaItems.querySelector('a[href="/decks/evaluate"]');
    expect(evalLink?.textContent).toContain("nav.deckEvaluator");
  });

  it("Build Deck appears after Top Decks in beta nav order", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const links = Array.from(betaItems.querySelectorAll("a"));
    const hrefs = links.map((l) => l.getAttribute("href"));
    const topDecksIdx = hrefs.indexOf("/decks/ranking");
    const buildIdx = hrefs.indexOf("/decks/build");
    expect(topDecksIdx).toBeGreaterThanOrEqual(0);
    expect(buildIdx).toBeGreaterThan(topDecksIdx);
  });

  it("Deck Evaluator appears after Build Deck in beta nav order", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const links = Array.from(betaItems.querySelectorAll("a"));
    const hrefs = links.map((l) => l.getAttribute("href"));
    const buildIdx = hrefs.indexOf("/decks/build");
    const evalIdx = hrefs.indexOf("/decks/evaluate");
    expect(buildIdx).toBeGreaterThanOrEqual(0);
    expect(evalIdx).toBeGreaterThan(buildIdx);
  });

  it("beta section has correct total item count (12)", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const links = betaItems.querySelectorAll("a");
    // 10 original + 2 new (build deck, deck evaluator)
    expect(links.length).toBe(12);
  });

  it("Build Deck nav item has wrench icon SVG", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const buildLink = betaItems.querySelector('a[href="/decks/build"]');
    const svg = buildLink?.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("Deck Evaluator nav item has beaker icon SVG", () => {
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const evalLink = betaItems.querySelector('a[href="/decks/evaluate"]');
    const svg = evalLink?.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("shows title tooltips on new items when collapsed", () => {
    localStorage.setItem("sidebar-collapsed", "true");
    renderLayout();
    const betaItems = screen.getByTestId("beta-nav-items");
    const buildLink = betaItems.querySelector('a[href="/decks/build"]');
    expect(buildLink).toHaveAttribute("title", "nav.buildDeck");
    const evalLink = betaItems.querySelector('a[href="/decks/evaluate"]');
    expect(evalLink).toHaveAttribute("title", "nav.deckEvaluator");
  });
});
