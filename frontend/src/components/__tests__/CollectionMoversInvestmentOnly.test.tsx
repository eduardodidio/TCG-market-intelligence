import { render, screen, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { CollectionMovers } from "../CollectionMovers";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
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

describe("CollectionMovers investmentOnly prop", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchCollectionMovers.mockResolvedValue({
      data: { gainers: [], losers: [], period_days: 7 },
      errors: [],
    });
  });

  it("passes investment_only=true to API when investmentOnly prop is true", async () => {
    render(<CollectionMovers investmentOnly />);
    await waitFor(() => expect(mockFetchCollectionMovers).toHaveBeenCalled());
    expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 5, true);
  });

  it("passes investment_only=false to API when investmentOnly prop is false", async () => {
    render(<CollectionMovers investmentOnly={false} />);
    await waitFor(() => expect(mockFetchCollectionMovers).toHaveBeenCalled());
    expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 5, false);
  });

  it("omits investmentOnly (defaults to false) when prop is not set", async () => {
    render(<CollectionMovers />);
    await waitFor(() => expect(mockFetchCollectionMovers).toHaveBeenCalled());
    expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 5, false);
  });

  it("forwards custom days and limit with investmentOnly", async () => {
    render(<CollectionMovers days={14} limit={3} investmentOnly />);
    await waitFor(() => expect(mockFetchCollectionMovers).toHaveBeenCalled());
    expect(mockFetchCollectionMovers).toHaveBeenCalledWith(14, 3, true);
  });
});
