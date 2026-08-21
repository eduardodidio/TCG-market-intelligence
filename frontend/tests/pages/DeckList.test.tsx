import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeckList } from "../../src/pages/DeckList";

function renderDeckList() {
  return render(
    <MemoryRouter initialEntries={["/decks"]}>
      <DeckList />
    </MemoryRouter>,
  );
}

const MOCK_DECKS = {
  data: [
    {
      id: 1,
      name: "Mono Red Burn",
      description: "Fast aggro",
      total_cards: 60,
      unique_cards: 15,
      owned_cards: 10,
      ownership_pct: 66.67,
      created_at: "2026-08-21T12:00:00",
      updated_at: "2026-08-21T12:00:00",
    },
    {
      id: 2,
      name: "Blue Control",
      description: null,
      total_cards: 60,
      unique_cards: 20,
      owned_cards: 20,
      ownership_pct: 100,
      created_at: "2026-08-21T12:00:00",
      updated_at: "2026-08-21T12:00:00",
    },
  ],
  meta: { cursor: null, total: null, offset: null, request_id: "r1" },
  errors: [],
};

describe("DeckList page", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  function mockFetchSuccess(data = MOCK_DECKS) {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(data),
    }) as unknown as typeof fetch;
  }

  it("renders page title and import button", async () => {
    mockFetchSuccess();
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("page-decks")).toBeDefined();
    });

    expect(screen.getByText("My Decks")).toBeDefined();
    expect(screen.getByTestId("import-deck-btn")).toBeDefined();
  });

  it("displays deck cards after loading", async () => {
    mockFetchSuccess();
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByText("Mono Red Burn")).toBeDefined();
    });

    expect(screen.getByText("Blue Control")).toBeDefined();
    expect(screen.getByTestId("deck-card-1")).toBeDefined();
    expect(screen.getByTestId("deck-card-2")).toBeDefined();
  });

  it("shows empty state when no decks", async () => {
    mockFetchSuccess({
      data: [],
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("deck-empty-state")).toBeDefined();
    });

    expect(screen.getByText("No decks yet")).toBeDefined();
  });

  it("shows loading skeletons", () => {
    mockFetchSuccess();
    renderDeckList();

    expect(screen.getAllByTestId("deck-skeleton")).toHaveLength(3);
  });

  it("opens import modal on button click", async () => {
    mockFetchSuccess();
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("page-decks")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("import-deck-btn"));

    expect(screen.getByTestId("deck-import-modal")).toBeDefined();
  });

  it("shows error on API failure", async () => {
    mockFetchSuccess({
      data: null,
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [{ code: "ERR", message: "Server error" }],
    });
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("deck-list-error")).toBeDefined();
    });
  });
});
