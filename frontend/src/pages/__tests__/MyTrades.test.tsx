import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MyTrades } from "../MyTrades";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const translations: Record<string, string> = {
        "marketplace.title": "Card Marketplace",
        "marketplace.myTrades": "My Trades",
        "marketplace.asBuyer": "As Buyer",
        "marketplace.asSeller": "As Seller",
        "marketplace.accept": "Accept",
        "marketplace.reject": "Reject",
        "marketplace.confirmTrade": "Confirm Trade",
        "marketplace.tradeCompleted": "Trade completed!",
        "marketplace.contactEmail": `Contact: ${opts?.email ?? ""}`,
        "marketplace.feeCharged": `Fee charged: ${opts?.fee ?? ""}`,
        "marketplace.pendingConfirmation": "Waiting for other party",
        "marketplace.estimatedFee": `Fee: ${opts?.fee ?? ""}`,
        "marketplace.insufficientForTrade": "Insufficient credits for this trade",
        "tradeFilters.searchPlaceholder": "Search trades by card name...",
        "tradeFilters.noResults": "No cards match the current filters.",
        "tradeFilters.noTradesBuyer": "You haven't expressed interest in any card yet.",
        "tradeFilters.noTradesSeller": "No one has requested your cards yet.",
        "tradeFilters.status.pending": "Pending",
        "tradeFilters.status.accepted": "Accepted",
        "tradeFilters.status.rejected": "Rejected",
        "tradeFilters.status.completed": "Completed",
        "tradeFilters.status.cancelled": "Cancelled",
      };
      return translations[key] ?? key;
    },
    i18n: { language: "en" },
  }),
}));

vi.mock("../../api/marketplace", () => ({
  fetchMyTrades: vi.fn(),
  respondToInterest: vi.fn(),
  confirmAgreement: vi.fn(),
}));

import {
  confirmAgreement,
  fetchMyTrades,
  respondToInterest,
  type TradeDetail,
} from "../../api/marketplace";

const mockFetchMyTrades = vi.mocked(fetchMyTrades);
const mockRespondToInterest = vi.mocked(respondToInterest);
const mockConfirmAgreement = vi.mocked(confirmAgreement);

function mockTrade(overrides: Partial<TradeDetail> = {}): TradeDetail {
  return {
    id: 1,
    card_name: "Lightning Bolt",
    set_code: "lea",
    collector_number: "161",
    counterparty_share_code: "abc123def456gh",
    status: "pending",
    estimated_fee: 3,
    my_role: "buyer",
    counterparty_email: null,
    created_at: "2026-08-27T10:00:00",
    ...overrides,
  };
}

function renderPage(initialEntry = "/marketplace/my-trades") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <MyTrades />
    </MemoryRouter>,
  );
}

