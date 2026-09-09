import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "../../contexts/ThemeContext";
import { LayoutV2 } from "../../components/LayoutV2";
import { Layout } from "../../components/Layout";

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
        "nav.settings": "Settings",
        "nav.admin": "Admin",
        "nav.betaTest": "Beta Test",
        "nav.market": "Market",
        "nav.trending": "Trending",
        "nav.banlist": "Ban List",
        "nav.banHistory": "Ban History",
        "nav.myDecks": "My Decks",
        "nav.topDecks": "Top Decks",
        "nav.marketplace": "Marketplace",
        "nav.tradeMatches": "Trade Matches",
        "nav.achievements": "Achievements",
        "nav.evaluations": "Evaluations",
        "nav.wishlist": "Wishlist",
        "alerts.priceAlerts": "Price Alerts",
        "collection.deleteUndoMessage": "Deleted {{name}}",
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

// Mock hooks used by Layout
vi.mock("../../hooks/useGauchoEasterEgg", () => ({
  useGauchoEasterEgg: () => ({ showIcon: false, showDialog: false, dialogData: null }),
}));
vi.mock("../../hooks/usePendingDelete", () => ({
  usePendingDelete: () => ({ pendingDelete: null, clearPendingDelete: vi.fn(), executeDelete: vi.fn() }),
  PendingDeleteProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Mock Layout sub-components that are not relevant to this test
vi.mock("../../components/AlertBell", () => ({ AlertBell: () => null }));
vi.mock("../../components/CurrencyToggle", () => ({ CurrencyToggle: () => null }));
vi.mock("../../components/ExchangeRateBanner", () => ({ ExchangeRateBanner: () => null }));
vi.mock("../../components/InstallPrompt", () => ({ InstallPrompt: () => null }));
vi.mock("../../components/LanguageSelector", () => ({ LanguageSelector: () => null }));
vi.mock("../../components/MarketTicker", () => ({ MarketTicker: () => null }));
vi.mock("../../components/OfflineBanner", () => ({ OfflineBanner: () => null }));
vi.mock("../../components/TreasureBalance", () => ({ TreasureBalance: () => null }));
vi.mock("../../components/UpdatePrompt", () => ({ UpdatePrompt: () => null }));
vi.mock("../../components/UndoToast", () => ({ UndoToast: () => null }));
vi.mock("../../components/ChimarraoIcon", () => ({ ChimarraoIcon: () => null }));
vi.mock("../../components/GauchoDialog", () => ({ GauchoDialog: () => null }));

describe("V2 Routes", () => {
  beforeEach(() => {
    mockAuthValue = {
      user: { display_name: "Test User", email: "test@test.com" },
      loading: false,
      error: null,
      isAuthenticated: true,
      mustChangePassword: false,
      login: vi.fn(),
      register: vi.fn(),
      logout: mockLogout,
      changePassword: vi.fn(),
      refreshProfile: vi.fn(),
    };
  });

  it("/v2 route renders DashboardV2 content in LayoutV2", () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <ThemeProvider>
          <Routes>
            <Route element={<LayoutV2 />}>
              <Route path="/v2" element={<div data-testid="dashboard-v2">DashboardV2</div>} />
              <Route path="/v2/collection" element={<div data-testid="collection-v2">CollectionV2</div>} />
            </Route>
          </Routes>
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("v2-topbar")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-v2")).toBeInTheDocument();
  });

  it("/v2/collection route renders CollectionV2 content in LayoutV2", () => {
    render(
      <MemoryRouter initialEntries={["/v2/collection"]}>
        <ThemeProvider>
          <Routes>
            <Route element={<LayoutV2 />}>
              <Route path="/v2" element={<div data-testid="dashboard-v2">DashboardV2</div>} />
              <Route path="/v2/collection" element={<div data-testid="collection-v2">CollectionV2</div>} />
            </Route>
          </Routes>
        </ThemeProvider>
      </MemoryRouter>,
    );
    expect(screen.getByTestId("v2-topbar")).toBeInTheDocument();
    expect(screen.getByTestId("collection-v2")).toBeInTheDocument();
  });

  it("LayoutV2 has 'Back to Classic' toggle linking to /", () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <ThemeProvider>
          <Routes>
            <Route element={<LayoutV2 />}>
              <Route path="/v2" element={<div>V2 Dashboard</div>} />
            </Route>
          </Routes>
        </ThemeProvider>
      </MemoryRouter>,
    );
    const toggle = screen.getByTestId("v2-back-to-classic");
    expect(toggle).toBeInTheDocument();
    expect(toggle).toHaveAttribute("href", "/");
  });

  it("Layout (v1) has 'Try New UI' toggle linking to /v2", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <ThemeProvider>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<div>V1 Dashboard</div>} />
            </Route>
          </Routes>
        </ThemeProvider>
      </MemoryRouter>,
    );
    const toggle = screen.getByTestId("try-new-ui");
    expect(toggle).toBeInTheDocument();
    expect(toggle).toHaveAttribute("href", "/v2");
    expect(toggle).toHaveTextContent("Try New UI");
  });

  it("LayoutV2 nav links point to /v2 paths for implemented pages", () => {
    render(
      <MemoryRouter initialEntries={["/v2"]}>
        <ThemeProvider>
          <Routes>
            <Route element={<LayoutV2 />}>
              <Route path="/v2" element={<div>V2 Dashboard</div>} />
            </Route>
          </Routes>
        </ThemeProvider>
      </MemoryRouter>,
    );
    const dashLink = screen.getByTestId("v2-nav-nav.dashboard");
    expect(dashLink).toHaveAttribute("href", "/v2");
    const collLink = screen.getByTestId("v2-nav-nav.myCollection");
    expect(collLink).toHaveAttribute("href", "/v2/collection");
  });
});
