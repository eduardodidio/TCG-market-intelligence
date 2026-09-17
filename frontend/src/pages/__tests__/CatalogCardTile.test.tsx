import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CatalogCardTile } from "../CatalogPage";
import type { CatalogCard } from "../../hooks/useCatalogCards";

// ---- Mocks ----

const mockRefreshCardPrice = vi.fn();
vi.mock("../../api/cards", () => ({
  refreshCardPrice: (...args: unknown[]) => mockRefreshCardPrice(...args),
}));

let mockIsAuthenticated = true;
vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: mockIsAuthenticated }),
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

// ---- Test data ----

const baseCatalogCard: CatalogCard = {
  id: 7,
  name_en: "Counterspell",
  name_pt: "Contramgica",
  set_code: "mh2",
  collector_number: "267",
  rarity: "U",
  color_identity: "U",
  mana_cost: "{U}{U}",
  type_line: "Instant",
  image_uri: "https://example.com/counterspell.jpg",
  liga_price: 8.0,
  liga_price_date: "2026-09-10",
  owned: null,
};

function renderTile(card?: Partial<CatalogCard>, ownedView?: boolean, compact?: boolean) {
  return render(
    <MemoryRouter>
      <CatalogCardTile card={{ ...baseCatalogCard, ...card }} ownedView={ownedView} compact={compact} />
    </MemoryRouter>,
  );
}

// ---- Tests ----

describe("CatalogCardTile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockIsAuthenticated = true;
  });

  it("opens CardPreviewModal when clicking the card image area", () => {
    renderTile();
    const imageArea = screen.getByAltText("Counterspell").closest(".cursor-zoom-in")!;
    fireEvent.click(imageArea);
    expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
  });

  it("does not open modal when clicking the card name", () => {
    renderTile();
    fireEvent.click(screen.getByText("Counterspell"));
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });

  it("does not add click handler when card has no image_uri", () => {
    renderTile({ image_uri: null });
    const tile = screen.getByTestId("catalog-card-7");
    const zoomDiv = tile.querySelector(".cursor-zoom-in");
    expect(zoomDiv).toBeNull();
  });

  it("closes CardPreviewModal when backdrop is clicked", () => {
    renderTile();
    const imageArea = screen.getByAltText("Counterspell").closest(".cursor-zoom-in")!;
    fireEvent.click(imageArea);
    expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("modal-backdrop"));
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });

  // --- T02: Per-card refresh button ---

  it("shows refresh button for authenticated users", () => {
    mockIsAuthenticated = true;
    renderTile();
    expect(screen.getByTestId("refresh-card-price-7")).toBeInTheDocument();
  });

  it("does NOT show refresh button for unauthenticated users", () => {
    mockIsAuthenticated = false;
    renderTile();
    expect(screen.queryByTestId("refresh-card-price-7")).not.toBeInTheDocument();
  });

  it("calls refreshCardPrice API when refresh button is clicked", async () => {
    mockRefreshCardPrice.mockResolvedValueOnce({
      data: { status: "queued", request_id: 1, card_id: 7 },
      errors: null,
    });
    renderTile();
    const btn = screen.getByTestId("refresh-card-price-7");
    fireEvent.click(btn);
    await waitFor(() => {
      expect(mockRefreshCardPrice).toHaveBeenCalledWith(7);
    });
  });

  it("disables button after successful queue", async () => {
    mockRefreshCardPrice.mockResolvedValueOnce({
      data: { status: "queued", request_id: 1, card_id: 7 },
      errors: null,
    });
    renderTile();
    const btn = screen.getByTestId("refresh-card-price-7");
    fireEvent.click(btn);
    await waitFor(() => {
      expect(btn).toBeDisabled();
    });
  });

  it("shows error icon when refresh fails with API error", async () => {
    mockRefreshCardPrice.mockResolvedValueOnce({
      data: null,
      errors: [{ code: "E001", message: "Not enough credits" }],
    });
    renderTile();
    const btn = screen.getByTestId("refresh-card-price-7");
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByTestId("error-icon")).toBeInTheDocument();
    });
  });

  it("shows error icon when refresh throws network error", async () => {
    mockRefreshCardPrice.mockRejectedValueOnce(new Error("Network error"));
    renderTile();
    const btn = screen.getByTestId("refresh-card-price-7");
    fireEvent.click(btn);
    await waitFor(() => {
      expect(screen.getByTestId("error-icon")).toBeInTheDocument();
    });
  });

  // --- T01: Compact mode ---

  it("hides card info section when compact is true", () => {
    renderTile({}, false, true);
    expect(screen.queryByText("Counterspell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("card-price")).not.toBeInTheDocument();
  });

  it("shows card info section when compact is false", () => {
    renderTile({}, false, false);
    expect(screen.getByText("Counterspell")).toBeInTheDocument();
    expect(screen.getByTestId("card-price")).toBeInTheDocument();
  });
});