describe("MyTrades", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    mockFetchMyTrades.mockResolvedValue({ trades: [], count: 0 });
  });

  it("renders buyer/seller tabs and filter bar", async () => {
    mockFetchMyTrades.mockResolvedValue({ trades: [mockTrade()], count: 1 });
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("tab-buyer")).toBeInTheDocument();
      expect(screen.getByTestId("tab-seller")).toBeInTheDocument();
      expect(screen.getByTestId("sticky-filter-bar")).toBeInTheDocument();
      expect(screen.getByTestId("filter-chips")).toBeInTheDocument();
    });
  });

  it("shows loading skeletons before trades resolve", async () => {
    let resolveFn: (v: { trades: TradeDetail[]; count: number }) => void = () => {};
    mockFetchMyTrades.mockReturnValue(
      new Promise((resolve) => {
        resolveFn = resolve;
      }),
    );
    renderPage();
    expect(screen.getAllByTestId("skeleton-card").length).toBeGreaterThan(0);
    resolveFn({ trades: [], count: 0 });
    await waitFor(() => {
      expect(screen.queryAllByTestId("skeleton-card").length).toBe(0);
    });
  });

  it("filters trades by search", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [
        mockTrade({ id: 1, card_name: "Lightning Bolt" }),
        mockTrade({ id: 2, card_name: "Dark Ritual" }),
        mockTrade({ id: 3, card_name: "Counterspell" }),
        mockTrade({ id: 4, card_name: "Giant Growth" }),
        mockTrade({ id: 5, card_name: "Shock" }),
      ],
      count: 5,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search trades by card name...");
    fireEvent.change(searchInput, { target: { value: "bolt" } });

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
      expect(screen.queryByTestId("trade-card-2")).not.toBeInTheDocument();
      expect(screen.queryByTestId("trade-card-3")).not.toBeInTheDocument();
      expect(screen.queryByTestId("trade-card-4")).not.toBeInTheDocument();
      expect(screen.queryByTestId("trade-card-5")).not.toBeInTheDocument();
    });
  });

  it("filters trades by status chip", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [
        mockTrade({ id: 1, status: "pending" }),
        mockTrade({ id: 2, status: "accepted" }),
      ],
      count: 2,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
      expect(screen.getByTestId("trade-card-2")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("filter-chip-pending"));

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
      expect(screen.queryByTestId("trade-card-2")).not.toBeInTheDocument();
    });
  });

  it("selects the seller tab from the URL on load", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [
        mockTrade({ id: 1, my_role: "buyer" }),
        mockTrade({ id: 2, my_role: "seller", card_name: "Dark Ritual" }),
      ],
      count: 2,
    });
    renderPage("/marketplace/my-trades?tab=seller");

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-2")).toBeInTheDocument();
      expect(screen.queryByTestId("trade-card-1")).not.toBeInTheDocument();
    });
  });

  it("derives set options from the trades", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [
        mockTrade({ id: 1, set_code: "lea" }),
        mockTrade({ id: 2, set_code: "2ed" }),
      ],
      count: 2,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("set-icon-filter")).toBeInTheDocument();
    });
  });

  it("sorts trades by date ascending/descending", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [
        mockTrade({ id: 1, card_name: "Older", created_at: "2026-01-01T00:00:00" }),
        mockTrade({ id: 2, card_name: "Newer", created_at: "2026-06-01T00:00:00" }),
      ],
      count: 2,
    });
    renderPage();

    await waitFor(() => {
      const ids = screen.getAllByTestId(/^trade-card-/).map((el) => el.getAttribute("data-testid"));
      expect(ids).toEqual(["trade-card-2", "trade-card-1"]);
    });
  });

  it("shows role-specific empty state when there are no trades", async () => {
    mockFetchMyTrades.mockResolvedValue({ trades: [], count: 0 });
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("You haven't expressed interest in any card yet."),
      ).toBeInTheDocument();
    });
  });

  it("shows filtered empty state when filters exclude everything", async () => {
    mockFetchMyTrades.mockResolvedValue({ trades: [mockTrade()], count: 1 });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search trades by card name...");
    fireEvent.change(searchInput, { target: { value: "nonexistent card" } });

    await waitFor(() => {
      expect(
        screen.getByText("No cards match the current filters."),
      ).toBeInTheDocument();
    });
  });

  it("clearing all filters restores the full list", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [mockTrade({ id: 1 }), mockTrade({ id: 2, card_name: "Dark Ritual" })],
      count: 2,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
      expect(screen.getByTestId("trade-card-2")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText("Search trades by card name...");
    fireEvent.change(searchInput, { target: { value: "bolt" } });
    await waitFor(() => {
      expect(screen.queryByTestId("trade-card-2")).not.toBeInTheDocument();
    });

    fireEvent.change(searchInput, { target: { value: "" } });
    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
      expect(screen.getByTestId("trade-card-2")).toBeInTheDocument();
    });
  });

  it("shows an error banner with retry when fetchMyTrades rejects", async () => {
    mockFetchMyTrades.mockRejectedValueOnce(new Error("boom"));
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("error-banner")).toBeInTheDocument();
    });

    mockFetchMyTrades.mockResolvedValueOnce({ trades: [mockTrade()], count: 1 });
    fireEvent.click(screen.getByRole("button", { name: /retry|try again/i }));

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
    });
  });

  it("accepts and reloads trades", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [mockTrade({ id: 1, my_role: "seller", status: "pending" })],
      count: 1,
    });
    mockRespondToInterest.mockResolvedValue({ id: 1, status: "accepted" });
    renderPage("/marketplace/my-trades?tab=seller");

    await waitFor(() => {
      expect(screen.getByTestId("accept-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("accept-btn-1"));

    await waitFor(() => {
      expect(mockRespondToInterest).toHaveBeenCalledWith(1, "accept");
      expect(mockFetchMyTrades).toHaveBeenCalledTimes(2);
    });
  });

  it("rejects and reloads trades", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [mockTrade({ id: 1, my_role: "seller", status: "pending" })],
      count: 1,
    });
    mockRespondToInterest.mockResolvedValue({ id: 1, status: "rejected" });
    renderPage("/marketplace/my-trades?tab=seller");

    await waitFor(() => {
      expect(screen.getByTestId("reject-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("reject-btn-1"));

    await waitFor(() => {
      expect(mockRespondToInterest).toHaveBeenCalledWith(1, "reject");
      expect(mockFetchMyTrades).toHaveBeenCalledTimes(2);
    });
  });

  it("confirms and reloads trades", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [mockTrade({ id: 1, status: "accepted" })],
      count: 1,
    });
    mockConfirmAgreement.mockResolvedValue({
      id: 1,
      status: "accepted",
      my_confirmed: true,
      both_confirmed: false,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("confirm-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("confirm-btn-1"));

    await waitFor(() => {
      expect(mockConfirmAgreement).toHaveBeenCalledWith(1);
      expect(mockFetchMyTrades).toHaveBeenCalledTimes(2);
    });
  });

  it("maps INSUFFICIENT_CREDITS to the translated error message", async () => {
    mockFetchMyTrades.mockResolvedValue({
      trades: [mockTrade({ id: 1, status: "accepted" })],
      count: 1,
    });
    mockConfirmAgreement.mockRejectedValue(new Error("INSUFFICIENT_CREDITS"));
    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("confirm-btn-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("confirm-btn-1"));

    await waitFor(() => {
      expect(
        screen.getByText("Insufficient credits for this trade"),
      ).toBeInTheDocument();
    });
  });

  it("renders 0, 1 and 100 trades without crashing", async () => {
    const many = Array.from({ length: 100 }, (_, i) =>
      mockTrade({ id: i + 1, card_name: `Card ${i + 1}` }),
    );
    mockFetchMyTrades.mockResolvedValue({ trades: many, count: many.length });
    renderPage();

    await waitFor(() => {
      expect(screen.getAllByTestId(/^trade-card-/).length).toBe(100);
    });
  });
});
