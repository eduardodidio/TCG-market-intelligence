import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeckCardTile } from "../DeckCardTile";
import type { DeckCard } from "../../types/api";

vi.mock("../../hooks/useCardName", () => ({
  useCardName: () => ({
    getCardName: (en: string | null, pt: string | null, fallback: string) =>
      en || pt || fallback,
  }),
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

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts?.defaultValue ?? key,
  }),
}));

vi.mock("../../utils/format", () => ({
  formatBRL: (price: number) => `R$ ${price.toFixed(2)}`,
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

const baseDeckCard: DeckCard = {
  id: 10,
  name_en: "Sol Ring",
  name_pt: "Anel de Sol",
  set_code: "cmr",
  collector_number: "472",
  quantity: 1,
  card_id: 99,
  in_collection: true,
  owned_quantity: 1,
  collection_entry_id: 55,
  image_url: "https://example.com/sol-ring.jpg",
  latest_price: 12.5,
};

function renderTile(card?: Partial<DeckCard>) {
  return render(
    <MemoryRouter>
      <DeckCardTile card={{ ...baseDeckCard, ...card }} />
    </MemoryRouter>,
  );
}

describe("DeckCardTile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens CardPreviewModal when clicking the card image area", () => {
    renderTile();
    // The image area has cursor-zoom-in when image_url is present
    const img = screen.getByAltText("Sol Ring");
    // Click the parent div (the image area)
    fireEvent.click(img.closest(".cursor-zoom-in")!);
    expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
  });

  it("does not open modal when clicking the card name", () => {
    renderTile();
    fireEvent.click(screen.getByTestId("card-name"));
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });

  it("does not add click handler when card has no image_url", () => {
    renderTile({ image_url: null });
    // No cursor-zoom-in div should exist
    const tile = screen.getByTestId("deck-card-tile-10");
    const zoomDiv = tile.querySelector(".cursor-zoom-in");
    expect(zoomDiv).toBeNull();
  });

  it("closes CardPreviewModal when backdrop is clicked", () => {
    renderTile();
    const img = screen.getByAltText("Sol Ring");
    fireEvent.click(img.closest(".cursor-zoom-in")!);
    expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("modal-backdrop"));
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });
});
