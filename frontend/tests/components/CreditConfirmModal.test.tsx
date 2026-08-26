import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CreditConfirmModal } from "../../src/components/CreditConfirmModal";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      const map: Record<string, string> = {
        "credits.confirmTitle": "Spend Treasure Tokens?",
        "credits.confirmCost": `This action costs ${opts?.cost ?? ""} token(s)`,
        "credits.confirmBalance": `Your balance: ${opts?.balance ?? ""}`,
        "credits.balanceAfter": `Balance after: ${opts?.balance ?? ""}`,
        "credits.insufficient": "Insufficient tokens!",
        "credits.spend": `Spend ${opts?.cost ?? ""} Token`,
        "credits.cancel": "Cancel",
        "credits.adminBypass": "Admin — no cost",
        "credits.balance": "Treasure Tokens",
        "collection.cardsToScan": `${opts?.count ?? ""} cards to scan`,
        "collection.skippedCards": `${opts?.count ?? ""} cards skipped (recently scanned)`,
      };
      return map[key] ?? key;
    },
  }),
}));

const defaultProps = {
  isOpen: true,
  onConfirm: vi.fn(),
  onCancel: vi.fn(),
  cost: 1,
  balance: 10,
  actionLabel: "Refresh price",
};

describe("TreasureTokenCard (via CreditConfirmModal)", () => {
  it("renders with count overlay", () => {
    render(<CreditConfirmModal {...defaultProps} />);
    const countEl = screen.getByTestId("treasure-count");
    expect(countEl.textContent).toBe("10");
  });
});

describe("CreditConfirmModal", () => {
  it("does not render when isOpen is false", () => {
    render(<CreditConfirmModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByTestId("credit-confirm-modal")).toBeNull();
  });

  it("renders when isOpen is true", () => {
    render(<CreditConfirmModal {...defaultProps} />);
    expect(screen.getByTestId("credit-confirm-modal")).toBeTruthy();
  });

  it("shows cost and balance text", () => {
    render(<CreditConfirmModal {...defaultProps} cost={1} balance={10} />);
    expect(screen.getByTestId("cost-text").textContent).toContain("1");
    expect(screen.getByTestId("balance-text").textContent).toContain("10");
  });

  it("shows balance after text for sufficient balance", () => {
    render(<CreditConfirmModal {...defaultProps} cost={1} balance={10} />);
    const afterEl = screen.getByTestId("balance-after-text");
    expect(afterEl.textContent).toContain("9");
  });

  it("disables confirm button when balance is insufficient (non-admin)", () => {
    render(<CreditConfirmModal {...defaultProps} cost={5} balance={2} />);
    const confirmBtn = screen.getByTestId("modal-confirm-btn");
    expect(confirmBtn).toHaveProperty("disabled", true);
  });

  it("shows insufficient text when balance is insufficient", () => {
    render(<CreditConfirmModal {...defaultProps} cost={5} balance={2} />);
    expect(screen.getByTestId("insufficient-text").textContent).toBe(
      "Insufficient tokens!",
    );
  });

  it("does not show balance-after when insufficient", () => {
    render(<CreditConfirmModal {...defaultProps} cost={5} balance={2} />);
    expect(screen.queryByTestId("balance-after-text")).toBeNull();
  });

  it("enables confirm button for admin regardless of balance", () => {
    render(
      <CreditConfirmModal {...defaultProps} cost={5} balance={0} isAdmin />,
    );
    const confirmBtn = screen.getByTestId("modal-confirm-btn");
    expect(confirmBtn).toHaveProperty("disabled", false);
  });

  it('shows "Admin — no cost" text for admin users', () => {
    render(
      <CreditConfirmModal {...defaultProps} cost={1} balance={0} isAdmin />,
    );
    expect(screen.getByTestId("admin-bypass-text").textContent).toBe(
      "Admin — no cost",
    );
    // Should not show cost/balance/insufficient for admin
    expect(screen.queryByTestId("cost-text")).toBeNull();
    expect(screen.queryByTestId("balance-text")).toBeNull();
    expect(screen.queryByTestId("insufficient-text")).toBeNull();
  });

  it("calls onConfirm when confirm button clicked", () => {
    const onConfirm = vi.fn();
    render(<CreditConfirmModal {...defaultProps} onConfirm={onConfirm} />);
    fireEvent.click(screen.getByTestId("modal-confirm-btn"));
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when cancel button clicked", () => {
    const onCancel = vi.fn();
    render(<CreditConfirmModal {...defaultProps} onCancel={onCancel} />);
    fireEvent.click(screen.getByTestId("modal-cancel-btn"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("calls onCancel when clicking the backdrop", () => {
    const onCancel = vi.fn();
    render(<CreditConfirmModal {...defaultProps} onCancel={onCancel} />);
    fireEvent.click(screen.getByTestId("credit-confirm-modal"));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it("does not call onCancel when clicking inside the modal content", () => {
    const onCancel = vi.fn();
    render(<CreditConfirmModal {...defaultProps} onCancel={onCancel} />);
    fireEvent.click(screen.getByTestId("modal-title"));
    expect(onCancel).not.toHaveBeenCalled();
  });

  it("shows the action label", () => {
    render(
      <CreditConfirmModal {...defaultProps} actionLabel="Refresh price" />,
    );
    expect(screen.getByText("Refresh price")).toBeTruthy();
  });

  it("renders treasure token card with correct balance count", () => {
    render(<CreditConfirmModal {...defaultProps} balance={42} />);
    expect(screen.getByTestId("treasure-count").textContent).toBe("42");
  });

  it("shows the title", () => {
    render(<CreditConfirmModal {...defaultProps} />);
    expect(screen.getByTestId("modal-title").textContent).toBe(
      "Spend Treasure Tokens?",
    );
  });

  it("displays card count when provided", () => {
    render(<CreditConfirmModal {...defaultProps} cardCount={42} />);
    const el = screen.getByTestId("card-count-text");
    expect(el.textContent).toContain("42");
    expect(el.textContent).toContain("cards to scan");
  });

  it("does not display card count when not provided", () => {
    render(<CreditConfirmModal {...defaultProps} />);
    expect(screen.queryByTestId("card-count-text")).toBeNull();
  });

  it("displays skipped count when greater than 0", () => {
    render(<CreditConfirmModal {...defaultProps} skippedCount={15} />);
    const el = screen.getByTestId("skipped-count-text");
    expect(el.textContent).toContain("15");
    expect(el.textContent).toContain("skipped");
  });

  it("does not display skipped count when 0", () => {
    render(<CreditConfirmModal {...defaultProps} skippedCount={0} />);
    expect(screen.queryByTestId("skipped-count-text")).toBeNull();
  });

  it("does not display skipped count when not provided", () => {
    render(<CreditConfirmModal {...defaultProps} />);
    expect(screen.queryByTestId("skipped-count-text")).toBeNull();
  });

  it("renders children (e.g. MaxAgeDaysSelect) inside modal", () => {
    render(
      <CreditConfirmModal {...defaultProps}>
        <div data-testid="child-slot">Hello</div>
      </CreditConfirmModal>,
    );
    expect(screen.getByTestId("child-slot")).toBeTruthy();
  });

  it("shows dynamic cost from props, not hardcoded", () => {
    render(<CreditConfirmModal {...defaultProps} cost={12} balance={50} />);
    expect(screen.getByTestId("cost-text").textContent).toContain("12");
    const confirmBtn = screen.getByTestId("modal-confirm-btn");
    expect(confirmBtn.textContent).toContain("12");
  });
});
