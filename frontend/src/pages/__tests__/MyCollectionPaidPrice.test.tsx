import { render, screen, waitFor, within, fireEvent } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MyCollection } from "../MyCollection";
import type { CollectionCard } from "../../types/api";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
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
const mockPatchCollectionEntry = vi.fn();
const mockFetchPortfolioSummary = vi.fn();
const mockFetchPortfolioHistory = vi.fn();

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
    patchCollectionEntry: (...args: unknown[]) => mockPatchCollectionEntry(...args),
    fetchPortfolioSummary: (...args: unknown[]) => mockFetchPortfolioSummary(...args),
    fetchPortfolioHistory: (...args: unknown[]) => mockFetchPortfolioHistory(...args),
    exportPnlCsv: vi.fn(),
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

vi.mock("../../components/SetCompletionBar", () => ({
  SetCompletionSection: () => null,
}));

function renderWithRouter(initialEntries: string[] = ["/collection"]) {
  let location: ReturnType<typeof useLocation> | null = null;
  function LocationProbe() {
    location = useLocation();
    return null;
  }
  const utils = render(
    <MemoryRouter initialEntries={initialEntries}>
      <LocationProbe />
      <MyCollection />
    </MemoryRouter>,
  );
  return { ...utils, getLocation: () => location };
}

const emptySummary = {
  data: {
    total_unique: 0, total_cards: 0, sets_count: 0,
    linked_count: 0, total_value: null, banned_count: 0,
    recently_changed_count: 0,
  },
  errors: [], meta: {},
};

function makeCard(overrides: Partial<CollectionCard>): CollectionCard {
  return {
    id: 1,
    card_id: 10,
    set_code: "DOM",
    collector_number: "1",
    name_en: "Test Card",
    name_pt: null,
    set_name_en: "Dominaria",
    set_name_pt: null,
    notes: null,
    quantity: 1,
    quality: "NM",
    language: "EN",
    rarity: "R",
    color: null,
    extras: null,
    is_foil: false,
    latest_price: 20,
    price_source: null,
    currency: "BRL",
    image_url: null,
    acquisition_price: null,
    acquired_at: null,
    ...overrides,
  };
}

describe("MyCollection paid-price quick edit integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchCollectionSummary.mockResolvedValue(emptySummary);
    mockFetchCollectionSets.mockResolvedValue({ data: [], errors: [], meta: {} });
    mockFetchSetCompletion.mockResolvedValue({ data: [], errors: [], meta: {} });
    mockFetchPortfolioSummary.mockResolvedValue({
      data: {
        total_invested: 10,
        total_current_value: 20,
        total_pnl: 10,
        total_pnl_pct: 100,
        invested_card_count: 1,
      },
    });
    mockFetchPortfolioHistory.mockResolvedValue({ data: [] });
  });

  it("renders a quick-edit editor per tile with the right initial state", async () => {
    mockFetchCollection.mockResolvedValue({
      data: [
        makeCard({ id: 1, acquisition_price: 10 }),
        makeCard({ id: 2, acquisition_price: null }),
      ],
      errors: [],
      meta: { total: 2 },
    });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("paid-price-quick-edit-1")).toBeInTheDocument();
      expect(screen.getByTestId("paid-price-quick-edit-2")).toBeInTheDocument();
    });

    expect(within(screen.getByTestId("paid-price-quick-edit-1")).getByText(/collection.paidPrice/)).toBeInTheDocument();
    expect(within(screen.getByTestId("paid-price-quick-edit-2")).getByText("collection.setPaidPrice")).toBeInTheDocument();
  });

  it("saves a new paid price, updates the tile, and refetches the portfolio summary once", async () => {
    mockFetchCollection.mockResolvedValue({
      data: [makeCard({ id: 2, acquisition_price: null })],
      errors: [],
      meta: { total: 1 },
    });
    mockPatchCollectionEntry.mockResolvedValue({ data: { id: 2, acquisition_price: 15 } });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("paid-price-quick-edit-2")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockFetchPortfolioSummary).toHaveBeenCalledTimes(1);
    });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    fireEvent.change(screen.getByTestId("paid-price-field"), { target: { value: "15" } });
    fireEvent.click(screen.getByTestId("paid-price-save"));

    await waitFor(() => {
      expect(mockPatchCollectionEntry).toHaveBeenCalledWith(2, { acquisition_price: 15 });
    });

    await waitFor(() => {
      expect(within(screen.getByTestId("paid-price-quick-edit-2")).getByText(/collection.paidPrice/)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(mockFetchPortfolioSummary).toHaveBeenCalledTimes(2);
    });
  });

  it("clears the paid price and shows the set-paid-price prompt again", async () => {
    mockFetchCollection.mockResolvedValue({
      data: [makeCard({ id: 1, acquisition_price: 10 })],
      errors: [],
      meta: { total: 1 },
    });
    mockPatchCollectionEntry.mockResolvedValue({ data: { id: 1, acquisition_price: null } });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("paid-price-quick-edit-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    fireEvent.change(screen.getByTestId("paid-price-field"), { target: { value: "" } });
    fireEvent.click(screen.getByTestId("paid-price-save"));

    await waitFor(() => {
      expect(mockPatchCollectionEntry).toHaveBeenCalledWith(1, { acquisition_price: null });
    });

    await waitFor(() => {
      expect(within(screen.getByTestId("paid-price-quick-edit-1")).getByText("collection.setPaidPrice")).toBeInTheDocument();
    });
  });

  it("hides the editor while selection mode is on", async () => {
    mockFetchCollection.mockResolvedValue({
      data: [makeCard({ id: 1, acquisition_price: 10 })],
      errors: [],
      meta: { total: 1 },
    });

    renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("paid-price-quick-edit-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("select-mode-btn"));

    await waitFor(() => {
      expect(screen.queryByTestId("paid-price-quick-edit-1")).not.toBeInTheDocument();
    });
  });

  it("does not navigate to the detail page when interacting with the editor", async () => {
    mockFetchCollection.mockResolvedValue({
      data: [makeCard({ id: 1, acquisition_price: 10 })],
      errors: [],
      meta: { total: 1 },
    });
    mockPatchCollectionEntry.mockResolvedValue({ data: { id: 1, acquisition_price: 12 } });

    const { getLocation } = renderWithRouter();

    await waitFor(() => {
      expect(screen.getByTestId("paid-price-quick-edit-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("paid-price-edit-btn"));
    fireEvent.change(screen.getByTestId("paid-price-field"), { target: { value: "2" } });
    fireEvent.click(screen.getByTestId("paid-price-save"));

    await waitFor(() => {
      expect(mockPatchCollectionEntry).toHaveBeenCalled();
    });

    expect(getLocation()?.pathname).toBe("/collection");
  });
});
