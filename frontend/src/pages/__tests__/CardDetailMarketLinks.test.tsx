import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CardDetail } from "../CardDetail";
import { fetchCardDetail } from "../../api/cards";
import type { CardDetail as CardDetailType } from "../../types/api";

vi.mock("react-parallax-tilt", () => ({
  default: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
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
  scryfallImageUrl: (set: string, num: string) =>
    `https://scryfall.com/${set}/${num}.jpg`,
  scryfallImageByName: (name: string) =>
    `https://scryfall.com/named/${name}.jpg`,
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

describe("CardDetail — Market cross-links (F158-T01)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders market movers and price trends links", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("market-links")).toBeInTheDocument();
    });

    const links = screen.getByTestId("market-links");
    const anchors = links.querySelectorAll("a");
    expect(anchors).toHaveLength(2);
    expect(anchors[0]).toHaveAttribute("href", "/market/movers");
    expect(anchors[1]).toHaveAttribute("href", "/market/trending");
  });
});
