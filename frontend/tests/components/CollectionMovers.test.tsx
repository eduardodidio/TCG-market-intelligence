import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CollectionMovers } from "../../src/components/CollectionMovers";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "movers.title": "Collection Movers",
        "movers.gainers": "Top Gainers",
        "movers.losers": "Top Losers",
        "movers.noData": "Not enough price history yet",
        "movers.change": "Change",
        "movers.showTop10": "Show Top 10",
        "movers.showTop100": "Show Top 100",
        "movers.collapse": "Collapse",
      };
      return map[key] || key;
    },
  }),
}));

vi.mock("../../src/utils/format", () => ({
  formatCurrency: (value: number | null, _currency: string) => {
    if (value == null) return "--";
    return `R$ ${value.toFixed(2)}`;
  },
}));

const mockFetchCollectionMovers = vi.fn();

vi.mock("../../src/api/collection", () => ({
  fetchCollectionMovers: (...args: unknown[]) => mockFetchCollectionMovers(...args),
}));

beforeEach(() => {
  vi.clearAllMocks();
});

describe("CollectionMovers", () => {
  it("shows loading skeleton initially", () => {
    mockFetchCollectionMovers.mockReturnValue(new Promise(() => {}));
    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);
    expect(screen.getByTestId("movers-loading")).toBeInTheDocument();
  });

  it("shows empty state when no data", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: { gainers: [], losers: [], period_days: 7 },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-empty")).toBeInTheDocument();
      expect(screen.getByText("Not enough price history yet")).toBeInTheDocument();
    });
  });

  it("shows empty state when data is null", async () => {
    mockFetchCollectionMovers.mockResolvedValue({ data: null });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-empty")).toBeInTheDocument();
    });
  });

  it("renders gainers and losers columns", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [
          {
            card_id: 1,
            card_name: "Gainer Card",
            set_code: "SET1",
            image_uri: null,
            price_start: 10.0,
            price_end: 15.0,
            change_abs: 5.0,
            change_pct: 50.0,
          },
        ],
        losers: [
          {
            card_id: 2,
            card_name: "Loser Card",
            set_code: "SET2",
            image_uri: null,
            price_start: 20.0,
            price_end: 10.0,
            change_abs: -10.0,
            change_pct: -50.0,
          },
        ],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("collection-movers")).toBeInTheDocument();
      expect(screen.getByTestId("movers-gainers")).toBeInTheDocument();
      expect(screen.getByTestId("movers-losers")).toBeInTheDocument();
    });

    expect(screen.getByText("Top Gainers")).toBeInTheDocument();
    expect(screen.getByText("Top Losers")).toBeInTheDocument();
    expect(screen.getByText("Gainer Card")).toBeInTheDocument();
    expect(screen.getByText("Loser Card")).toBeInTheDocument();
  });

  it("displays green color for gainers", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [
          {
            card_id: 1,
            card_name: "Up Card",
            set_code: "SET",
            image_uri: null,
            price_start: 10.0,
            price_end: 15.0,
            change_abs: 5.0,
            change_pct: 50.0,
          },
        ],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      const gainerRows = screen.getAllByTestId("mover-row-gainer");
      expect(gainerRows).toHaveLength(1);
      // Check green color class is present
      const priceEl = gainerRows[0].querySelector(".text-emerald-400");
      expect(priceEl).toBeTruthy();
    });
  });

  it("displays red color for losers", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [],
        losers: [
          {
            card_id: 2,
            card_name: "Down Card",
            set_code: "SET",
            image_uri: null,
            price_start: 20.0,
            price_end: 10.0,
            change_abs: -10.0,
            change_pct: -50.0,
          },
        ],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      const loserRows = screen.getAllByTestId("mover-row-loser");
      expect(loserRows).toHaveLength(1);
      // Check red color class is present
      const priceEl = loserRows[0].querySelector(".text-red-400");
      expect(priceEl).toBeTruthy();
    });
  });

  it("displays set code in uppercase", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [
          {
            card_id: 1,
            card_name: "Card",
            set_code: "mh3",
            image_uri: null,
            price_start: 10.0,
            price_end: 15.0,
            change_abs: 5.0,
            change_pct: 50.0,
          },
        ],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByText("mh3")).toBeInTheDocument();
    });
  });

  it("passes custom days and limit to API", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: { gainers: [], losers: [], period_days: 30 },
    });

    render(<MemoryRouter><CollectionMovers days={30} limit={10} /></MemoryRouter>);

    await waitFor(() => {
      expect(mockFetchCollectionMovers).toHaveBeenCalledWith(30, 10, false);
    });
  });

  it("renders card image when image_uri is provided", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [
          {
            card_id: 1,
            card_name: "Image Card",
            set_code: "SET",
            image_uri: "https://example.com/card.jpg",
            price_start: 10.0,
            price_end: 15.0,
            change_abs: 5.0,
            change_pct: 50.0,
          },
        ],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      const img = screen.getByAltText("Image Card");
      expect(img).toBeInTheDocument();
      expect(img).toHaveAttribute("src", "https://example.com/card.jpg");
    });
  });

  it("shows top 10 button by default", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers limit={5} /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top10")).toBeInTheDocument();
      expect(screen.getByText("Show Top 10")).toBeInTheDocument();
    });
  });

  it("expand to top 10 re-fetches", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers limit={5} /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top10")).toBeInTheDocument();
    });

    mockFetchCollectionMovers.mockClear();
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    fireEvent.click(screen.getByTestId("movers-show-top10"));

    await waitFor(() => {
      expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 10, false);
    });
  });

  it("shows top 100 button after expanding to 10", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers limit={5} /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top10")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("movers-show-top10"));

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top100")).toBeInTheDocument();
      expect(screen.getByText("Show Top 100")).toBeInTheDocument();
    });
  });

  it("collapse button returns to initial limit", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers limit={5} /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top10")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("movers-show-top10"));

    await waitFor(() => {
      expect(screen.getByTestId("movers-collapse")).toBeInTheDocument();
    });

    mockFetchCollectionMovers.mockClear();
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    fireEvent.click(screen.getByTestId("movers-collapse"));

    await waitFor(() => {
      expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 5, false);
    });
  });

  it("handles expand when API returns fewer items than the limit", async () => {
    // Initial render with limit=5 returns 1 item
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Only Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers limit={5} /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top10")).toBeInTheDocument();
    });

    // Expand to top 10, but API still returns only 1 item
    mockFetchCollectionMovers.mockClear();
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Only Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    fireEvent.click(screen.getByTestId("movers-show-top10"));

    await waitFor(() => {
      expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 10, false);
      // Component still renders fine with fewer items than the limit
      expect(screen.getByTestId("collection-movers")).toBeInTheDocument();
      expect(screen.getAllByTestId("mover-row-gainer")).toHaveLength(1);
      // Show Top 100 button should appear (since we are at limit=10)
      expect(screen.getByTestId("movers-show-top100")).toBeInTheDocument();
      // Collapse button should appear
      expect(screen.getByTestId("movers-collapse")).toBeInTheDocument();
    });
  });

  it("shows error state when re-fetch after expand fails", async () => {
    // Initial render succeeds
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers limit={5} /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top10")).toBeInTheDocument();
    });

    // Expand to top 10 fails
    mockFetchCollectionMovers.mockClear();
    mockFetchCollectionMovers.mockRejectedValue(new Error("Network error"));

    fireEvent.click(screen.getByTestId("movers-show-top10"));

    await waitFor(() => {
      expect(screen.getByTestId("movers-error")).toBeInTheDocument();
    });

    // Retry button should be visible
    expect(screen.getByText("common.retry")).toBeInTheDocument();
  });

  it("retry from error state re-fetches with current limit", async () => {
    // Initial render succeeds
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers limit={5} /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-show-top10")).toBeInTheDocument();
    });

    // Expand to top 10 fails
    mockFetchCollectionMovers.mockClear();
    mockFetchCollectionMovers.mockRejectedValue(new Error("Network error"));

    fireEvent.click(screen.getByTestId("movers-show-top10"));

    await waitFor(() => {
      expect(screen.getByTestId("movers-error")).toBeInTheDocument();
    });

    // Retry should re-fetch with the expanded limit (10)
    mockFetchCollectionMovers.mockClear();
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [{ card_id: 1, card_name: "Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 }],
        losers: [],
        period_days: 7,
      },
    });

    fireEvent.click(screen.getByText("common.retry"));

    await waitFor(() => {
      expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 10, false);
      expect(screen.getByTestId("collection-movers")).toBeInTheDocument();
    });
  });

  it("mover rows render as links to card detail page", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [
          { card_id: 42, card_name: "Link Card", set_code: "SET", image_uri: null, price_start: 10, price_end: 15, change_abs: 5, change_pct: 50 },
        ],
        losers: [
          { card_id: 99, card_name: "Loser Link", set_code: "SET2", image_uri: null, price_start: 20, price_end: 10, change_abs: -10, change_pct: -50 },
        ],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      const gainerRow = screen.getByTestId("mover-row-gainer");
      expect(gainerRow.tagName).toBe("A");
      expect(gainerRow).toHaveAttribute("href", "/cards/42");

      const loserRow = screen.getByTestId("mover-row-loser");
      expect(loserRow.tagName).toBe("A");
      expect(loserRow).toHaveAttribute("href", "/cards/99");
    });
  });

  it("gainers link to correct card_id", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [
          { card_id: 101, card_name: "G1", set_code: "A", image_uri: null, price_start: 1, price_end: 2, change_abs: 1, change_pct: 100 },
          { card_id: 202, card_name: "G2", set_code: "B", image_uri: null, price_start: 5, price_end: 8, change_abs: 3, change_pct: 60 },
        ],
        losers: [],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      const rows = screen.getAllByTestId("mover-row-gainer");
      expect(rows).toHaveLength(2);
      expect(rows[0]).toHaveAttribute("href", "/cards/101");
      expect(rows[1]).toHaveAttribute("href", "/cards/202");
    });
  });

  it("losers link to correct card_id", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [],
        losers: [
          { card_id: 301, card_name: "L1", set_code: "X", image_uri: null, price_start: 20, price_end: 10, change_abs: -10, change_pct: -50 },
          { card_id: 402, card_name: "L2", set_code: "Y", image_uri: null, price_start: 30, price_end: 15, change_abs: -15, change_pct: -50 },
        ],
        period_days: 7,
      },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      const rows = screen.getAllByTestId("mover-row-loser");
      expect(rows).toHaveLength(2);
      expect(rows[0]).toHaveAttribute("href", "/cards/301");
      expect(rows[1]).toHaveAttribute("href", "/cards/402");
    });
  });

  it("empty state does not render links", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: { gainers: [], losers: [], period_days: 7 },
    });

    render(<MemoryRouter><CollectionMovers /></MemoryRouter>);

    await waitFor(() => {
      expect(screen.getByTestId("movers-empty")).toBeInTheDocument();
    });

    expect(screen.queryAllByRole("link")).toHaveLength(0);
  });
});
