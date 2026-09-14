import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CardDetail } from "../CardDetail";
import { fetchCardDetail } from "../../api/cards";
import type { CardDetail as CardDetailType } from "../../types/api";

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
    t: (key: string, opts?: Record<string, unknown>) =>
      opts?.defaultValue ?? key,
  }),
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: true, user: { id: 1 } }),
}));

vi.mock("../../hooks/useCardName", () => ({
  useCardName: () => ({
    getCardName: (en: string | null, pt: string | null, fallback: string) =>
      en || pt || fallback,
    getSubtitleName: () => null,
  }),
}));

vi.mock("../../hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: "BRL" }),
}));

vi.mock("../../utils/format", () => ({
  formatPriceOrFallback: (price: number | null | undefined) =>
    price != null ? `R$ ${price.toFixed(2)}` : null,
  formatDate: (d: string) => d,
}));

vi.mock("../../utils/scryfall", () => ({
  scryfallImageUrl: (set: string, num: string, version?: string) =>
    `https://scryfall.com/${set}/${num}${version ? `?v=${version}` : ""}.jpg`,
  scryfallImageByName: (name: string, version?: string) =>
    `https://scryfall.com/named/${name}${version ? `?v=${version}` : ""}.jpg`,
}));

vi.mock("../../api/cards", () => ({
  fetchCardDetail: vi.fn(),
}));

vi.mock("../../api/collection", () => ({
  refreshCardPrice: vi.fn(),
}));

vi.mock("../../components/PriceChart", () => ({
  PriceChart: () => <div data-testid="price-chart" />,
}));

vi.mock("../../components/Breadcrumb", () => ({
  Breadcrumb: () => <div data-testid="breadcrumb" />,
}));

vi.mock("../../components/SetAlertModal", () => ({
  SetAlertModal: () => <div data-testid="set-alert-modal" />,
}));

vi.mock("../../components/BatchAddModal", () => ({
  BatchAddModal: () => <div data-testid="batch-add-modal" />,
}));

vi.mock("../../components/AddToWishlistButton", () => ({
  AddToWishlistButton: () => <span data-testid="wishlist-btn" />,
}));

vi.mock("../../components/ErrorBanner", () => ({
  ErrorBanner: () => <div data-testid="error-banner" />,
}));

vi.mock("../../components/CurrencyIndicator", () => ({
  CurrencyIndicator: () => <span data-testid="currency-indicator" />,
}));

vi.mock("../../components/Skeleton", () => ({
  SkeletonInfoPanel: () => <div data-testid="skeleton-info" />,
  SkeletonChartPanel: () => <div data-testid="skeleton-chart" />,
}));

const baseCard: CardDetailType = {
  id: 42,
  game: "magic",
  name_en: "Lightning Bolt",
  name_pt: "Raio",
  set_code: "m10",
  collector_number: "146",
  latest_price: 3.5,
  source_cards: [],
  collection_entry_id: null,
  ligamagic_url: null,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};

function renderPage(card: CardDetailType = baseCard) {
  vi.mocked(fetchCardDetail).mockResolvedValue({
    data: card,
    meta: { cursor: null, total: null, offset: null, request_id: "1" },
    errors: [],
  });

  return render(
    <MemoryRouter initialEntries={[`/cards/${card.id}`]}>
      <Routes>
        <Route path="/cards/:id" element={<CardDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CardDetail — 3D Preview Modal (F125-T02)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clicking card image opens CardPreviewModal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("card-image"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    });
  });

  it("clicking card name (h1) opens CardPreviewModal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    });

    // The h1 element with the card name has the click handler
    const heading = screen.getByText("Lightning Bolt");
    fireEvent.click(heading);

    await waitFor(() => {
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    });
  });

  it("Escape closes the modal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("card-image"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    });

    fireEvent.keyDown(document, { key: "Escape" });

    await waitFor(() => {
      expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
    });
  });

  it("backdrop click closes the modal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("card-image"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("modal-backdrop"));

    await waitFor(() => {
      expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
    });
  });

  it("placeholder image does NOT open modal on click", async () => {
    // Card with no set_code, collector_number, or name_en will show placeholder
    const placeholderCard: CardDetailType = {
      ...baseCard,
      set_code: null,
      collector_number: null,
      name_en: "",
    };

    renderPage(placeholderCard);

    await waitFor(() => {
      expect(screen.getByTestId("card-image-placeholder")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("card-image-placeholder"));

    // Modal should NOT open since there is no image to preview
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });

  it("Card3DTilt wraps the card image", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeInTheDocument();
    });

    expect(screen.getByTestId("tilt-wrapper")).toBeInTheDocument();
  });
});
