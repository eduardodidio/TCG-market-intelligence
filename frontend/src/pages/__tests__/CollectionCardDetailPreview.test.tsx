import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CollectionCardDetail } from "../CollectionCardDetail";
import { fetchCollectionEntry } from "../../api/collection";
import type { CollectionCardDetail as CollectionCardDetailType } from "../../types/api";

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

vi.mock("../../hooks/useCredits", () => ({
  useCredits: () => ({
    balance: 100,
    isAdmin: false,
    bonusEligible: false,
    claimBonus: vi.fn(),
    refetch: vi.fn(),
  }),
}));

vi.mock("../../hooks/usePendingDelete", () => ({
  usePendingDelete: () => ({
    setPendingDelete: vi.fn(),
  }),
}));

vi.mock("../../utils/format", () => ({
  formatCurrency: (price: number | null | undefined) =>
    price != null ? `R$ ${price.toFixed(2)}` : "N/A",
}));

vi.mock("../../utils/scryfall", () => ({
  scryfallImageUrl: (set: string, num: string) =>
    `https://scryfall.com/${set}/${num}.jpg`,
}));

vi.mock("../../api/collection", () => ({
  fetchCollectionEntry: vi.fn(),
  fetchCollectionHistory: vi.fn(),
  patchCollectionEntry: vi.fn(),
  refreshCardPrice: vi.fn(),
  refreshCardPriceLiga: vi.fn(),
  canonizeCard: vi.fn(),
}));

vi.mock("../../api/banlist", () => ({
  fetchCardBanHistory: vi.fn().mockResolvedValue({ data: [] }),
}));

// Stub components that are not relevant to these tests
vi.mock("../../components/AcquisitionPriceInput", () => ({
  AcquisitionPriceInput: () => <div data-testid="acquisition-input" />,
}));
vi.mock("../../components/Breadcrumb", () => ({
  Breadcrumb: () => <div data-testid="breadcrumb" />,
}));
vi.mock("../../components/BanEventCard", () => ({
  BanEventCard: () => <div data-testid="ban-event-card" />,
}));
vi.mock("../../components/CostBadge", () => ({
  CostBadge: () => <span data-testid="cost-badge" />,
}));
vi.mock("../../components/CreditConfirmModal", () => ({
  CreditConfirmModal: () => null,
}));
vi.mock("../../components/CurrencyIndicator", () => ({
  CurrencyIndicator: () => <span data-testid="currency-indicator" />,
}));
vi.mock("../../components/DeleteEntryButton", () => ({
  DeleteEntryButton: () => <button data-testid="delete-btn">Delete</button>,
}));
vi.mock("../../components/InlineEditField", () => ({
  InlineEditField: ({ value }: { value: string }) => <span data-testid="inline-edit">{value}</span>,
}));
vi.mock("../../components/LegalityPanel", () => ({
  LegalityPanel: () => <div data-testid="legality-panel" />,
}));
vi.mock("../../components/ErrorBanner", () => ({
  ErrorBanner: () => <div data-testid="error-banner" />,
}));
vi.mock("../../components/ManualPriceInput", () => ({
  ManualPriceInput: () => <div data-testid="manual-price" />,
}));
vi.mock("../../components/MetricsPanel", () => ({
  MetricsPanel: () => <div data-testid="metrics-panel" />,
}));
vi.mock("../../components/PnlBadge", () => ({
  PnlBadge: () => <span data-testid="pnl-badge" />,
}));
vi.mock("../../components/PriceChart", () => ({
  PriceChart: () => <div data-testid="price-chart" />,
}));
vi.mock("../../components/FoilBadge", () => ({
  FoilBadge: ({ variant }: { variant: string }) => <span data-testid="foil-badge">{variant}</span>,
}));
vi.mock("../../components/PriceSourceBadge", () => ({
  PriceSourceBadge: () => <span data-testid="price-source-badge" />,
}));
vi.mock("../../components/QuantityStepper", () => ({
  QuantityStepper: () => <div data-testid="quantity-stepper" />,
}));
vi.mock("../../components/Skeleton", () => ({
  SkeletonInfoPanel: () => <div data-testid="skeleton-info" />,
  SkeletonChartPanel: () => <div data-testid="skeleton-chart" />,
}));

const baseEntry: CollectionCardDetailType = {
  id: 99,
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
  price_history: [],
  source_cards: [],
  scryfall_url: null,
  ligamagic_url: null,
};

function renderPage(entry: CollectionCardDetailType = baseEntry) {
  vi.mocked(fetchCollectionEntry).mockResolvedValue({
    data: entry,
    meta: { cursor: null, total: null, offset: null, request_id: "1" },
    errors: [],
  });

  return render(
    <MemoryRouter initialEntries={[`/collection/${entry.id}`]}>
      <Routes>
        <Route path="/collection/:id" element={<CollectionCardDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("CollectionCardDetail — 3D Preview Modal (F125-T03)", () => {
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

  it("clicking card name opens CardPreviewModal", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    });

    const heading = screen.getByText("Lightning Bolt");
    fireEvent.click(heading);

    await waitFor(() => {
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    });
  });

  it("foil entry renders with foil shimmer in modal", async () => {
    const foilEntry: CollectionCardDetailType = {
      ...baseEntry,
      is_foil: true,
    };

    renderPage(foilEntry);

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("card-image"));

    await waitFor(() => {
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    });

    // The CardPreviewModal with isFoil=true renders a foil-shimmer wrapper
    const shimmer = document.querySelector(".foil-shimmer");
    expect(shimmer).toBeInTheDocument();
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

  it("Card3DTilt wraps the card image with foil prop", async () => {
    const foilEntry: CollectionCardDetailType = {
      ...baseEntry,
      is_foil: true,
    };

    renderPage(foilEntry);

    await waitFor(() => {
      expect(screen.getByTestId("card-image")).toBeInTheDocument();
    });

    // The tilt wrapper should exist (Card3DTilt wraps the image)
    const tiltWrapper = screen.getAllByTestId("tilt-wrapper")[0];
    expect(tiltWrapper).toBeInTheDocument();

    // When foil=true, Card3DTilt enables glare which our mock stores in data-props
    const props = JSON.parse(tiltWrapper.getAttribute("data-props") || "{}");
    expect(props.glareEnable).toBe(true);
  });
});
