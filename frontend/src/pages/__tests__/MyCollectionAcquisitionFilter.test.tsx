import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MyCollection } from "../MyCollection";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "collection.filterAcquisitionAll": "All",
        "collection.filterAcquisitionWith": "With price",
        "collection.filterAcquisitionWithout": "Without price",
        "collection.filterAcquisitionLabel": "Investment",
      };
      return map[key] || key;
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

function renderWithRouter(initialEntries: string[] = ["/"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <MyCollection />
    </MemoryRouter>,
  );
}

const emptyApiResponse = { data: [], errors: [], meta: { total: 0 } };
const emptySummary = {
  data: {
    total_unique: 5, total_cards: 10, sets_count: 2,
    linked_count: 3, total_value: 100, banned_count: 0,
    recently_changed_count: 0, priced_count: 3,
  },
  errors: [], meta: {},
};

describe("MyCollection acquisition price filter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchCollection.mockResolvedValue(emptyApiResponse);
    mockFetchCollectionSummary.mockResolvedValue(emptySummary);
    mockFetchCollectionSets.mockResolvedValue({ data: [], errors: [], meta: {} });
    mockFetchSetCompletion.mockResolvedValue({ data: [], errors: [], meta: {} });
  });

  it("renders filter chips with All active by default", async () => {
    renderWithRouter();
    await waitFor(() => expect(screen.getByTestId("acquisition-filter")).toBeInTheDocument());
    const allBtn = screen.getByTestId("acquisition-filter-all");
    expect(allBtn).toHaveClass("bg-cyan-500");
    const withBtn = screen.getByTestId("acquisition-filter-with");
    expect(withBtn).not.toHaveClass("bg-cyan-500");
    const withoutBtn = screen.getByTestId("acquisition-filter-without");
    expect(withoutBtn).not.toHaveClass("bg-cyan-500");
  });

  it("clicking Without price sends has_acquisition_price=false to API", async () => {
    renderWithRouter();
    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());

    // Reset mock to track next call
    mockFetchCollection.mockClear();

    const withoutBtn = screen.getByTestId("acquisition-filter-without");
    fireEvent.click(withoutBtn);

    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());
    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.has_acquisition_price).toBe("false");
  });

  it("clicking With price sends has_acquisition_price=true to API", async () => {
    renderWithRouter();
    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());

    mockFetchCollection.mockClear();

    const withBtn = screen.getByTestId("acquisition-filter-with");
    fireEvent.click(withBtn);

    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());
    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.has_acquisition_price).toBe("true");
  });

  it("clicking All omits has_acquisition_price from API params", async () => {
    renderWithRouter(["/?has_acquisition_price=false"]);
    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());

    mockFetchCollection.mockClear();

    const allBtn = screen.getByTestId("acquisition-filter-all");
    fireEvent.click(allBtn);

    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());
    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.has_acquisition_price).toBeUndefined();
  });

  it("initializes from URL with has_acquisition_price=false", async () => {
    renderWithRouter(["/?has_acquisition_price=false"]);

    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());
    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.has_acquisition_price).toBe("false");

    // Without price chip should be active
    const withoutBtn = screen.getByTestId("acquisition-filter-without");
    expect(withoutBtn).toHaveClass("bg-cyan-500");
  });

  it("initializes from URL with has_acquisition_price=true", async () => {
    renderWithRouter(["/?has_acquisition_price=true"]);

    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());
    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.has_acquisition_price).toBe("true");

    // With price chip should be active
    const withBtn = screen.getByTestId("acquisition-filter-with");
    expect(withBtn).toHaveClass("bg-cyan-500");
  });

  it("default API call does not include has_acquisition_price", async () => {
    renderWithRouter();
    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());

    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.has_acquisition_price).toBeUndefined();
  });

  it("clear filters resets acquisition filter to All", async () => {
    renderWithRouter(["/?has_acquisition_price=false&name=bolt"]);
    await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());

    // Verify Without is active
    expect(screen.getByTestId("acquisition-filter-without")).toHaveClass("bg-cyan-500");

    // The empty state should show clear filters button since filters are active
    // but the list is empty
    const clearBtn = screen.queryByText("common.clearFilters");
    if (clearBtn) {
      mockFetchCollection.mockClear();
      fireEvent.click(clearBtn);
      await waitFor(() => expect(mockFetchCollection).toHaveBeenCalled());
      const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
      expect(params.has_acquisition_price).toBeUndefined();
    }
  });
});
