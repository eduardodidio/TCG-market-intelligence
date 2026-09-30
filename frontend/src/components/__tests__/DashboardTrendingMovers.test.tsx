import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DashboardTrendingMovers } from "../DashboardTrendingMovers";
import type { TrendingCardEntry, TrendingResponse } from "../../types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "movers.gainers": "Top Gainers",
        "movers.losers": "Top Losers",
        "movers.noData": "Not enough price history yet",
        "common.retry": "Retry",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

vi.mock("../../hooks/useCardName", () => ({
  useCardName: () => ({
    getCardName: (name_en: string | null, name_pt: string | null) => name_en || name_pt || "Unknown",
    getSubtitleName: () => null,
  }),
}));

vi.mock("../../utils/format", () => ({
  formatCurrency: (v: number) => `R$ ${v.toFixed(2)}`,
}));

const mockFetchTrending = vi.fn();
vi.mock("../../api/trending", () => ({
  fetchTrending: (...args: unknown[]) => mockFetchTrending(...args),
}));

function makeTrendingEntry(overrides: Partial<TrendingCardEntry> = {}): TrendingCardEntry {
  return {
    card_id: 1,
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "m21",
    collector_number: "123",
    image_url: "https://example.com/bolt.jpg",
    price_start: 10,
    price_end: 15,
    change_pct: 50,
    change_abs: 5,
    consistency: 0.9,
    composite_score: 85,
    observation_count: 10,
    currency: "BRL",
    ...overrides,
  };
}

function makeTrendingResponse(cards: TrendingCardEntry[]): TrendingResponse {
  return {
    cards,
    period: "30d",
    direction: "up",
    computed_at: new Date().toISOString(),
    cached: false,
  };
}

function renderComponent(props: Partial<Parameters<typeof DashboardTrendingMovers>[0]> = {}) {
  return render(
    <MemoryRouter>
      <DashboardTrendingMovers
        direction="gainers"
        period="30d"
        currency="BRL"
        {...props}
      />
    </MemoryRouter>,
  );
}

describe("DashboardTrendingMovers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders gainers with MoverRow style (bg-slate-800 container, card names, price changes)", async () => {
    const card1 = makeTrendingEntry({ card_id: 1, name_en: "Lightning Bolt", change_abs: 5, change_pct: 50 });
    const card2 = makeTrendingEntry({ card_id: 2, name_en: "Counterspell", change_abs: 3, change_pct: 20 });
    mockFetchTrending.mockResolvedValue({ data: makeTrendingResponse([card1, card2]), errors: [] });

    renderComponent({ direction: "gainers" });

    await waitFor(() => expect(screen.getByTestId("dashboard-trending-gainers")).toBeInTheDocument());
    const container = screen.getByTestId("dashboard-trending-gainers");
    expect(container.className).toContain("bg-slate-800");
    expect(container.className).toContain("border-slate-600");
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    expect(screen.getByText("Counterspell")).toBeInTheDocument();
    expect(screen.getByText("Top Gainers")).toBeInTheDocument();
  });

  it("renders losers with red color header", async () => {
    const card = makeTrendingEntry({ card_id: 1, name_en: "Bad Card" });
    mockFetchTrending.mockResolvedValue({ data: makeTrendingResponse([card]), errors: [] });

    renderComponent({ direction: "losers" });

    await waitFor(() => expect(screen.getByTestId("dashboard-trending-losers")).toBeInTheDocument());
    const header = screen.getByText("Top Losers");
    expect(header.className).toContain("text-red-400");
  });

  it("shows loading skeleton", () => {
    mockFetchTrending.mockReturnValue(new Promise(() => {}));
    renderComponent({ direction: "gainers" });

    expect(screen.getByTestId("dashboard-trending-gainers-loading")).toBeInTheDocument();
  });

  it("shows error with retry", async () => {
    mockFetchTrending.mockRejectedValue(new Error("Network error"));
    renderComponent({ direction: "gainers" });

    await waitFor(() => expect(screen.getByTestId("dashboard-trending-gainers-error")).toBeInTheDocument());
    expect(screen.getByText("Retry")).toBeInTheDocument();

    // Retry should re-fetch
    mockFetchTrending.mockResolvedValue({
      data: makeTrendingResponse([makeTrendingEntry()]),
      errors: [],
    });
    fireEvent.click(screen.getByText("Retry"));
    await waitFor(() => expect(screen.getByTestId("dashboard-trending-gainers")).toBeInTheDocument());
  });

  it("shows empty state", async () => {
    mockFetchTrending.mockResolvedValue({ data: makeTrendingResponse([]), errors: [] });
    renderComponent({ direction: "gainers" });

    await waitFor(() => expect(screen.getByTestId("dashboard-trending-gainers-empty")).toBeInTheDocument());
    expect(screen.getByText("Not enough price history yet")).toBeInTheDocument();
  });

  it("maps image_url to image_uri correctly", async () => {
    const card = makeTrendingEntry({
      card_id: 42,
      name_en: "Sol Ring",
      image_url: "https://example.com/sol-ring.jpg",
    });
    mockFetchTrending.mockResolvedValue({ data: makeTrendingResponse([card]), errors: [] });

    renderComponent({ direction: "gainers" });

    await waitFor(() => expect(screen.getByTestId("dashboard-trending-gainers")).toBeInTheDocument());
    const img = screen.getByAltText("Sol Ring") as HTMLImageElement;
    expect(img.src).toBe("https://example.com/sol-ring.jpg");
  });

  it("passes collectionOnly param to API", async () => {
    mockFetchTrending.mockResolvedValue({ data: makeTrendingResponse([]), errors: [] });
    renderComponent({ direction: "gainers", collectionOnly: true });

    await waitFor(() => expect(mockFetchTrending).toHaveBeenCalled());
    const [direction, params] = mockFetchTrending.mock.calls[0];
    expect(direction).toBe("gainers");
    expect(params.collection_only).toBe("true");
  });

  it("each row links to /cards/{card_id}", async () => {
    const card = makeTrendingEntry({ card_id: 99, name_en: "Path to Exile" });
    mockFetchTrending.mockResolvedValue({ data: makeTrendingResponse([card]), errors: [] });

    renderComponent({ direction: "gainers" });

    await waitFor(() => expect(screen.getByTestId("dashboard-trending-gainers")).toBeInTheDocument());
    const link = screen.getByTestId("mover-row-gainer");
    expect(link).toHaveAttribute("href", "/cards/99");
  });
});
