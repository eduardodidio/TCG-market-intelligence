import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MyCollection } from "../MyCollection";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts && "count" in opts) return `${key}:${opts.count}`;
      return key;
    },
    i18n: { language: "en" },
  }),
}));

// Mock hooks
vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: true, user: { id: 1, display_name: "Test" } }),
}));

vi.mock("../../hooks/useCredits", () => ({
  useCredits: () => ({
    balance: 100,
    isAdmin: false,
    bonusEligible: false,
    claimBonus: vi.fn(),
    refetch: vi.fn(),
  }),
}));

vi.mock("../../hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: "BRL", setCurrency: vi.fn() }),
}));

vi.mock("../../hooks/useGridSize", () => ({
  useGridSize: () => ({ gridSize: "md", setGridSize: vi.fn() }),
}));

vi.mock("../../hooks/useDebounce", () => ({
  useDebounce: (val: string) => val,
}));

vi.mock("../../hooks/useInfiniteScroll", () => ({
  useInfiniteScroll: () => ({ current: null }),
}));

vi.mock("../../hooks/useCardName", () => ({
  useCardName: () => ({ getCardName: (en: string) => en }),
}));

vi.mock("../../hooks/useCollectionRefresh", () => ({
  useCollectionRefresh: () => ({
    isRefreshing: false,
    progress: null,
    error: null,
    isDone: false,
    lastScannedCard: null,
    summary: null,
    startRefresh: vi.fn(),
    cancelRefresh: vi.fn(),
    dismissSummary: vi.fn(),
  }),
}));

vi.mock("../../hooks/useScrollRestoration", () => ({
  useScrollRestoration: vi.fn(),
}));

vi.mock("../../hooks/useMultiSelect", () => ({
  useMultiSelect: () => ({
    selectedIds: new Set(),
    toggle: vi.fn(),
    selectAll: vi.fn(),
    deselectAll: vi.fn(),
    count: 0,
  }),
}));

vi.mock("../../contexts/RoutePrefixContext", () => ({
  useRoutePrefix: () => "",
}));

// Mock API calls
const mockFetchCollection = vi.fn();
const mockFetchCollectionSummary = vi.fn();
const mockFetchCollectionSets = vi.fn();
const mockFetchSetCompletion = vi.fn();
const mockRefreshAllCollectionPrices = vi.fn();

vi.mock("../../api/collection", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/collection")>();
  return {
    ...actual,
    fetchCollection: (...args: unknown[]) => mockFetchCollection(...args),
    fetchCollectionSummary: (...args: unknown[]) => mockFetchCollectionSummary(...args),
    fetchCollectionSets: (...args: unknown[]) => mockFetchCollectionSets(...args),
    refreshCardPriceLiga: vi.fn(),
    bulkUpdateEntries: vi.fn(),
    bulkDeleteEntries: vi.fn(),
    fetchSetCompletion: (...args: unknown[]) => mockFetchSetCompletion(...args),
    refreshAllCollectionPrices: (...args: unknown[]) => mockRefreshAllCollectionPrices(...args),
  };
});

vi.mock("../../api/banEngine", () => ({
  fetchCollectionBanned: () => Promise.resolve({ data: [], errors: [], meta: {} }),
}));

vi.mock("../../api/collect", () => ({
  fetchCollectionHealth: () => Promise.resolve({ data: { status: "healthy", last_collection_at: null }, errors: [], meta: {} }),
}));

vi.mock("../../api/scans", () => ({
  fetchScanPreview: vi.fn(),
}));

vi.mock("../../api/marketplace", () => ({
  fetchSharingStatus: () => Promise.resolve({ is_shared: false }),
  toggleSharing: vi.fn(),
}));

vi.mock("../../components/PortfolioDashboard", () => ({
  PortfolioDashboard: () => <div data-testid="portfolio-dashboard" />,
}));

vi.mock("../../components/SetCompletionBar", () => ({
  SetCompletionSection: () => null,
}));

function renderWithRouter() {
  return render(
    <MemoryRouter initialEntries={["/"]}>
      <MyCollection />
    </MemoryRouter>,
  );
}

const summaryWithCards = {
  data: {
    total_unique: 10, total_cards: 15, sets_count: 2,
    linked_count: 8, total_value: null, banned_count: 0,
    recently_changed_count: 0,
  },
  errors: [], meta: {},
};

const emptyApiResponse = { data: [], errors: [], meta: { total: 0 } };

describe("MyCollection Queue Refresh All Prices (F148-T04)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchCollection.mockResolvedValue(emptyApiResponse);
    mockFetchCollectionSummary.mockResolvedValue(summaryWithCards);
    mockFetchCollectionSets.mockResolvedValue({ data: [], errors: [], meta: {} });
    mockFetchSetCompletion.mockResolvedValue({ data: [], errors: [], meta: {} });
  });

  it("renders the queue refresh button when collection has cards", async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("queue-refresh-all-btn")).toBeInTheDocument();
    });
  });

  it("does not render the queue refresh button when collection is empty", async () => {
    const emptySummary = {
      data: {
        total_unique: 0, total_cards: 0, sets_count: 0,
        linked_count: 0, total_value: null, banned_count: 0,
        recently_changed_count: 0,
      },
      errors: [], meta: {},
    };
    mockFetchCollectionSummary.mockResolvedValue(emptySummary);

    renderWithRouter();

    await waitFor(() => {
      expect(mockFetchCollectionSummary).toHaveBeenCalled();
    });

    expect(screen.queryByTestId("queue-refresh-all-btn")).not.toBeInTheDocument();
  });

  it("opens credit confirm modal when queue refresh button is clicked", async () => {
    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("queue-refresh-all-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("queue-refresh-all-btn"));

    // There should be two CreditConfirmModals now; the queue one should be visible
    await waitFor(() => {
      // The modal shows the action label
      const modals = screen.getAllByTestId("credit-confirm-modal");
      expect(modals.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("calls refreshAllCollectionPrices on confirm", async () => {
    mockRefreshAllCollectionPrices.mockResolvedValue({
      data: { status: "queued", card_count: 10, total_cost: 10, skipped: 0 },
      errors: [],
      meta: {},
    });

    // Mock alert to prevent jsdom error
    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("queue-refresh-all-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("queue-refresh-all-btn"));

    await waitFor(() => {
      const confirmBtns = screen.getAllByTestId("modal-confirm-btn");
      expect(confirmBtns.length).toBeGreaterThanOrEqual(1);
    });

    // Click the last confirm button (should be the queue modal)
    const confirmBtns = screen.getAllByTestId("modal-confirm-btn");
    fireEvent.click(confirmBtns[confirmBtns.length - 1]);

    await waitFor(() => {
      expect(mockRefreshAllCollectionPrices).toHaveBeenCalled();
    });

    alertSpy.mockRestore();
  });
});
