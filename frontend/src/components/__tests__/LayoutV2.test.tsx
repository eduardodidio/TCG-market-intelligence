import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "../../contexts/ThemeContext";
import { LayoutV2 } from "../LayoutV2";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "nav.dashboard": "Dashboard",
        "nav.myCollection": "Collection",
        "nav.exploreCards": "Explore",
        "nav.catalog": "Catalog",
        "nav.alerts": "Alerts",
        "nav.signIn": "Sign In",
        "nav.signOut": "Sign Out",
        "nav.toggleNav": "Toggle navigation",
      };
      return map[key] ?? key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock useAuth
const mockLogout = vi.fn();
let mockAuthValue = {
  user: null as { display_name?: string; email?: string; is_admin?: boolean } | null,
  loading: false,
  error: null,
  isAuthenticated: false,
  mustChangePassword: false,
  login: vi.fn(),
  register: vi.fn(),
  logout: mockLogout,
  changePassword: vi.fn(),
  refreshProfile: vi.fn(),
};
vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => mockAuthValue,
}));

function renderLayout(initialRoute = "/") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <ThemeProvider>
        <Routes>
          <Route element={<LayoutV2 />}>
            <Route path="/" element={<div data-testid="dashboard-page">Dashboard</div>} />
            <Route path="/collection" element={<div data-testid="collection-page">Collection</div>} />
            <Route path="/cards" element={<div data-testid="cards-page">Explore</div>} />
            <Route path="/catalog" element={<div data-testid="catalog-page">Catalog</div>} />
            <Route path="/alerts" element={<div data-testid="alerts-page">Alerts</div>} />
          </Route>
        </Routes>
      </ThemeProvider>
    </MemoryRouter>,
  );
}

describe("LayoutV2", () => {
  beforeEach(() => {
    mockAuthValue = {
      user: null,
      loading: false,
      error: null,
      isAuthenticated: false,
      mustChangePassword: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: mockLogout,
      changePassword: vi.fn(),
      refreshProfile: vi.fn(),
    };
  });

  it("renders topbar with logo text", () => {
    renderLayout();
    expect(screen.getByTestId("v2-topbar")).toBeInTheDocument();
    expect(screen.getByTestId("v2-logo")).toBeInTheDocument();
    expect(screen.getByText("TEDHC Market")).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    renderLayout();
    const nav = screen.getByTestId("v2-nav");
    expect(nav).toBeInTheDocument();
    expect(screen.getByTestId("v2-nav-nav.dashboard")).toHaveTextContent("Dashboard");
    expect(screen.getByTestId("v2-nav-nav.myCollection")).toHaveTextContent("Collection");
    expect(screen.getByTestId("v2-nav-nav.exploreCards")).toHaveTextContent("Explore");
    expect(screen.getByTestId("v2-nav-nav.catalog")).toHaveTextContent("Catalog");
    expect(screen.getByTestId("v2-nav-nav.alerts")).toHaveTextContent("Alerts");
  });

  it("renders Outlet content", () => {
    renderLayout("/");
    expect(screen.getByTestId("v2-main-content")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
  });

  it("renders routed page through Outlet", () => {
    renderLayout("/collection");
    expect(screen.getByTestId("collection-page")).toBeInTheDocument();
  });

  it("NavLink shows active state for current route", () => {
    renderLayout("/catalog");
    const catalogLink = screen.getByTestId("v2-nav-nav.catalog");
    // NavLink with active state should have the accent class
    expect(catalogLink.className).toContain("text-v2-accent");
    // Other links should not have the accent class
    const dashboardLink = screen.getByTestId("v2-nav-nav.dashboard");
    expect(dashboardLink.className).toContain("text-v2-muted");
  });

  it("shows sign-in link when not authenticated", () => {
    renderLayout();
    expect(screen.getByTestId("v2-sign-in")).toBeInTheDocument();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
  });

  it("shows user menu when authenticated", () => {
    mockAuthValue = {
      ...mockAuthValue,
      user: { display_name: "John Doe", email: "john@test.com" },
      isAuthenticated: true,
    };
    renderLayout();
    expect(screen.getByTestId("v2-user-menu")).toBeInTheDocument();
    expect(screen.getByText("John Doe")).toBeInTheDocument();
    expect(screen.getByText("JD")).toBeInTheDocument(); // initials
  });

  it("renders bottom tab bar for mobile", () => {
    renderLayout();
    expect(screen.getByTestId("v2-bottom-tabs")).toBeInTheDocument();
  });

  it("renders hamburger button for mobile", () => {
    renderLayout();
    expect(screen.getByTestId("v2-hamburger")).toBeInTheDocument();
  });
});
