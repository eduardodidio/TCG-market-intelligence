import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CardTile } from "../CardTile";
import type { CardSummary } from "../../types/api";

// Mock dependencies
vi.mock("../../api/cards", () => ({
  refreshCardPrice: vi.fn(),
}));

vi.mock("../../hooks/useAuth", () => ({
  useAuth: vi.fn(() => ({ isAuthenticated: true, user: { id: 1 } })),
}));

vi.mock("../../hooks/useCardName", () => ({
  useCardName: () => ({
    getCardName: (en: string | null, pt: string | null, fallback: string) =>
      en || pt || fallback,
  }),
}));

vi.mock("../../hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: "BRL" }),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts?.defaultValue ?? key,
  }),
}));

vi.mock("../../utils/format", () => ({
  formatPriceOrFallback: (price: number | null | undefined, _cur: string) =>
    price != null ? `R$ ${price.toFixed(2)}` : null,
}));

vi.mock("../../utils/scryfall", () => ({
  scryfallImageUrl: (set: string, num: string) =>
    `https://scryfall.com/${set}/${num}.jpg`,
  scryfallImageByName: (name: string) =>
    `https://scryfall.com/named/${name}.jpg`,
}));

const baseCard: CardSummary = {
  id: 42,
  name_en: "Lightning Bolt",
  name_pt: "Raio",
  set_code: "m10",
  collector_number: "146",
  latest_price: 3.5,
  game: "magic",
};

function renderTile(
  props?: Partial<React.ComponentProps<typeof CardTile>>,
) {
  return render(
    <MemoryRouter>
      <CardTile card={baseCard} {...props} />
    </MemoryRouter>,
  );
}

describe("CardTile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders card name and price", () => {
    renderTile();
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    expect(screen.getByTestId("card-price")).toHaveTextContent("R$ 3.50");
  });

  it("renders refresh button for authenticated user", () => {
    renderTile();
    expect(
      screen.getByTestId("refresh-card-price-42"),
    ).toBeInTheDocument();
  });

  it("hides refresh button for unauthenticated user", async () => {
    const { useAuth } = await import("../../hooks/useAuth");
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: false,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
      loading: false,
      error: null,
      register: vi.fn(),
      fetchProfile: vi.fn(),
      updateProfile: vi.fn(),
      changePassword: vi.fn(),
    } as ReturnType<typeof useAuth>);

    renderTile();
    expect(screen.queryByTestId("refresh-card-price-42")).not.toBeInTheDocument();

    // Restore
    vi.mocked(useAuth).mockReturnValue({
      isAuthenticated: true,
      user: { id: 1 },
    } as ReturnType<typeof useAuth>);
  });

  it("calls refreshCardPrice and updates display on success", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockResolvedValue({
      data: { ...baseCard, latest_price: 5.0 },
      error: null,
    } as Awaited<ReturnType<typeof refreshCardPrice>>);

    const onRefreshed = vi.fn();
    renderTile({ onPriceRefreshed: onRefreshed });

    fireEvent.click(screen.getByTestId("refresh-card-price-42"));

    await waitFor(() => {
      expect(refreshCardPrice).toHaveBeenCalledWith(42);
    });

    await waitFor(() => {
      expect(onRefreshed).toHaveBeenCalledWith(42, 5.0);
    });

    expect(screen.getByTestId("card-price")).toHaveTextContent("R$ 5.00");
  });

  it("disables button while refreshing", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    let resolvePromise: (v: unknown) => void;
    vi.mocked(refreshCardPrice).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      }) as ReturnType<typeof refreshCardPrice>,
    );

    renderTile();
    const btn = screen.getByTestId("refresh-card-price-42");

    fireEvent.click(btn);
    expect(btn).toBeDisabled();

    // Resolve and cleanup
    resolvePromise!({ data: { ...baseCard, latest_price: 4.0 }, error: null });
    await waitFor(() => {
      expect(btn).not.toBeDisabled();
    });
  });

  it("handles refresh failure gracefully", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockRejectedValue(new Error("Network error"));

    renderTile();
    fireEvent.click(screen.getByTestId("refresh-card-price-42"));

    await waitFor(() => {
      expect(refreshCardPrice).toHaveBeenCalledWith(42);
    });

    // Price should remain unchanged
    expect(screen.getByTestId("card-price")).toHaveTextContent("R$ 3.50");
  });

  it("shows set code badge", () => {
    renderTile();
    expect(screen.getByText("m10")).toBeInTheDocument();
  });

  it("links to card detail page", () => {
    renderTile();
    const link = screen.getByTestId("card-tile-42");
    expect(link).toHaveAttribute("href", "/cards/42");
  });

  it("uses linkTo prop when provided", () => {
    renderTile({ linkTo: "/collection/99" });
    const link = screen.getByTestId("card-tile-42");
    expect(link).toHaveAttribute("href", "/collection/99");
  });

  it("falls back to /cards/{id} when linkTo is not provided", () => {
    renderTile({ linkTo: undefined });
    const link = screen.getByTestId("card-tile-42");
    expect(link).toHaveAttribute("href", "/cards/42");
  });
});
