import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CollectionMovers } from "../CollectionMovers";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "movers.error": "Failed to load movers",
        "movers.noData": "Not enough price history yet",
        "movers.title": "Collection Movers",
        "movers.gainers": "Top Gainers",
        "movers.losers": "Top Losers",
        "common.retry": "Retry",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

vi.mock("../../utils/format", () => ({
  formatCurrency: (v: number) => `R$ ${v.toFixed(2)}`,
}));

const mockFetchCollectionMovers = vi.fn();
vi.mock("../../api/collection", () => ({
  fetchCollectionMovers: (...args: unknown[]) => mockFetchCollectionMovers(...args),
}));

describe("CollectionMovers error handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows error state when fetch rejects", async () => {
    mockFetchCollectionMovers.mockRejectedValue(new Error("network error"));
    render(<CollectionMovers />);
    await waitFor(() => expect(screen.getByTestId("movers-error")).toBeInTheDocument());
    expect(screen.getByText("Failed to load movers")).toBeInTheDocument();
  });

  it("does not show loading skeleton when error state is active", async () => {
    mockFetchCollectionMovers.mockRejectedValue(new Error("network error"));
    render(<CollectionMovers />);
    await waitFor(() => expect(screen.getByTestId("movers-error")).toBeInTheDocument());
    expect(screen.queryByTestId("movers-loading")).not.toBeInTheDocument();
  });

  it("shows retry button on error", async () => {
    mockFetchCollectionMovers.mockRejectedValue(new Error("network error"));
    render(<CollectionMovers />);
    await waitFor(() => expect(screen.getByTestId("movers-error")).toBeInTheDocument());
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("re-fetches data when retry button is clicked", async () => {
    mockFetchCollectionMovers
      .mockRejectedValueOnce(new Error("network error"))
      .mockResolvedValueOnce({
        data: { gainers: [], losers: [], period_days: 7 },
        errors: [],
      });

    render(<CollectionMovers />);
    await waitFor(() => expect(screen.getByTestId("movers-error")).toBeInTheDocument());
    expect(mockFetchCollectionMovers).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByText("Retry"));
    await waitFor(() => expect(mockFetchCollectionMovers).toHaveBeenCalledTimes(2));
    // After successful retry, should show empty state (no gainers/losers)
    await waitFor(() => expect(screen.getByTestId("movers-empty")).toBeInTheDocument());
    expect(screen.queryByTestId("movers-error")).not.toBeInTheDocument();
  });

  it("shows empty state (not error) when fetch returns empty data", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: { gainers: [], losers: [], period_days: 7 },
      errors: [],
    });
    render(<CollectionMovers />);
    await waitFor(() => expect(screen.getByTestId("movers-empty")).toBeInTheDocument());
    expect(screen.queryByTestId("movers-error")).not.toBeInTheDocument();
  });
});
