import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { WishlistPage } from "../WishlistPage";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "common.loading": "Loading...",
        "common.delete": "Delete",
        "common.unknownCard": "Unknown Card",
        "nav.dashboard": "Dashboard",
        "wishlist.title": "Wishlist",
        "wishlist.searchPlaceholder": "Search wishlist...",
        "wishlist.tabs.wanted": "Wanted",
        "wishlist.tabs.acquired": "Acquired",
        "wishlist.emptyWanted": "No cards in your wishlist",
        "wishlist.emptyWantedDesc": "Browse the catalog and add cards you want.",
        "wishlist.emptyAcquired": "No acquired cards",
        "wishlist.emptyAcquiredDesc": "Cards you mark as acquired will appear here.",
        "wishlist.browseCatalog": "Browse Catalog",
        "wishlist.maxPrice": "Max price",
        "wishlist.markAcquired": "Mark as acquired",
        "wishlist.loginRequired": "Sign in to manage your wishlist.",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock hooks
vi.mock("../../hooks/useAuth", () => ({
  useAuth: vi.fn(() => ({
    isAuthenticated: true,
    user: { id: 1, display_name: "Test" },
  })),
}));

// Mock API
vi.mock("../../api/wishlist", () => ({
  fetchWishlist: vi.fn(),
  removeFromWishlist: vi.fn(),
  markWishlistAcquired: vi.fn(),
}));

import { fetchWishlist } from "../../api/wishlist";
import { useAuth } from "../../hooks/useAuth";

const mockFetchWishlist = vi.mocked(fetchWishlist);
const mockUseAuth = vi.mocked(useAuth);

const MOCK_ITEMS = [
  {
    id: 1,
    card_id: 10,
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "2ed",
    collector_number: "157",
    notes: null,
    max_price: 5.0,
    is_acquired: false,
    acquired_at: null,
    created_at: "2026-09-07T00:00:00",
    image_uri: null,
    current_price: null,
  },
  {
    id: 2,
    card_id: 20,
    name_en: "Counterspell",
    name_pt: null,
    set_code: "2ed",
    collector_number: "55",
    notes: "For EDH",
    max_price: null,
    is_acquired: false,
    acquired_at: null,
    created_at: "2026-09-07T00:00:00",
    image_uri: null,
    current_price: null,
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <WishlistPage />
    </MemoryRouter>,
  );
}

describe("WishlistPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      user: { id: 1, display_name: "Test" } as any,
      error: null,
      mustChangePassword: false,
      register: vi.fn(),
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });
  });

  it("renders empty state when no items", async () => {
    mockFetchWishlist.mockResolvedValue({
      data: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("empty-state")).toBeDefined();
    });
  });

  it("renders wishlist items", async () => {
    mockFetchWishlist.mockResolvedValue({
      data: MOCK_ITEMS,
      meta: { cursor: null, total: 2, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getAllByTestId("wishlist-card")).toHaveLength(2);
    });
  });

  it("renders tab bar with wanted and acquired tabs", async () => {
    mockFetchWishlist.mockResolvedValue({
      data: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("tab-wanted")).toBeDefined();
      expect(screen.getByTestId("tab-acquired")).toBeDefined();
    });
  });

  it("shows login required when not authenticated", async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      user: null,
      error: null,
      mustChangePassword: false,
      register: vi.fn(),
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    renderPage();
    expect(screen.getByText("Sign in to manage your wishlist.")).toBeDefined();
  });

  it("renders search input", async () => {
    mockFetchWishlist.mockResolvedValue({
      data: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    expect(screen.getByTestId("wishlist-search")).toBeDefined();
  });
});
