import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TradeInterestModal } from "../../src/components/TradeInterestModal";
import type { MarketplaceListing } from "../../src/api/marketplace";

const mockListing: MarketplaceListing = {
  share_code: "abc123def456gh",
  entry_id: 1,
  card_name_en: "Lightning Bolt",
  card_name_pt: "Relampago",
  set_code: "lea",
  collector_number: "161",
  rarity: "C",
  quantity: 1,
  latest_price: 25.5,
  estimated_fee: 3,
};

function renderModal(props?: Partial<{ onSubmit: (msg?: string) => Promise<void>; onCancel: () => void }>) {
  const onSubmit = props?.onSubmit ?? vi.fn().mockResolvedValue(undefined);
  const onCancel = props?.onCancel ?? vi.fn();

  return {
    ...render(
      <MemoryRouter>
        <TradeInterestModal
          listing={mockListing}
          onSubmit={onSubmit}
          onCancel={onCancel}
        />
      </MemoryRouter>,
    ),
    onSubmit,
    onCancel,
  };
}

describe("TradeInterestModal", () => {
  it("renders modal with card name", () => {
    renderModal();
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
  });

  it("shows fee preview", () => {
    renderModal();
    expect(screen.getByTestId("fee-preview")).toHaveTextContent("Fee: 3 tokens");
  });

  it("shows set code and number", () => {
    renderModal();
    expect(screen.getByText("LEA #161")).toBeInTheDocument();
  });

  it("has a message textarea", () => {
    renderModal();
    expect(screen.getByTestId("interest-message")).toBeInTheDocument();
  });

  it("submits with message", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderModal({ onSubmit });

    fireEvent.change(screen.getByTestId("interest-message"), {
      target: { value: "I want this card!" },
    });
    fireEvent.click(screen.getByTestId("interest-submit-btn"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith("I want this card!");
    });
  });

  it("submits without message", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    renderModal({ onSubmit });

    fireEvent.click(screen.getByTestId("interest-submit-btn"));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(undefined);
    });
  });

  it("calls onCancel when cancel button clicked", () => {
    const onCancel = vi.fn();
    renderModal({ onCancel });

    fireEvent.click(screen.getByTestId("interest-cancel-btn"));
    expect(onCancel).toHaveBeenCalled();
  });

  it("shows error on submission failure", async () => {
    const onSubmit = vi.fn().mockRejectedValue(new Error("Cannot trade with yourself"));
    renderModal({ onSubmit });

    fireEvent.click(screen.getByTestId("interest-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("interest-error")).toHaveTextContent("Cannot trade with yourself");
    });
  });
});
