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

vi.mock("../UpdatePrompt", () => ({
  UpdatePrompt: () => null,
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
    // Text spans should not be rendered in collapsed mode
    const spans = nav.querySelectorAll("a span");
    expect(spans.length).toBe(0);
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
