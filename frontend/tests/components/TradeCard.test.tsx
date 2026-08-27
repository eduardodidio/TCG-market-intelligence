import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TradeCard } from "../../src/components/TradeCard";
import type { TradeDetail } from "../../src/api/marketplace";

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

function renderCard(trade: TradeDetail, handlers?: { onAccept?: (id: number) => void; onReject?: (id: number) => void; onConfirm?: (id: number) => void }) {
  return render(
    <MemoryRouter>
      <TradeCard trade={trade} {...handlers} />
    </MemoryRouter>,
  );
}

describe("TradeCard", () => {
  it("renders card name", () => {
    renderCard(mockTrade());
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
  });

  it("renders status badge", () => {
    renderCard(mockTrade({ status: "pending" }));
    expect(screen.getByTestId("trade-status-1")).toHaveTextContent("pending");
  });

  it("renders status badge for all states", () => {
    for (const status of ["pending", "accepted", "rejected", "completed", "cancelled"]) {
      const { unmount } = renderCard(mockTrade({ status }));
      expect(screen.getByTestId("trade-status-1")).toHaveTextContent(status);
      unmount();
    }
  });

  it("shows accept/reject for seller with pending trade", () => {
    renderCard(
      mockTrade({ my_role: "seller", status: "pending" }),
      { onAccept: vi.fn(), onReject: vi.fn() },
    );
    expect(screen.getByTestId("accept-btn-1")).toBeInTheDocument();
    expect(screen.getByTestId("reject-btn-1")).toBeInTheDocument();
  });

  it("does not show accept/reject for buyer", () => {
    renderCard(mockTrade({ my_role: "buyer", status: "pending" }));
    expect(screen.queryByTestId("accept-btn-1")).not.toBeInTheDocument();
  });

  it("shows confirm button for accepted trade", () => {
    renderCard(
      mockTrade({ status: "accepted" }),
      { onConfirm: vi.fn() },
    );
    expect(screen.getByTestId("confirm-btn-1")).toBeInTheDocument();
  });

  it("shows completed view with email", () => {
    renderCard(
      mockTrade({
        status: "completed",
        counterparty_email: "seller@test.com",
      }),
    );
    expect(screen.getByTestId("trade-completed-1")).toBeInTheDocument();
    expect(screen.getByText("Trade Completed!")).toBeInTheDocument();
    expect(screen.getByText("Contact: seller@test.com")).toBeInTheDocument();
  });

  it("shows fee info", () => {
    renderCard(mockTrade({ estimated_fee: 5 }));
    expect(screen.getByText("Fee: 5 tokens")).toBeInTheDocument();
  });

  it("shows role label", () => {
    renderCard(mockTrade({ my_role: "buyer" }));
    expect(screen.getByText("As Buyer")).toBeInTheDocument();
  });

  it("shows pending confirmation text", () => {
    renderCard(mockTrade({ status: "accepted" }));
    expect(screen.getByTestId("trade-pending-1")).toHaveTextContent("Waiting for other party");
  });

  it("calls onAccept when accept clicked", () => {
    const onAccept = vi.fn();
    renderCard(
      mockTrade({ my_role: "seller", status: "pending" }),
      { onAccept },
    );
    fireEvent.click(screen.getByTestId("accept-btn-1"));
    expect(onAccept).toHaveBeenCalledWith(1);
  });

  it("calls onReject when reject clicked", () => {
    const onReject = vi.fn();
    renderCard(
      mockTrade({ my_role: "seller", status: "pending" }),
      { onReject },
    );
    fireEvent.click(screen.getByTestId("reject-btn-1"));
    expect(onReject).toHaveBeenCalledWith(1);
  });

  it("calls onConfirm when confirm clicked", () => {
    const onConfirm = vi.fn();
    renderCard(
      mockTrade({ status: "accepted" }),
      { onConfirm },
    );
    fireEvent.click(screen.getByTestId("confirm-btn-1"));
    expect(onConfirm).toHaveBeenCalledWith(1);
  });
});
