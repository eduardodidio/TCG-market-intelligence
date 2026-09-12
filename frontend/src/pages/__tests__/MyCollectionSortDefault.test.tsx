import { render, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MyCollection } from "../MyCollection";

/**
 * F123-T05: Validate that MyCollection ALWAYS defaults to price desc sort
 * from any entry point (direct nav, set filter, dashboard link, breadcrumb).
 */

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { language: "en" },
  }),
}));

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

const emptyApiResponse = { data: [], errors: [], meta: { total: 0 } };
const emptySummary = {
  data: {
    total_unique: 0, total_cards: 0, sets_count: 0,
    linked_count: 0, total_value: null, banned_count: 0,
    recently_changed_count: 0,
  },
  errors: [], meta: {},
};

function renderWithRoute(route: string) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <MyCollection />
    </MemoryRouter>,
  );
}

describe("F123-T05: Collection sort defaults to price desc from any entry point", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchCollection.mockResolvedValue(emptyApiResponse);
    mockFetchCollectionSummary.mockResolvedValue(emptySummary);
    mockFetchCollectionSets.mockResolvedValue({ data: [], errors: [], meta: {} });
    mockFetchSetCompletion.mockResolvedValue({ data: [], errors: [], meta: {} });
  });

  it("defaults to sort=price, dir=desc when navigating with no params", async () => {
    renderWithRoute("/");

    await waitFor(() => {
      expect(mockFetchCollection).toHaveBeenCalled();
    });

    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.sort_by).toBe("price");
    expect(params.sort_dir).toBe("desc");
  });

  it("defaults to sort=price, dir=desc when navigating with only set filter (SetCompletionBar path)", async () => {
    // Simulates clicking a set in SetCompletionBar: /collection?set=mh3
    renderWithRoute("/?set=mh3");

    await waitFor(() => {
      expect(mockFetchCollection).toHaveBeenCalled();
    });

    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.sort_by).toBe("price");
    expect(params.sort_dir).toBe("desc");
    expect(params.set).toBe("mh3");
  });

  it("defaults to sort=price, dir=desc when navigating with only name filter", async () => {
    renderWithRoute("/?name=Sol+Ring");

    await waitFor(() => {
      expect(mockFetchCollection).toHaveBeenCalled();
    });

    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.sort_by).toBe("price");
    expect(params.sort_dir).toBe("desc");
  });

  it("respects explicit sort=name&dir=asc from URL", async () => {
    renderWithRoute("/?sort=name&dir=asc");

    await waitFor(() => {
      expect(mockFetchCollection).toHaveBeenCalled();
    });

    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.sort_by).toBe("name");
    expect(params.sort_dir).toBe("asc");
  });

  it("respects explicit sort=added&dir=desc from URL", async () => {
    renderWithRoute("/?sort=added&dir=desc");

    await waitFor(() => {
      expect(mockFetchCollection).toHaveBeenCalled();
    });

    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.sort_by).toBe("added");
    expect(params.sort_dir).toBe("desc");
  });

  it("uses price desc even when set filter and other params are present but no sort", async () => {
    renderWithRoute("/?set=fdn&name=Island");

    await waitFor(() => {
      expect(mockFetchCollection).toHaveBeenCalled();
    });

    const params = mockFetchCollection.mock.calls[0][0] as Record<string, string>;
    expect(params.sort_by).toBe("price");
    expect(params.sort_dir).toBe("desc");
  });
});
