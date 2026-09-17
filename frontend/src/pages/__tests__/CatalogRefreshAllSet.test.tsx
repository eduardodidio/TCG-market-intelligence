import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CatalogPage } from "../CatalogPage";

// ---- Mock data ----

const mockCatalogCards = [
  {
    id: 1,
    name_en: "Card A",
    name_pt: null,
    set_code: "mh3",
    collector_number: "1",
    rarity: "R",
    color_identity: "W",
    mana_cost: "{1}{W}",
    type_line: "Creature",
    image_uri: "https://img.example.com/1.jpg",
    liga_price: 10.0,
    liga_price_date: "2026-09-15",
    owned: null,
  },
];

const mockSets = [
  { set_code: "mh3", card_count: 5, priced_count: 3 },
  { set_code: "fdn", card_count: 10, priced_count: 7 },
];

const mockStats = {
  total_cards: 100,
  total_sets: 10,
  cards_with_price: 50,
  cards_without_price: 50,
};

// ---- Mocks ----

const mockRefreshCatalogSet = vi.fn();
vi.mock("../../api/catalog", () => ({
  refreshCatalogSet: (...args: unknown[]) => mockRefreshCatalogSet(...args),
}));

vi.mock("../../api/cards", () => ({
  refreshCardPrice: vi.fn().mockResolvedValue({ data: null, errors: [] }),
}));

let mockIsAuthenticated = true;
vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: mockIsAuthenticated }),
}));

vi.mock("../../hooks/useCatalogCards", () => ({
  useCatalogCards: () => ({
    cards: mockCatalogCards,
    total: mockCatalogCards.length,
    loading: false,
    loadingMore: false,
    error: null,
    hasMore: false,
    loadMore: vi.fn(),
  }),
}));

vi.mock("../../hooks/useCatalogSets", () => ({
  useCatalogSets: () => ({
    sets: mockSets,
    loading: false,
    error: null,
  }),
}));

vi.mock("../../hooks/useCatalogStats", () => ({
  useCatalogStats: () => ({
    stats: mockStats,
    loading: false,
    error: null,
  }),
}));

const mockRefetchCredits = vi.fn();
vi.mock("../../hooks/useCredits", () => ({
  useCredits: () => ({
    balance: 100,
    bonusEligible: false,
    claimBonus: vi.fn(),
    refetch: mockRefetchCredits,
  }),
}));

vi.mock("../../hooks/useCardName", () => ({
  useCardName: () => ({
    getCardName: (en: string | null, pt: string | null, fallback: string) =>
      en || pt || fallback,
  }),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts?.defaultValue ?? key,
  }),
}));

vi.mock("react-parallax-tilt", () => ({
  default: ({
    children,
    className,
  }: {
    children: React.ReactNode;
    className?: string;
  }) => (
    <div data-testid="tilt-wrapper" className={className}>
      {children}
    </div>
  ),
}));

vi.mock("../../hooks/usePriceRequestPolling", () => ({
  usePriceRequestPolling: () => ({
    status: "none",
    isPolling: false,
    resultPrice: null,
  }),
}));

vi.mock("../../hooks/useGridSize", () => ({
  useGridSize: () => ({
    gridSize: "md" as const,
    setGridSize: vi.fn(),
  }),
}));

vi.mock("../../hooks/useScrollRestoration", () => ({
  useScrollRestoration: vi.fn(),
}));

vi.mock("../../hooks/useTreasureImage", () => ({
  useTreasureImage: () => "/treasure.png",
}));

describe("CatalogPage - Refresh All Set button", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
    mockRefreshCatalogSet.mockResolvedValue({
      data: { status: "queued", set_code: "mh3", card_count: 5, total_cost: 5 },
      errors: [],
    });
  });

  function renderWithSetSelected() {
    return render(
      <MemoryRouter initialEntries={["/catalog?set_code=mh3"]}>
        <CatalogPage />
      </MemoryRouter>,
    );
  }

  function renderWithoutSet() {
    return render(
      <MemoryRouter initialEntries={["/catalog"]}>
        <CatalogPage />
      </MemoryRouter>,
    );
  }

  it("renders Refresh All Set button when a set is selected", () => {
    renderWithSetSelected();
    expect(screen.getByTestId("refresh-all-set-btn")).toBeInTheDocument();
  });

  it("does NOT render Refresh All Set button when no set is selected", () => {
    renderWithoutSet();
    expect(screen.queryByTestId("refresh-all-set-btn")).not.toBeInTheDocument();
  });

  it("does NOT render Refresh All Set button when not authenticated", () => {
    mockIsAuthenticated = false;
    renderWithSetSelected();
    expect(screen.queryByTestId("refresh-all-set-btn")).not.toBeInTheDocument();
  });

  it("shows card count badge on the button", () => {
    renderWithSetSelected();
    const btn = screen.getByTestId("refresh-all-set-btn");
    // The button should show the card count (5 for mh3)
    expect(btn.textContent).toContain("5");
  });

  it("opens the credit confirm modal when clicked", () => {
    renderWithSetSelected();
    fireEvent.click(screen.getByTestId("refresh-all-set-btn"));
    expect(screen.getByTestId("credit-confirm-modal")).toBeInTheDocument();
  });

  it("calls refreshCatalogSet when confirmed", async () => {
    renderWithSetSelected();
    fireEvent.click(screen.getByTestId("refresh-all-set-btn"));
    fireEvent.click(screen.getByTestId("modal-confirm-btn"));

    await waitFor(() => {
      expect(mockRefreshCatalogSet).toHaveBeenCalledWith("mh3");
    });
  });

  it("shows success feedback after scan is queued", async () => {
    renderWithSetSelected();
    fireEvent.click(screen.getByTestId("refresh-all-set-btn"));
    fireEvent.click(screen.getByTestId("modal-confirm-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("scan-feedback")).toBeInTheDocument();
    });
  });

  it("shows error feedback when scan fails", async () => {
    mockRefreshCatalogSet.mockResolvedValue({
      data: null,
      errors: [{ code: "CREDIT_INSUFFICIENT", message: "Not enough tokens" }],
    });

    renderWithSetSelected();
    fireEvent.click(screen.getByTestId("refresh-all-set-btn"));
    fireEvent.click(screen.getByTestId("modal-confirm-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("scan-error")).toBeInTheDocument();
    });
  });

  it("closes modal when cancel is clicked", () => {
    renderWithSetSelected();
    fireEvent.click(screen.getByTestId("refresh-all-set-btn"));
    expect(screen.getByTestId("credit-confirm-modal")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("modal-cancel-btn"));
    expect(screen.queryByTestId("credit-confirm-modal")).not.toBeInTheDocument();
  });

  it("refetches credits after successful scan", async () => {
    renderWithSetSelected();
    fireEvent.click(screen.getByTestId("refresh-all-set-btn"));
    fireEvent.click(screen.getByTestId("modal-confirm-btn"));

    await waitFor(() => {
      expect(mockRefetchCredits).toHaveBeenCalled();
    });
  });
});
