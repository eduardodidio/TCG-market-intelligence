import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { Marketplace } from "../Marketplace";

vi.mock("react-i18next", () => ({
  initReactI18next: { type: "3rdParty", init: () => {} },
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        "nav.dashboard": "Dashboard",
        "nav.marketplace": "Marketplace",
        "marketplace.title": "Card Marketplace",
        "marketplace.myTrades": "My Trades",
        "marketplace.noListings": "No cards available for trade",
        "marketplace.interested": "I'm Interested",
        "marketplace.expressInterest": "Express Interest",
        "marketplace.tokens": "tokens",
        "marketplace.estimatedFee": `Fee: ${opts?.fee ?? 0} tokens`,
        "common.unknownCard": "Unknown Card",
        "common.noData": "No data",
        "common.retry": "Retry",
      };
      return translations[key] || key;
    },
  }),
}));

let loadMoreCallback: (() => void) | null = null;
vi.mock("../../hooks/useInfiniteScroll", () => ({
  useInfiniteScroll: (onLoadMore: () => void) => {
    loadMoreCallback = onLoadMore;
    return { current: null };
  },
}));

vi.mock("../../api/marketplace", () => ({
  fetchListings: vi.fn(),
  fetchListingSets: vi.fn(),
  expressInterest: vi.fn(),
}));

import { fetchListings, fetchListingSets } from "../../api/marketplace";

const mockFetchListings = vi.mocked(fetchListings);
const mockFetchListingSets = vi.mocked(fetchListingSets);

function mockListing(overrides: Record<string, unknown> = {}) {
  return {
    share_code: "abc123def456gh",
    entry_id: 1,
    card_name_en: "Lightning Bolt",
    card_name_pt: null,
    set_code: "lea",
    collector_number: "161",
    rarity: "C",
    quantity: 1,
    latest_price: 25.5,
    estimated_fee: 3,
    ...overrides,
  };
}

function makePage(count: number, offset: number) {
  return Array.from({ length: count }, (_, i) =>
    mockListing({ entry_id: offset + i + 1, share_code: `code-${offset + i + 1}` }),
  );
}

function renderPage(initialEntries = ["/marketplace"]) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Marketplace />
    </MemoryRouter>,
  );
}

describe("Marketplace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    loadMoreCallback = null;
    mockFetchListingSets.mockResolvedValue({ sets: [] });
  });

  it("loads 40 items then appends the next page on loadMore with offset=40", async () => {
    mockFetchListings
      .mockResolvedValueOnce({ listings: makePage(40, 0), count: 40 })
      .mockResolvedValueOnce({ listings: makePage(40, 40), count: 40 });

    renderPage();

    await waitFor(() => {
      expect(mockFetchListings).toHaveBeenCalledWith(
        expect.objectContaining({ limit: "40", offset: "0" }),
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-1")).toBeInTheDocument();
    });

    expect(loadMoreCallback).not.toBeNull();
    loadMoreCallback!();

    await waitFor(() => {
      expect(mockFetchListings).toHaveBeenLastCalledWith(
        expect.objectContaining({ offset: "40" }),
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-80")).toBeInTheDocument();
    });
  });

  it("hides the set filter when the sets API returns []", async () => {
    mockFetchListings.mockResolvedValue({ listings: [mockListing()], count: 1 });
    mockFetchListingSets.mockResolvedValue({ sets: [] });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-1")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("set-icon-filter")).not.toBeInTheDocument();
  });

  it("shows 'No data' for a listing with a null price", async () => {
    mockFetchListings.mockResolvedValue({
      listings: [mockListing({ latest_price: null })],
      count: 1,
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("No data")).toBeInTheDocument();
    });
  });

  it("does not enable further loading when fewer than 40 results are returned", async () => {
    mockFetchListings.mockResolvedValue({ listings: makePage(5, 0), count: 5 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-1")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("marketplace-sentinel")).toBeInTheDocument();

    // No more pages should be requested even if the callback were invoked externally.
    expect(mockFetchListings).toHaveBeenCalledTimes(1);
  });

  it("shows an ErrorBanner on fetch failure and retries on click", async () => {
    mockFetchListings
      .mockRejectedValueOnce(new Error("boom"))
      .mockResolvedValueOnce({ listings: [mockListing()], count: 1 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Retry"));

    await waitFor(() => {
      expect(mockFetchListings).toHaveBeenCalledTimes(2);
    });
    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-1")).toBeInTheDocument();
    });
  });

  it("still works without a set row when fetchListingSets rejects", async () => {
    mockFetchListings.mockResolvedValue({ listings: [mockListing()], count: 1 });
    mockFetchListingSets.mockRejectedValue(new Error("sets down"));

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("marketplace-card-1")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("set-icon-filter")).not.toBeInTheDocument();
  });

  it("seeds the search box from the legacy ?search= param", async () => {
    mockFetchListings.mockResolvedValue({ listings: [], count: 0 });

    renderPage(["/marketplace?search=bolt"]);

    await waitFor(() => {
      expect(screen.getByRole("textbox")).toHaveValue("bolt");
    });
  });

  it("only renders the latest result when a stale request resolves after a newer one", async () => {
    vi.useFakeTimers();
    try {
      let resolveStale: (v: { listings: ReturnType<typeof mockListing>[]; count: number }) => void;
      const stalePromise = new Promise<{ listings: ReturnType<typeof mockListing>[]; count: number }>(
        (resolve) => {
          resolveStale = resolve;
        },
      );
      const freshResult = {
        listings: [mockListing({ entry_id: 99, card_name_en: "Dark Ritual" })],
        count: 1,
      };

      mockFetchListings.mockReturnValueOnce(stalePromise);

      render(
        <MemoryRouter initialEntries={["/marketplace"]}>
          <Marketplace />
        </MemoryRouter>,
      );

      expect(mockFetchListings).toHaveBeenCalledTimes(1);

      mockFetchListings.mockResolvedValueOnce(freshResult);
      const input = screen.getByRole("textbox");
      fireEvent.change(input, { target: { value: "bolt" } });

      await vi.advanceTimersByTimeAsync(300);
      await vi.waitFor(() => expect(mockFetchListings).toHaveBeenCalledTimes(2));
      await vi.waitFor(() => expect(screen.getByTestId("marketplace-card-99")).toBeInTheDocument());

      resolveStale!({ listings: [mockListing({ entry_id: 1 })], count: 1 });
      await vi.runOnlyPendingTimersAsync();

      expect(screen.queryByTestId("marketplace-card-1")).not.toBeInTheDocument();
      expect(screen.getByTestId("marketplace-card-99")).toBeInTheDocument();
    } finally {
      vi.useRealTimers();
    }
  });
});
