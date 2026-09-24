import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { BanCardDetailModal } from "../../src/components/BanCardDetailModal";

vi.mock("../../src/api/banlist", () => ({
  fetchCardLegalities: vi.fn(),
  fetchCardBanHistory: vi.fn(),
}));

import { fetchCardLegalities, fetchCardBanHistory } from "../../src/api/banlist";

function mockApiResponse(data: unknown) {
  return Promise.resolve({
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "r1" },
    errors: [],
  });
}

const BASE_ENTRY = {
  card_id: 42,
  name_en: "Lightning Bolt",
  name_pt: null,
  set_code: "lea",
  collector_number: "161",
  format: "commander",
  status: "banned",
  effective_date: "2026-01-01",
  image_url: null,
};

const LEGALITIES = [
  { format: "commander", status: "banned", effective_date: "2026-01-01" },
  { format: "legacy", status: "legal", effective_date: null },
];

const HISTORY = [
  { id: 1, format: "commander", old_status: "legal", new_status: "banned", changed_at: "2026-01-01T00:00:00Z", source: "sync" },
  { id: 2, format: "commander", old_status: null, new_status: "legal", changed_at: "2020-01-01T00:00:00Z", source: "scryfall_baseline" },
  { id: 3, format: "legacy", old_status: "legal", new_status: "restricted", changed_at: "2025-06-01T00:00:00Z", source: "sync" },
];

function renderModal(entry: unknown, onClose = vi.fn()) {
  return render(
    <MemoryRouter>
      <BanCardDetailModal entry={entry as never} onClose={onClose} />
    </MemoryRouter>,
  );
}

describe("BanCardDetailModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders nothing when entry is null", () => {
    const { container } = renderModal(null);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows name, set/#, status badge, legalities and grouped history", async () => {
    (fetchCardLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(LEGALITIES),
    );
    (fetchCardBanHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(HISTORY),
    );

    renderModal(BASE_ENTRY);

    expect(screen.getByTestId("ban-card-modal")).toBeInTheDocument();
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    expect(screen.getByText("LEA #161")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId("ban-card-legalities")).toBeInTheDocument();
    });
    expect(screen.getAllByTestId(/legality-badge/).length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(
        screen.getByTestId("ban-card-history-format-commander"),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("ban-card-history-format-legacy")).toBeInTheDocument();
    expect(screen.getByText(/tracking started|monitoramento começou/i)).toBeInTheDocument();
  });

  it("shows owned badge with quantity when owned_quantity=2", async () => {
    (fetchCardLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(LEGALITIES),
    );
    (fetchCardBanHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(HISTORY),
    );

    renderModal({ ...BASE_ENTRY, owned_quantity: 2 });

    await waitFor(() => {
      expect(screen.getByTestId("ban-card-owned-badge")).toBeInTheDocument();
    });
    expect(screen.getByTestId("ban-card-owned-badge").textContent).toContain("2");
  });

  it("shows empty history and unavailable legalities messages", async () => {
    (fetchCardLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse([]),
    );
    (fetchCardBanHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse([]),
    );

    renderModal(BASE_ENTRY);

    await waitFor(() => {
      expect(screen.getByTestId("ban-card-history-empty")).toBeInTheDocument();
    });
    expect(screen.getByText(/not available/i)).toBeInTheDocument();
  });

  it("shows history error while legalities still render", async () => {
    (fetchCardLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(LEGALITIES),
    );
    (fetchCardBanHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      Promise.reject(new Error("network error")),
    );

    renderModal(BASE_ENTRY);

    await waitFor(() => {
      expect(screen.getAllByTestId(/legality-badge/).length).toBeGreaterThan(0);
    });
    await waitFor(() => {
      expect(screen.getByText(/network error/i)).toBeInTheDocument();
    });
  });

  it("renders 20+ formats without crashing", async () => {
    const manyLegalities = Array.from({ length: 25 }, (_, i) => ({
      format: `format${i}`,
      status: "legal",
      effective_date: null,
    }));
    (fetchCardLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(manyLegalities),
    );
    (fetchCardBanHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse([]),
    );

    renderModal(BASE_ENTRY);

    await waitFor(() => {
      const container = screen.getByTestId("ban-card-legalities");
      expect(container.querySelectorAll('[data-testid^="legality-badge-"]').length).toBe(25);
    });
  });

  it("calls onClose on Esc, backdrop click, and close button; not on inner click", async () => {
    (fetchCardLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(LEGALITIES),
    );
    (fetchCardBanHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(HISTORY),
    );

    const onClose = vi.fn();
    renderModal(BASE_ENTRY, onClose);

    fireEvent.click(screen.getByTestId("ban-card-modal"));
    expect(onClose).toHaveBeenCalledTimes(1);

    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(2);

    onClose.mockClear();
    fireEvent.click(screen.getByText("Lightning Bolt"));
    expect(onClose).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId("ban-card-modal-close"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("moves focus to the close button on open and is accessible", () => {
    (fetchCardLegalities as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(LEGALITIES),
    );
    (fetchCardBanHistory as ReturnType<typeof vi.fn>).mockReturnValue(
      mockApiResponse(HISTORY),
    );

    renderModal(BASE_ENTRY);

    const dialog = screen.getByRole("dialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAttribute("aria-labelledby");
    expect(screen.getByTestId("ban-card-modal-close")).toHaveFocus();
  });
});
