import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, act } from "@testing-library/react";
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
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
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
      hasBetaAccess: true,
      user: null,
      login: vi.fn(),
      logout: vi.fn(),
      loading: false,
      error: null,
      register: vi.fn(),
      mustChangePassword: false,
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

  it("calls refreshCardPrice and shows enqueued feedback on success", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockResolvedValue({
      data: { status: "queued", request_id: 123, card_id: 42 },
      error: null,
    } as Awaited<ReturnType<typeof refreshCardPrice>>);

    renderTile();

    await act(async () => {
      fireEvent.click(screen.getByTestId("refresh-card-price-42"));
    });

    expect(refreshCardPrice).toHaveBeenCalledWith(42);

    // Should show enqueued feedback
    expect(screen.getByTestId("enqueued-feedback")).toBeInTheDocument();
    expect(screen.getByTestId("check-icon")).toBeInTheDocument();

    // Price should remain unchanged
    expect(screen.getByTestId("card-price")).toHaveTextContent("R$ 3.50");
  });

  it("shows enqueued feedback for 1.5s then resets", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockResolvedValue({
      data: { status: "queued", request_id: 123, card_id: 42 },
      error: null,
    } as Awaited<ReturnType<typeof refreshCardPrice>>);

    renderTile();

    await act(async () => {
      fireEvent.click(screen.getByTestId("refresh-card-price-42"));
    });

    // Enqueued feedback visible
    expect(screen.getByTestId("enqueued-feedback")).toBeInTheDocument();
    expect(screen.getByTestId("check-icon")).toBeInTheDocument();

    // Advance 1.5s — feedback should disappear
    act(() => {
      vi.advanceTimersByTime(1500);
    });

    expect(screen.queryByTestId("enqueued-feedback")).not.toBeInTheDocument();
    expect(screen.queryByTestId("check-icon")).not.toBeInTheDocument();
  });

  it("button is clickable again immediately after enqueue (not disabled during feedback)", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockResolvedValue({
      data: { status: "queued", request_id: 123, card_id: 42 },
      error: null,
    } as Awaited<ReturnType<typeof refreshCardPrice>>);

    renderTile();
    const btn = screen.getByTestId("refresh-card-price-42");

    await act(async () => {
      fireEvent.click(btn);
    });

    // Enqueued feedback is showing, but button should NOT be disabled
    expect(screen.getByTestId("enqueued-feedback")).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
  });

  it("disables button only while refreshing (API call in progress)", async () => {
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
    // Disabled during API call
    expect(btn).toBeDisabled();

    // Resolve with queued response — button re-enables
    await act(async () => {
      resolvePromise!({ data: { status: "queued", request_id: 1, card_id: 42 }, error: null });
    });

    expect(btn).not.toBeDisabled();
  });

  it("does not use usePriceRequestPolling", async () => {
    // Verify that usePriceRequestPolling is not imported/used in CardTile
    // by checking that fetchPriceRequestStatus is never called
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockResolvedValue({
      data: { status: "queued", request_id: 123, card_id: 42 },
      error: null,
    } as Awaited<ReturnType<typeof refreshCardPrice>>);

    renderTile();

    await act(async () => {
      fireEvent.click(screen.getByTestId("refresh-card-price-42"));
    });

    // No spinner-icon (polling indicator) should appear
    expect(screen.queryByTestId("spinner-icon")).not.toBeInTheDocument();
    // No clock-icon (timeout indicator) should appear
    expect(screen.queryByTestId("clock-icon")).not.toBeInTheDocument();
  });

  it("handles rapid double-click (debounce during refreshing)", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    let resolvePromise: (v: unknown) => void;
    vi.mocked(refreshCardPrice).mockReturnValue(
      new Promise((resolve) => {
        resolvePromise = resolve;
      }) as ReturnType<typeof refreshCardPrice>,
    );

    renderTile();
    const btn = screen.getByTestId("refresh-card-price-42");

    // First click
    fireEvent.click(btn);
    // Second click while refreshing — should be ignored (button is disabled)
    fireEvent.click(btn);

    expect(refreshCardPrice).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolvePromise!({ data: { status: "queued", request_id: 1, card_id: 42 }, error: null });
    });
  });

  it("shows error icon and feedback on refresh failure (errors in response)", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockResolvedValue({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code: "TIMEOUT", message: "Request timed out" }],
    } as Awaited<ReturnType<typeof refreshCardPrice>>);

    renderTile();
    await act(async () => {
      fireEvent.click(screen.getByTestId("refresh-card-price-42"));
    });

    expect(screen.getByTestId("error-icon")).toBeInTheDocument();
    expect(screen.getByTestId("refresh-error-feedback")).toBeInTheDocument();
  });

  it("shows error state when refreshCardPrice throws", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockRejectedValue(new Error("Network error"));

    renderTile();
    await act(async () => {
      fireEvent.click(screen.getByTestId("refresh-card-price-42"));
    });

    expect(screen.getByTestId("error-icon")).toBeInTheDocument();
    expect(screen.getByTestId("refresh-error-feedback")).toBeInTheDocument();

    // Price should remain unchanged
    expect(screen.getByTestId("card-price")).toHaveTextContent("R$ 3.50");
  });

  it("error state clears after 3s", async () => {
    const { refreshCardPrice } = await import("../../api/cards");
    vi.mocked(refreshCardPrice).mockRejectedValue(new Error("Network error"));

    renderTile();
    await act(async () => {
      fireEvent.click(screen.getByTestId("refresh-card-price-42"));
    });

    expect(screen.getByTestId("error-icon")).toBeInTheDocument();
    expect(screen.getByTestId("refresh-error-feedback")).toBeInTheDocument();

    // Advance 3s — error should clear
    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByTestId("error-icon")).not.toBeInTheDocument();
    expect(screen.queryByTestId("refresh-error-feedback")).not.toBeInTheDocument();
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

  it("renders Card3DTilt wrapper", () => {
    renderTile();
    expect(screen.getByTestId("tilt-wrapper")).toBeInTheDocument();
  });

  it("opens CardPreviewModal when clicking the card image", () => {
    renderTile();
    const imagePlaceholder = screen.getByTestId("card-image-placeholder");
    fireEvent.click(imagePlaceholder);
    expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
  });

  it("does not open modal when clicking the card name", () => {
    renderTile();
    fireEvent.click(screen.getByText("Lightning Bolt"));
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });

  it("does not add click handler when card has no image", () => {
    renderTile({
      card: {
        ...baseCard,
        set_code: null,
        collector_number: null,
        name_en: null,
      },
    });
    const imagePlaceholder = screen.getByTestId("card-image-placeholder");
    fireEvent.click(imagePlaceholder);
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });

  it("closes CardPreviewModal when onClose is called", () => {
    renderTile();
    fireEvent.click(screen.getByTestId("card-image-placeholder"));
    expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
    // Click backdrop to close
    fireEvent.click(screen.getByTestId("modal-backdrop"));
    expect(screen.queryByTestId("modal-backdrop")).not.toBeInTheDocument();
  });

  describe("isFoil prop plumbing", () => {
    it("passes foil={true} to Card3DTilt when isFoil is true", () => {
      const { container } = renderTile({ isFoil: true });
      // Card3DTilt wraps children in a foil-shimmer div when foil=true
      expect(container.querySelector(".foil-shimmer")).toBeInTheDocument();
      // The Tilt mock captures glareEnable in data-props
      const tiltWrapper = screen.getAllByTestId("tilt-wrapper")[0];
      const props = JSON.parse(tiltWrapper.getAttribute("data-props") ?? "{}");
      expect(props.glareEnable).toBe(true);
    });

    it("passes foil={false} to Card3DTilt when isFoil is undefined", () => {
      const { container } = renderTile();
      // No foil-shimmer div when foil is false
      expect(container.querySelector(".foil-shimmer")).not.toBeInTheDocument();
      const tiltWrapper = screen.getAllByTestId("tilt-wrapper")[0];
      const props = JSON.parse(tiltWrapper.getAttribute("data-props") ?? "{}");
      expect(props.glareEnable).toBe(false);
    });

    it("passes isFoil to CardPreviewModal when preview is opened", () => {
      renderTile({ isFoil: true });
      // Open the preview modal by clicking the image
      fireEvent.click(screen.getByTestId("card-image-placeholder"));
      expect(screen.getByTestId("modal-backdrop")).toBeInTheDocument();
      // The modal renders its own Card3DTilt with foil={isFoil}
      const tiltWrappers = screen.getAllByTestId("tilt-wrapper");
      expect(tiltWrappers.length).toBeGreaterThanOrEqual(2);
      // The modal's tilt wrapper (last one) should also have glareEnable=true
      const modalTilt = tiltWrappers[tiltWrappers.length - 1];
      const modalProps = JSON.parse(modalTilt.getAttribute("data-props") ?? "{}");
      expect(modalProps.glareEnable).toBe(true);
    });
  });
});
