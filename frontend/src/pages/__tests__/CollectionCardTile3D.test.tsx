import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MyCollection } from "../MyCollection";
import type { CollectionCard } from "../../types/api";

// --- Mocks ---

vi.mock("react-parallax-tilt", () => ({
  default: ({
    children,
    className,
    ...props
  }: {
    children: React.ReactNode;
    className?: string;
    [key: string]: unknown;
  }) => (
    <div data-testid="tilt-wrapper" className={className} data-props={JSON.stringify(props)}>
      {children}
    </div>
  ),
}));

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
  useCardName: () => ({
    getCardName: (en: string | null, pt: string | null, fallback: string) =>
      en || pt || fallback,
  }),
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

vi.mock("../../utils/format", () => ({
  formatCurrency: (price: number | null | undefined) =>
    price != null ? `R$ ${price.toFixed(2)}` : "N/A",
}));

vi.mock("../../utils/scryfall", () => ({
  scryfallImageUrl: (set: string, num: string) =>
    `https://scryfall.com/${set}/${num}.jpg`,
  scryfallImageByName: (name: string) =>
    `https://scryfall.com/named/${name}.jpg`,
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

const makeCard = (overrides?: Partial<CollectionCard>): CollectionCard => ({
  id: 1,
  card_id: 42,
  set_code: "m10",
  collector_number: "146",
  name_en: "Lightning Bolt",
  name_pt: "Raio",
  set_name_en: "Magic 2010",
  set_name_pt: null,
  notes: null,
  quantity: 1,
  quality: "NM",
  language: "EN",
  rarity: "C",
  color: "R",
  extras: null,
  is_foil: false,
  latest_price: 3.5,
  price_source: "liga",
  currency: "BRL",
  image_url: null,
  acquisition_price: null,
  acquired_at: null,
  ...overrides,
});

const emptySummary = {
  data: {
    total_unique: 1,
    total_cards: 1,
    sets_count: 1,
    linked_count: 1,
    priced_count: 1,
    total_value: 3.5,
    banned_count: 0,
    recently_changed_count: 0,
  },
  errors: [],
  meta: {},
};

function renderPage(cards: CollectionCard[] = [makeCard()]) {
  mockFetchCollection.mockResolvedValue({
    data: cards,
    errors: [],
    meta: { total: cards.length },
  });
  mockFetchCollectionSummary.mockResolvedValue(emptySummary);
  mockFetchCollectionSets.mockResolvedValue({ data: [], errors: [], meta: {} });
  mockFetchSetCompletion.mockResolvedValue({ data: [], errors: [], meta: {} });

  return render(
    <MemoryRouter>
      <MyCollection />
    </MemoryRouter>,
  );
}

describe("CollectionCardTile — 3D & Preview Modal (F125-T01)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("Card3DTilt wraps the tile", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-1")).toBeInTheDocument();
    });

    // Card3DTilt mock renders data-testid="tilt-wrapper"
    const tiltWrappers = screen.getAllByTestId("tilt-wrapper");
    expect(tiltWrappers.length).toBeGreaterThanOrEqual(1);
  });

  it("clicking image area opens CardPreviewModal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-1")).toBeInTheDocument();
    });

    // The image area has cursor-zoom-in class and an onClick handler
    const imageArea = screen.getByTestId("collection-card-1").querySelector(".cursor-zoom-in");
    expect(imageArea).not.toBeNull();

    fireEvent.click(imageArea!);

    await waitFor(() => {
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    });
  });

  it("foil card passes isFoil=true (glare enabled on Card3DTilt)", async () => {
    const foilCard = makeCard({ is_foil: true });
    renderPage([foilCard]);

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-1")).toBeInTheDocument();
    });

    // When is_foil=true, Card3DTilt receives foil=true, which enables glare
    const tiltWrapper = screen.getAllByTestId("tilt-wrapper")[0];
    const props = JSON.parse(tiltWrapper.getAttribute("data-props") || "{}");
    expect(props.glareEnable).toBe(true);
  });

  it("hover:scale-[1.02] is not present in the component", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("collection-card-1")).toBeInTheDocument();
    });

    // Check the collection card tile element does not contain the old scale CSS class
    const tile = screen.getByTestId("collection-card-1");
    expect(tile.className).not.toContain("hover:scale-[1.02]");
    // Also check the parent link/wrapper
    expect(tile.parentElement?.className ?? "").not.toContain("hover:scale-[1.02]");
  });
});
