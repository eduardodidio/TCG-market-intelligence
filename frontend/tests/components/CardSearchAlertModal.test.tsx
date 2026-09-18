import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { CardSearchAlertModal } from "../../src/components/CardSearchAlertModal";

// Mock cards API
vi.mock("../../src/api/cards", () => ({
  fetchCards: vi.fn(),
}));

// Mock alerts API (used by SetAlertModal)
vi.mock("../../src/api/alerts", () => ({
  fetchAlerts: vi.fn().mockResolvedValue({
    data: [],
    meta: { cursor: null, total: 0, offset: null, request_id: "" },
    errors: [],
  }),
  createAlert: vi.fn().mockResolvedValue({
    data: { id: 1, card_id: 42, card_name: "Test", target_price: 10, direction: "below", is_active: true, triggered_at: null, created_at: new Date().toISOString(), current_price: null },
    meta: { cursor: null, total: null, offset: null, request_id: "" },
    errors: [],
  }),
  deleteAlert: vi.fn(),
}));

import { fetchCards } from "../../src/api/cards";

const mockFetchCards = vi.mocked(fetchCards);

const emptyMeta = { cursor: null, total: 0, offset: null, request_id: "" };

function renderModal(props?: Partial<{ onClose: () => void; onAlertCreated: () => void }>) {
  const onClose = props?.onClose ?? vi.fn();
  const onAlertCreated = props?.onAlertCreated ?? vi.fn();
  return render(
    <MemoryRouter>
      <CardSearchAlertModal onClose={onClose} onAlertCreated={onAlertCreated} />
    </MemoryRouter>,
  );
}

describe("CardSearchAlertModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders search input on open", () => {
    renderModal();
    expect(screen.getByTestId("card-search-input")).toBeDefined();
  });

  it("typing triggers debounced search", async () => {
    mockFetchCards.mockResolvedValue({
      data: [
        { id: 42, game: "magic", name_en: "Lightning Bolt", name_pt: null, set_code: "2ed", collector_number: "157", latest_price: 5.0 },
      ],
      meta: emptyMeta,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("card-search-input");
    fireEvent.change(input, { target: { value: "Lightning" } });

    // Advance debounce timer
    vi.advanceTimersByTime(350);

    await waitFor(() => {
      expect(mockFetchCards).toHaveBeenCalledWith({ q: "Lightning", limit: "20" });
    });

    await waitFor(() => {
      expect(screen.getByTestId("search-result-item")).toBeDefined();
      expect(screen.getByText("Lightning Bolt")).toBeDefined();
    });
  });

  it("shows no results message when search returns empty", async () => {
    mockFetchCards.mockResolvedValue({
      data: [],
      meta: emptyMeta,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("card-search-input");
    fireEvent.change(input, { target: { value: "zzzzz" } });

    vi.advanceTimersByTime(350);

    await waitFor(() => {
      expect(screen.getByTestId("search-no-results")).toBeDefined();
    });
  });

  it("clicking a result shows the configure step", async () => {
    mockFetchCards.mockResolvedValue({
      data: [
        { id: 42, game: "magic", name_en: "Lightning Bolt", name_pt: null, set_code: "2ed", collector_number: "157", latest_price: 5.0 },
      ],
      meta: emptyMeta,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("card-search-input");
    fireEvent.change(input, { target: { value: "Lightning" } });
    vi.advanceTimersByTime(350);

    await waitFor(() => {
      expect(screen.getByTestId("search-result-item")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("search-result-item"));

    await waitFor(() => {
      expect(screen.getByTestId("back-to-search")).toBeDefined();
      expect(screen.getByTestId("set-alert-modal")).toBeDefined();
    });
  });

  it("back button returns to search step", async () => {
    mockFetchCards.mockResolvedValue({
      data: [
        { id: 42, game: "magic", name_en: "Lightning Bolt", name_pt: null, set_code: "2ed", collector_number: "157", latest_price: 5.0 },
      ],
      meta: emptyMeta,
      errors: [],
    });

    renderModal();
    const input = screen.getByTestId("card-search-input");
    fireEvent.change(input, { target: { value: "Lightning" } });
    vi.advanceTimersByTime(350);

    await waitFor(() => {
      expect(screen.getByTestId("search-result-item")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("search-result-item"));

    await waitFor(() => {
      expect(screen.getByTestId("back-to-search")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("back-to-search"));

    await waitFor(() => {
      expect(screen.getByTestId("card-search-input")).toBeDefined();
    });
  });

  it("calls onClose on escape key", () => {
    const onClose = vi.fn();
    renderModal({ onClose });
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });
});
