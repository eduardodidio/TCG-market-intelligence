import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Trending } from "../Trending";
import type { ApiResponse, TrendingCardEntry, TrendingResponse } from "../../types/api";

vi.mock("react-i18next", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-i18next")>();
  return {
    ...actual,
    useTranslation: () => ({
      t: (key: string) => key,
      i18n: { language: "en" },
    }),
  };
});

const mockUseAuth = vi.fn();
vi.mock("../../hooks/useAuth", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("../../hooks/useCurrency", () => ({
  useCurrency: () => ({ currency: "BRL", setCurrency: vi.fn(), toggle: vi.fn() }),
}));

vi.mock("../../hooks/useOwnedCardIds", () => ({
  useOwnedCardIds: () => new Set<number>(),
}));

const mockFetchTrending = vi.fn();
vi.mock("../../api/trending", () => ({
  fetchTrending: (...args: unknown[]) => mockFetchTrending(...args),
}));

function makeCard(name: string): TrendingCardEntry {
  return {
    card_id: name === "Owned Card" ? 1 : 2,
    name_en: name,
    name_pt: null,
    set_code: "TST",
    collector_number: "1",
    image_url: null,
    price_start: 1,
    price_end: 2,
    change_pct: 10,
    change_abs: 1,
    consistency: 1,
    composite_score: 1,
    observation_count: 5,
    currency: "BRL",
  };
}

function makeResponse(name: string, cards: TrendingCardEntry[] = [makeCard(name)]): ApiResponse<TrendingResponse> {
  return {
    data: {
      cards,
      period: "30d",
      direction: "up",
      computed_at: new Date().toISOString(),
      cached: false,
    },
    errors: [],
    meta: {},
  };
}

function renderTrending() {
  return render(
    <MemoryRouter>
      <Trending />
    </MemoryRouter>,
  );
}

describe("Trending page — collection-only toggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true, user: { id: 1 } });
    mockFetchTrending.mockImplementation((_direction: string, params: Record<string, string>) => {
      const owned = params.collection_only === "true";
      return Promise.resolve(makeResponse(owned ? "Owned Card" : "Market Card"));
    });
  });

  it("defaults to collection-only mode for an authenticated user", async () => {
    renderTrending();

    await waitFor(() => expect(screen.getAllByText("Owned Card")).toHaveLength(2));

    expect(mockFetchTrending).toHaveBeenCalledWith(
      "gainers",
      expect.objectContaining({ collection_only: "true" }),
      expect.anything(),
    );
    expect(mockFetchTrending).toHaveBeenCalledWith(
      "losers",
      expect.objectContaining({ collection_only: "true" }),
      expect.anything(),
    );
  });

  it("switches both sections to market mode when the toggle is unchecked", async () => {
    renderTrending();

    await waitFor(() => expect(screen.getAllByText("Owned Card")).toHaveLength(2));

    const toggle = screen.getByTestId("collection-only-toggle").querySelector("input")!;
    fireEvent.click(toggle);

    await waitFor(() => expect(screen.getAllByText("Market Card")).toHaveLength(2));

    const marketCalls = mockFetchTrending.mock.calls.filter(
      ([, params]) => (params as Record<string, string>).collection_only === undefined,
    );
    expect(marketCalls.length).toBeGreaterThanOrEqual(2);
  });

  it("toggling off and back on returns to collection-only mode", async () => {
    renderTrending();

    await waitFor(() => expect(screen.getAllByText("Owned Card")).toHaveLength(2));

    const toggle = screen.getByTestId("collection-only-toggle").querySelector("input")!;
    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getAllByText("Market Card")).toHaveLength(2));

    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getAllByText("Owned Card")).toHaveLength(2));
  });

  it("does not render the toggle for unauthenticated users and always fetches market mode", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, user: null });
    renderTrending();

    await waitFor(() => expect(screen.getAllByText("Market Card")).toHaveLength(2));
    expect(screen.queryByTestId("collection-only-toggle")).not.toBeInTheDocument();

    for (const [, params] of mockFetchTrending.mock.calls) {
      expect((params as Record<string, string>).collection_only).toBeUndefined();
    }
  });

  it("shows an empty state without crashing when the market has no trending cards", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, user: null });
    mockFetchTrending.mockImplementation(() => Promise.resolve(makeResponse("Market Card", [])));

    renderTrending();

    await waitFor(() => expect(screen.getAllByTestId("empty-state")).toHaveLength(2));
    expect(screen.getAllByText("trending.noTrending")).toHaveLength(2);
  });

  it("shows an error banner with retry when fetchTrending rejects in market mode", async () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false, user: null });
    mockFetchTrending.mockRejectedValue(new Error("boom"));

    renderTrending();

    await waitFor(() => expect(screen.getAllByTestId("error-banner")).toHaveLength(2));

    mockFetchTrending.mockImplementation(() => Promise.resolve(makeResponse("Market Card")));

    const retryButtons = screen.getAllByText("common.retry");
    const callsBeforeRetry = mockFetchTrending.mock.calls.length;
    for (const button of retryButtons) {
      fireEvent.click(button);
    }

    expect(mockFetchTrending.mock.calls.length).toBeGreaterThan(callsBeforeRetry);
    await waitFor(() => expect(screen.getAllByText("Market Card")).toHaveLength(2));
  });

  it("does not let a slow collection response overwrite a faster market response after toggling off", async () => {
    let resolveCollection!: (value: ApiResponse<TrendingResponse>) => void;
    const collectionPromise = new Promise<ApiResponse<TrendingResponse>>((resolve) => {
      resolveCollection = resolve;
    });

    mockFetchTrending.mockImplementation((_direction: string, params: Record<string, string>) => {
      if (params.collection_only === "true") {
        return collectionPromise;
      }
      return Promise.resolve(makeResponse("Market Card"));
    });

    renderTrending();

    await waitFor(() => expect(screen.getAllByTestId("trending-loading")).toHaveLength(2));

    const toggle = screen.getByTestId("collection-only-toggle").querySelector("input")!;
    fireEvent.click(toggle);

    await waitFor(() => expect(screen.getAllByText("Market Card")).toHaveLength(2));

    resolveCollection(makeResponse("Owned Card"));

    await new Promise((r) => setTimeout(r, 0));
    expect(screen.getAllByText("Market Card")).toHaveLength(2);
    expect(screen.queryByText("Owned Card")).not.toBeInTheDocument();
  });
});
