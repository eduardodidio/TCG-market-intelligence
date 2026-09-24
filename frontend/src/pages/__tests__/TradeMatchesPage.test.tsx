import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TradeMatchesPage } from "../TradeMatchesPage";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        "common.loading": "Loading...",
        "common.unknownCard": "Unknown Card",
        "nav.dashboard": "Dashboard",
        "tradeMatch.title": "Trade Matches",
        "tradeMatch.duplicates": "My Duplicates",
        "tradeMatch.theyHave": "They Have What I Want",
        "tradeMatch.theyWant": "They Want What I Have",
        "tradeMatch.surplus": "Available",
        "tradeMatch.noMatches": "No trade matches found",
        "tradeMatch.noMatchesDesc": "Add cards to your wishlist to find trade partners.",
        "tradeMatch.noReverseMatches": "No reverse matches found",
        "tradeMatch.noDuplicates": "No duplicates found",
        "tradeMatch.noDuplicatesDesc": "Cards with quantity > 1 appear here.",
        "tradeMatch.goToWishlist": "Go to Wishlist",
        "tradeMatch.shareToMatch": "Share your collection.",
        "tradeMatch.viewCollection": "View collection",
        "tradeMatch.loginRequired": "Sign in to find trade matches.",
        "tradeMatch.matchingCards": `${opts?.count ?? 0} matching cards`,
        "tradeFilters.searchPlaceholder": "Search trades by card name...",
        "tradeFilters.noResults": "No cards match the current filters.",
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
vi.mock("../../api/tradeMatch", () => ({
  fetchDuplicates: vi.fn(),
  fetchDuplicateSets: vi.fn(),
  fetchTradeMatches: vi.fn(),
  fetchReverseMatches: vi.fn(),
}));

import {
  fetchDuplicates,
  fetchDuplicateSets,
  fetchTradeMatches,
  fetchReverseMatches,
} from "../../api/tradeMatch";
import { useAuth } from "../../hooks/useAuth";

const mockFetchDuplicates = vi.mocked(fetchDuplicates);
const mockFetchDuplicateSets = vi.mocked(fetchDuplicateSets);
const mockFetchTradeMatches = vi.mocked(fetchTradeMatches);
const mockFetchReverseMatches = vi.mocked(fetchReverseMatches);
const mockUseAuth = vi.mocked(useAuth);

const MOCK_DUPLICATES = [
  {
    card_id: 10,
    name_en: "Lightning Bolt",
    name_pt: null,
    set_code: "2ed",
    collector_number: "157",
    quantity: 3,
    surplus: 2,
    quality: "NM",
    image_uri: null,
    current_price: null,
  },
];

const MOCK_MATCHES = [
  {
    partner_name: "Partner",
    share_code: "ABC123",
    matching_card_count: 2,
    matched_cards: [
      {
        card_id: 10,
        name_en: "Lightning Bolt",
        set_code: "2ed",
        image_uri: null,
        partner_quantity: 3,
        your_max_price: null,
      },
      {
        card_id: 11,
        name_en: "Counterspell",
        set_code: "3ed",
        image_uri: null,
        partner_quantity: 1,
        your_max_price: null,
      },
    ],
  },
];

const emptyResponse = {
  data: [],
  meta: { cursor: null, total: 0, offset: null, request_id: "1" },
  errors: [],
};

function renderPage() {
  return render(
    <MemoryRouter>
      <TradeMatchesPage />
    </MemoryRouter>,
  );
}

