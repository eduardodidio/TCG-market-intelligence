import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MyTrades } from "../../src/pages/MyTrades";

function mockTrade(overrides: Record<string, unknown> = {}) {
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

function mockFetch(trades = [mockTrade()]) {
  return vi.fn().mockImplementation(() => {
    return Promise.resolve({
      ok: true,
      json: () => Promise.resolve({ trades, count: trades.length }),
    });
  });
}

function renderPage(fetchImpl?: ReturnType<typeof vi.fn>) {
  if (fetchImpl) vi.stubGlobal("fetch", fetchImpl);
  return render(
    <MemoryRouter>
      <MyTrades />
    </MemoryRouter>,
  );
}

describe("MyTrades", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders buyer/seller tabs", async () => {
    renderPage(mockFetch());
    await waitFor(() => {
      expect(screen.getByTestId("tab-buyer")).toBeInTheDocument();
      expect(screen.getByTestId("tab-seller")).toBeInTheDocument();
    });
  });

  it("shows buyer tab count", async () => {
    renderPage(mockFetch([mockTrade({ my_role: "buyer" })]));
    await waitFor(() => {
      expect(screen.getByTestId("tab-buyer")).toHaveTextContent("As Buyer (1)");
    });
  });

  it("shows seller tab count", async () => {
    renderPage(mockFetch([mockTrade({ my_role: "seller", id: 2 })]));
    await waitFor(() => {
      expect(screen.getByTestId("tab-seller")).toHaveTextContent("As Seller (1)");
    });
  });

  it("renders trade card in buyer tab", async () => {
    renderPage(mockFetch([mockTrade({ id: 1, my_role: "buyer" })]));
    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
    });
  });

  it("switches to seller tab", async () => {
    const trades = [
      mockTrade({ id: 1, my_role: "buyer" }),
      mockTrade({ id: 2, my_role: "seller", card_name: "Dark Ritual" }),
    ];
    renderPage(mockFetch(trades));

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-1")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("tab-seller"));

    await waitFor(() => {
      expect(screen.getByTestId("trade-card-2")).toBeInTheDocument();
      expect(screen.queryByTestId("trade-card-1")).not.toBeInTheDocument();
    });
  });

  it("shows accept/reject for seller pending trades", async () => {
    renderPage(
      mockFetch([mockTrade({ id: 1, my_role: "seller", status: "pending" })]),
    );

    fireEvent.click(await screen.findByTestId("tab-seller"));

    await waitFor(() => {
      expect(screen.getByTestId("accept-btn-1")).toBeInTheDocument();
      expect(screen.getByTestId("reject-btn-1")).toBeInTheDocument();
    });
  });

  it("shows confirm button for accepted trades", async () => {
    renderPage(
      mockFetch([mockTrade({ id: 1, my_role: "buyer", status: "accepted" })]),
    );

    await waitFor(() => {
      expect(screen.getByTestId("confirm-btn-1")).toBeInTheDocument();
    });
  });

  it("shows completed trade with email", async () => {
    renderPage(
      mockFetch([
        mockTrade({
          id: 1,
          my_role: "buyer",
          status: "completed",
          counterparty_email: "seller@test.com",
        }),
      ]),
    );

    await waitFor(() => {
      expect(screen.getByTestId("trade-completed-1")).toBeInTheDocument();
      expect(screen.getByText("Contact: seller@test.com")).toBeInTheDocument();
    });
  });

  it("shows status badges", async () => {
    renderPage(
      mockFetch([mockTrade({ id: 1, status: "pending" })]),
    );

    await waitFor(() => {
      expect(screen.getByTestId("trade-status-1")).toHaveTextContent("pending");
    });
  });

  it("shows pending confirmation text for accepted", async () => {
    renderPage(
      mockFetch([mockTrade({ id: 1, status: "accepted" })]),
    );

    await waitFor(() => {
      expect(screen.getByTestId("trade-pending-1")).toHaveTextContent("Waiting for other party");
    });
  });

  it("shows empty state when no trades", async () => {
    renderPage(mockFetch([]));

    await waitFor(() => {
      expect(screen.getByText("No cards available for trade")).toBeInTheDocument();
    });
  });

  it("renders breadcrumb", async () => {
    renderPage(mockFetch());
    expect(screen.getByText("Card Marketplace")).toBeInTheDocument();
  });
});
