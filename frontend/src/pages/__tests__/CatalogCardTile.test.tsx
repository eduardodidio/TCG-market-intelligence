import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CatalogCardTile } from "../CatalogPage";
import type { CatalogCard } from "../../hooks/useCatalogCards";

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

function renderTile(card?: Partial<CatalogCard>, ownedView?: boolean) {
  return render(
    <MemoryRouter>
      <CatalogCardTile card={{ ...baseCatalogCard, ...card }} ownedView={ownedView} />
    </MemoryRouter>,
  );
}

describe("CatalogCardTile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
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
});
