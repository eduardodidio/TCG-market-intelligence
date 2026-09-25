import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TradeCard } from "../TradeCard";
import type { TradeDetail } from "../../api/marketplace";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      opts ? `${key}:${JSON.stringify(opts)}` : key,
  }),
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

function tradeFixture(overrides: Partial<TradeDetail> = {}): TradeDetail {
  return {
    id: 1,
    card_name: "Sol Ring",
    set_code: "cmr",
    collector_number: "123",
    counterparty_share_code: "abcdef1234567890",
    status: "pending",
    estimated_fee: 5,
    my_role: "seller",
    counterparty_email: null,
    created_at: "2024-01-01T00:00:00Z",
    ...overrides,
  };
}

describe("TradeCard", () => {
  it("renders as a tile with aspect-[5/7] image area and top-left status badge", () => {
    const trade = tradeFixture();
    render(<TradeCard trade={trade} />);

    expect(screen.getByTestId(`trade-card-${trade.id}`)).toBeInTheDocument();
    const status = screen.getByTestId(`trade-status-${trade.id}`);
    expect(status).toBeInTheDocument();
    expect(status.className).toContain("absolute");
    expect(status.className).toContain("top-2");
    expect(status.className).toContain("left-2");
    expect(status.parentElement?.className).toContain("aspect-[5/7]");
  });

  it("shows accept/reject for seller + pending, and calls onAccept(id)", () => {
    const trade = tradeFixture({ my_role: "seller", status: "pending" });
    const onAccept = vi.fn();
    render(<TradeCard trade={trade} onAccept={onAccept} onReject={vi.fn()} />);

    const acceptBtn = screen.getByTestId(`accept-btn-${trade.id}`);
    expect(acceptBtn).toBeInTheDocument();
    expect(screen.getByTestId(`reject-btn-${trade.id}`)).toBeInTheDocument();

    fireEvent.click(acceptBtn);
    expect(onAccept).toHaveBeenCalledWith(trade.id);
  });

  it("does not show accept/reject for buyer + pending", () => {
    const trade = tradeFixture({ my_role: "buyer", status: "pending" });
    render(<TradeCard trade={trade} />);

    expect(screen.queryByTestId(`accept-btn-${trade.id}`)).not.toBeInTheDocument();
    expect(screen.queryByTestId(`reject-btn-${trade.id}`)).not.toBeInTheDocument();
  });

  it("shows confirm button and pending message for accepted status", () => {
    const trade = tradeFixture({ status: "accepted" });
    const onConfirm = vi.fn();
    render(<TradeCard trade={trade} onConfirm={onConfirm} />);

    const confirmBtn = screen.getByTestId(`confirm-btn-${trade.id}`);
    expect(confirmBtn).toBeInTheDocument();
    expect(screen.getByTestId(`trade-pending-${trade.id}`)).toBeInTheDocument();

    fireEvent.click(confirmBtn);
    expect(onConfirm).toHaveBeenCalledWith(trade.id);
  });

  it("shows the email box for completed status", () => {
    const trade = tradeFixture({ status: "completed", counterparty_email: "seller@example.com" });
    render(<TradeCard trade={trade} />);

    expect(screen.getByTestId(`trade-completed-${trade.id}`)).toBeInTheDocument();
    expect(screen.queryByTestId(`accept-btn-${trade.id}`)).not.toBeInTheDocument();
    expect(screen.queryByTestId(`confirm-btn-${trade.id}`)).not.toBeInTheDocument();
  });

  it("falls back to the pending style for an unknown status", () => {
    const trade = tradeFixture({ status: "weird-status" as TradeDetail["status"] });
    render(<TradeCard trade={trade} />);

    const status = screen.getByTestId(`trade-status-${trade.id}`);
    expect(status.className).toContain("bg-yellow-600/20");
  });

  it("falls back to the by-name image when the primary image errors", () => {
    const trade = tradeFixture();
    render(<TradeCard trade={trade} />);

    const img = screen.getByTestId("card-image");
    expect(img.getAttribute("src")).toContain(`cards/${trade.set_code}/${trade.collector_number}`);
    fireEvent.error(img);
    expect(screen.getByTestId("card-image").getAttribute("src")).toContain(
      "cards/named?exact=",
    );
  });

  it("renders without the counterparty code when missing", () => {
    const trade = tradeFixture({ counterparty_share_code: null });
    render(<TradeCard trade={trade} />);

    expect(screen.queryByText(/\.\.\.$/)).not.toBeInTheDocument();
  });

  it("does nothing when a handler is undefined and the button is clicked", () => {
    const trade = tradeFixture({ my_role: "seller", status: "pending" });
    expect(() => {
      render(<TradeCard trade={trade} />);
      fireEvent.click(screen.getByTestId(`accept-btn-${trade.id}`));
    }).not.toThrow();
  });

  it("hides the counterparty code and fee line when compact", () => {
    const trade = tradeFixture({ counterparty_share_code: "abcdef1234567890" });
    const { rerender } = render(<TradeCard trade={trade} compact={false} />);
    expect(screen.getByText(/abcdef12\.\.\./)).toBeInTheDocument();
    expect(screen.getByText(/marketplace\.estimatedFee/)).toBeInTheDocument();

    rerender(<TradeCard trade={trade} compact />);
    expect(screen.queryByText(/abcdef12\.\.\./)).not.toBeInTheDocument();
    expect(screen.queryByText(/marketplace\.estimatedFee/)).not.toBeInTheDocument();
    // Actions and status stay visible in compact mode.
    expect(screen.getByTestId(`trade-status-${trade.id}`)).toBeInTheDocument();
    expect(screen.getByTestId(`accept-btn-${trade.id}`)).toBeInTheDocument();
  });

  it("truncates a long card name and exposes it via the title attribute", () => {
    const longName = "A Very Extremely Long Card Name That Should Truncate In The Tile";
    const trade = tradeFixture({ card_name: longName });
    render(<TradeCard trade={trade} />);

    const heading = screen.getByTitle(longName);
    expect(heading.className).toContain("truncate");
  });
});