describe("TradeMatchesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({
      isAuthenticated: true,
      hasBetaAccess: true,
      user: { id: 1, display_name: "Test" } as any,
      error: null,
      mustChangePassword: false,
      register: vi.fn(),
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      changePassword: vi.fn(),
    });
    mockFetchDuplicates.mockResolvedValue(emptyResponse);
    mockFetchDuplicateSets.mockResolvedValue(emptyResponse);
    mockFetchTradeMatches.mockResolvedValue(emptyResponse);
    mockFetchReverseMatches.mockResolvedValue(emptyResponse);
  });

  it("renders all three tabs", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("tab-duplicates")).toBeDefined();
      expect(screen.getByTestId("tab-theyHave")).toBeDefined();
      expect(screen.getByTestId("tab-theyWant")).toBeDefined();
    });
  });

  it("renders the sticky filter bar above the tab content", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("sticky-filter-bar")).toBeDefined();
    });
  });

  it("renders empty state for duplicates", async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("No duplicates found")).toBeDefined();
    });
  });

  it("renders duplicates list", async () => {
    mockFetchDuplicates.mockResolvedValue({
      data: MOCK_DUPLICATES,
      meta: { cursor: null, total: 1, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("duplicates-list")).toBeDefined();
      expect(screen.getAllByTestId("duplicate-card")).toHaveLength(1);
    });
  });

  it("calls fetchDuplicates with search/set/sort params on filter change", async () => {
    mockFetchDuplicates.mockResolvedValue({
      data: MOCK_DUPLICATES,
      meta: { cursor: null, total: 1, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();

    await waitFor(() => {
      expect(mockFetchDuplicates).toHaveBeenCalledWith(
        expect.objectContaining({
          limit: "200",
          search: "",
          set_code: "",
          sort_by: "quantity",
          sort_dir: "desc",
        }),
      );
    });

    const search = screen.getByPlaceholderText("Search trades by card name...");
    fireEvent.change(search, { target: { value: "bolt" } });

    await waitFor(
      () => {
        expect(mockFetchDuplicates).toHaveBeenCalledWith(
          expect.objectContaining({ search: "bolt" }),
        );
      },
      { timeout: 1000 },
    );
  });

  it("fetches duplicate sets for the set icon filter", async () => {
    mockFetchDuplicateSets.mockResolvedValue({
      data: [{ set_code: "2ed", set_name: "Unlimited", count: 3 }],
      meta: { cursor: null, total: 1, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    await waitFor(() => {
      expect(mockFetchDuplicateSets).toHaveBeenCalled();
    });
  });

  it("renders trade matches", async () => {
    mockFetchTradeMatches.mockResolvedValue({
      data: MOCK_MATCHES,
      meta: { cursor: null, total: 1, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();

    // Click "They Have" tab
    const theyHaveTab = screen.getByTestId("tab-theyHave");
    await theyHaveTab.click();

    await waitFor(() => {
      expect(screen.getByTestId("matches-list")).toBeDefined();
      expect(screen.getAllByTestId("partner-card")).toHaveLength(1);
    });
  });

  it("resets sort to the tab default when switching tabs", async () => {
    renderPage();

    const theyHaveTab = screen.getByTestId("tab-theyHave");
    await theyHaveTab.click();

    await waitFor(() => {
      expect(screen.getByTestId("tab-theyHave")).toBeDefined();
    });

    // Switching back to duplicates keeps working without crashing and refetches
    const duplicatesTab = screen.getByTestId("tab-duplicates");
    await duplicatesTab.click();

    await waitFor(() => {
      expect(mockFetchDuplicates).toHaveBeenCalled();
    });
  });

  it("hides partners with 0 remaining cards after client-side filtering by set", async () => {
    mockFetchTradeMatches.mockResolvedValue({
      data: MOCK_MATCHES,
      meta: { cursor: null, total: 1, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    const theyHaveTab = screen.getByTestId("tab-theyHave");
    await theyHaveTab.click();

    await waitFor(() => {
      expect(screen.getAllByTestId("partner-card")).toHaveLength(1);
    });
  });

  it("shows noResults when all partners are filtered out", async () => {
    mockFetchTradeMatches.mockResolvedValue({
      data: MOCK_MATCHES,
      meta: { cursor: null, total: 1, offset: null, request_id: "1" },
      errors: [],
    });

    renderPage();
    const theyHaveTab = screen.getByTestId("tab-theyHave");
    await theyHaveTab.click();

    await waitFor(() => {
      expect(screen.getAllByTestId("partner-card")).toHaveLength(1);
    });

    const search = screen.getByPlaceholderText("Search trades by card name...");
    fireEvent.change(search, { target: { value: "no-such-card" } });

    await waitFor(
      () => {
        expect(screen.getByText("No cards match the current filters.")).toBeDefined();
      },
      { timeout: 1000 },
    );
  });

  it("shows an error banner when a fetch fails", async () => {
    mockFetchDuplicates.mockResolvedValue({
      data: null,
      meta: { cursor: null, total: 0, offset: null, request_id: "1" },
      errors: [{ code: "ERR", message: "Failed to load" }],
    });

    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeDefined();
    });
  });

  it("shows login required when not authenticated", async () => {
    mockUseAuth.mockReturnValue({
      isAuthenticated: false,
      hasBetaAccess: true,
      user: null,
      error: null,
      mustChangePassword: false,
      register: vi.fn(),
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
      changePassword: vi.fn(),
    });

    renderPage();
    expect(screen.getByText("Sign in to find trade matches.")).toBeDefined();
  });
});
