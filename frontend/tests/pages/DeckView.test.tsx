import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { DeckView } from "../../src/pages/DeckView";

function renderDeckView(deckId = "1") {
  return render(
    <MemoryRouter initialEntries={[`/decks/${deckId}`]}>
      <Routes>
        <Route path="/decks/:id" element={<DeckView />} />
        <Route path="/decks" element={<div data-testid="decks-page">Redirected</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

const MOCK_DECK_DETAIL = {
  data: {
    id: 1,
    name: "Mono Red Burn",
    description: "Fast aggro deck",
    cards: [
      {
        id: 10,
        name_en: "Lightning Bolt",
        set_code: "lea",
        collector_number: "161",
        quantity: 4,
        card_id: 42,
        in_collection: true,
        owned_quantity: 3,
        collection_entry_id: 100,
        image_url: "https://api.scryfall.com/cards/lea/161?format=image&version=normal",
        latest_price: 5.0,
      },
      {
        id: 11,
        name_en: "Force of Will",
        set_code: "all",
        collector_number: "28",
        quantity: 2,
        card_id: null,
        in_collection: false,
        owned_quantity: 0,
        collection_entry_id: null,
        image_url: "https://api.scryfall.com/cards/all/28?format=image&version=normal",
        latest_price: null,
      },
    ],
    total_cards: 6,
    unique_cards: 2,
    owned_cards: 1,
    ownership_pct: 50.0,
    created_at: "2026-08-21T12:00:00",
    updated_at: "2026-08-21T12:00:00",
  },
  meta: { cursor: null, total: null, offset: null, request_id: "r1" },
  errors: [],
};

describe("DeckView page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchSuccess(data: unknown = MOCK_DECK_DETAIL) {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(data),
    }) as unknown as typeof fetch;
  }

  it("renders deck header", async () => {
    mockFetchSuccess();
    renderDeckView();

    await waitFor(() => {
      expect(screen.getByTestId("deck-title")).toBeDefined();
    });

    expect(screen.getByText("Mono Red Burn")).toBeDefined();
    expect(screen.getByText("Fast aggro deck")).toBeDefined();
  });

  it("renders deck stats", async () => {
    mockFetchSuccess();
    renderDeckView();

    await waitFor(() => {
      expect(screen.getByTestId("deck-total-cards")).toBeDefined();
    });

    expect(screen.getByTestId("deck-total-cards").textContent).toBe("6 cards");
    expect(screen.getByTestId("deck-unique-cards").textContent).toBe("2 unique");
    expect(screen.getByTestId("deck-owned-cards").textContent).toBe("1 owned");
    expect(screen.getByTestId("deck-ownership-pct").textContent).toBe("50% complete");
  });

  it("renders card tiles", async () => {
    mockFetchSuccess();
    renderDeckView();

    await waitFor(() => {
      expect(screen.getByTestId("deck-card-tile-10")).toBeDefined();
    });

    expect(screen.getByTestId("deck-card-tile-11")).toBeDefined();
  });

  it("shows not-owned overlay for cards not in collection", async () => {
    mockFetchSuccess();
    renderDeckView();

    await waitFor(() => {
      expect(screen.getByTestId("deck-card-tile-11")).toBeDefined();
    });

    expect(screen.getByTestId("not-owned-overlay")).toBeDefined();
  });

  it("shows loading skeletons", () => {
    mockFetchSuccess();
    renderDeckView();

    expect(screen.getAllByTestId("deck-view-skeleton")).toHaveLength(6);
  });

  it("shows delete confirmation on button click", async () => {
    mockFetchSuccess();
    renderDeckView();

    await waitFor(() => {
      expect(screen.getByTestId("delete-deck-btn")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("delete-deck-btn"));
    expect(screen.getByTestId("delete-confirm-modal")).toBeDefined();
  });

  it("cancels delete confirmation", async () => {
    mockFetchSuccess();
    renderDeckView();

    await waitFor(() => {
      expect(screen.getByTestId("delete-deck-btn")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("delete-deck-btn"));
    fireEvent.click(screen.getByTestId("cancel-delete-btn"));

    expect(screen.queryByTestId("delete-confirm-modal")).toBeNull();
  });

  it("shows error on API failure", async () => {
    mockFetchSuccess({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [{ code: "ERR", message: "Not found" }],
    });
    renderDeckView();

    await waitFor(() => {
      expect(screen.getByTestId("deck-view-error")).toBeDefined();
    });
  });
});
