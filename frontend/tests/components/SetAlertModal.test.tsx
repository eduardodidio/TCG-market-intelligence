import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SetAlertModal } from "../../src/components/SetAlertModal";

// Mock the alerts API
vi.mock("../../src/api/alerts", () => ({
  createAlert: vi.fn(),
  deleteAlert: vi.fn(),
  fetchAlerts: vi.fn(),
}));

import { createAlert, fetchAlerts } from "../../src/api/alerts";

const mockCreateAlert = vi.mocked(createAlert);
const mockFetchAlerts = vi.mocked(fetchAlerts);

function renderModal(props?: Partial<{ cardId: number; cardName: string; onClose: () => void }>) {
  const onClose = props?.onClose ?? vi.fn();
  return render(
    <MemoryRouter>
      <SetAlertModal
        cardId={props?.cardId ?? 42}
        cardName={props?.cardName ?? "Lightning Bolt"}
        onClose={onClose}
      />
    </MemoryRouter>,
  );
}

describe("SetAlertModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetchAlerts.mockResolvedValue({
      data: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "" },
      errors: [],
    });
  });

  it("renders modal with title", () => {
    renderModal();
    expect(screen.getByTestId("set-alert-modal")).toBeDefined();
    expect(screen.getByText("Set Price Alert")).toBeDefined();
  });

  it("renders direction buttons", () => {
    renderModal();
    expect(screen.getByTestId("direction-below")).toBeDefined();
    expect(screen.getByTestId("direction-above")).toBeDefined();
  });

  it("renders price input", () => {
    renderModal();
    expect(screen.getByTestId("target-price-input")).toBeDefined();
  });

  it("calls onClose when close button clicked", () => {
    const onClose = vi.fn();
    renderModal({ onClose });
    fireEvent.click(screen.getByTestId("close-modal"));
    expect(onClose).toHaveBeenCalled();
  });

  it("calls onClose when overlay clicked", () => {
    const onClose = vi.fn();
    renderModal({ onClose });
    fireEvent.click(screen.getByTestId("set-alert-modal-overlay"));
    expect(onClose).toHaveBeenCalled();
  });

  it("submits alert successfully", async () => {
    mockCreateAlert.mockResolvedValue({
      data: {
        id: 1,
        card_id: 42,
        card_name: "Lightning Bolt",
        target_price: 10.5,
        direction: "below" as const,
        is_active: true,
        triggered_at: null,
        created_at: new Date().toISOString(),
      },
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [],
    });

    renderModal();

    const input = screen.getByTestId("target-price-input");
    fireEvent.change(input, { target: { value: "10.50" } });
    fireEvent.click(screen.getByTestId("submit-alert"));

    await waitFor(() => {
      expect(mockCreateAlert).toHaveBeenCalledWith({
        card_id: 42,
        target_price: 10.5,
        direction: "below",
      });
    });

    await waitFor(() => {
      expect(screen.getByTestId("alert-success")).toBeDefined();
    });
  });

  it("shows error when API returns error", async () => {
    mockCreateAlert.mockResolvedValue({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "" },
      errors: [{ code: "HTTP_409", message: "Maximum 50 active alerts allowed" }],
    });

    renderModal();

    const input = screen.getByTestId("target-price-input");
    fireEvent.change(input, { target: { value: "10.00" } });
    fireEvent.click(screen.getByTestId("submit-alert"));

    await waitFor(() => {
      expect(screen.getByTestId("alert-error")).toBeDefined();
    });
  });

  it("can switch direction to above", () => {
    renderModal();
    fireEvent.click(screen.getByTestId("direction-above"));

    // Direction-above should have the active style
    const btn = screen.getByTestId("direction-above");
    expect(btn.className).toContain("bg-red-600");
  });

  it("shows existing alerts for the card", async () => {
    mockFetchAlerts.mockResolvedValue({
      data: [
        {
          id: 1,
          card_id: 42,
          card_name: "Lightning Bolt",
          target_price: 5.0,
          direction: "below" as const,
          is_active: true,
          triggered_at: null,
          created_at: new Date().toISOString(),
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "" },
      errors: [],
    });

    renderModal();

    await waitFor(() => {
      expect(screen.getByText("Active alerts for this card")).toBeDefined();
    });

    expect(screen.getByTestId("existing-alert-item")).toBeDefined();
  });
});
