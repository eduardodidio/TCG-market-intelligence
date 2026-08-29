import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { Evaluations } from "../../src/pages/Evaluations";
import type { ApiResponse } from "../../src/types/api";
import type { EvalEntry } from "../../src/api/evaluations";

function envelope<T>(data: T): ApiResponse<T> {
  return {
    data,
    meta: { cursor: null, total: null, offset: null, request_id: "test" },
    errors: [],
  };
}

const mockEntries: EvalEntry[] = [
  {
    id: 1,
    card_name: "Lightning Bolt",
    set_code: "m21",
    collector_number: "152",
    liga_url: null,
    price_at_add: 5.5,
    card_id: null,
    image_url: "https://api.scryfall.com/cards/m21/152?format=image&version=normal",
    created_at: "2026-08-29T10:00:00",
  },
  {
    id: 2,
    card_name: "Counterspell",
    set_code: null,
    collector_number: null,
    liga_url: null,
    price_at_add: null,
    card_id: null,
    image_url: null,
    created_at: "2026-08-29T11:00:00",
  },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <Evaluations />
    </MemoryRouter>,
  );
}

describe("Evaluations page", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders empty state when no entries", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(envelope([])),
    } as Response);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("eval-empty")).toBeInTheDocument();
    });
  });

  it("renders table with entries", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(envelope(mockEntries)),
    } as Response);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("eval-table")).toBeInTheDocument();
    });

    const rows = screen.getAllByTestId("eval-row");
    expect(rows).toHaveLength(2);
    expect(screen.getByText("Lightning Bolt")).toBeInTheDocument();
    expect(screen.getByText("Counterspell")).toBeInTheDocument();
  });

  it("renders title", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(envelope([])),
    } as Response);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("evaluations-title")).toBeInTheDocument();
    });
  });

  it("remove button removes entry from list", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(envelope(mockEntries)),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({}),
      } as Response);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("eval-table")).toBeInTheDocument();
    });

    const removeButtons = screen.getAllByTestId("remove-btn");
    fireEvent.click(removeButtons[0]);

    await waitFor(() => {
      const rows = screen.getAllByTestId("eval-row");
      expect(rows).toHaveLength(1);
    });
  });

  it("promote button removes entry from list", async () => {
    vi.spyOn(globalThis, "fetch")
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(envelope(mockEntries)),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve(
            envelope({ collection_entry_id: 10, card_name: "Lightning Bolt" }),
          ),
      } as Response);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("eval-table")).toBeInTheDocument();
    });

    const promoteButtons = screen.getAllByTestId("promote-btn");
    fireEvent.click(promoteButtons[0]);

    await waitFor(() => {
      const rows = screen.getAllByTestId("eval-row");
      expect(rows).toHaveLength(1);
    });
  });

  it("shows error when fetch fails", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: () => Promise.resolve({ detail: "Server error" }),
    } as Response);

    renderPage();

    await waitFor(() => {
      expect(screen.getByTestId("eval-error")).toBeInTheDocument();
    });
  });
});
