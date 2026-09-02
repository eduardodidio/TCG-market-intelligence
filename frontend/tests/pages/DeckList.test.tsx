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
      total_value: 150.5,
      value_change_pct: 5.2,
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
      total_value: null,
      value_change_pct: null,
      created_at: "2026-08-21T12:00:00",
      updated_at: "2026-08-21T12:00:00",
    },
    {
      id: 3,
      name: "Jund Midrange",
      description: null,
      total_cards: 60,
      unique_cards: 25,
      owned_cards: 15,
      ownership_pct: 60,
      total_value: 300.0,
      value_change_pct: -3.1,
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

  function mockFetchSuccess(data: unknown = MOCK_DECKS) {
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

    expect(screen.getAllByText("My Decks").length).toBeGreaterThanOrEqual(1);
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

  it("renders total_value badge on deck card", async () => {
    mockFetchSuccess();
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("deck-card-1")).toBeDefined();
    });

    const badges = screen.getAllByTestId("deck-value-badge");
    expect(badges.length).toBeGreaterThanOrEqual(1);

    // First deck has value R$ 150.50
    expect(badges[0].textContent).toContain("R$ 150.50");
  });

  it("shows N/A when total_value is null", async () => {
    mockFetchSuccess();
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("deck-card-2")).toBeDefined();
    });

    const badges = screen.getAllByTestId("deck-value-badge");
    // Second deck (id=2) has null value
    expect(badges[1].textContent).toContain("N/A");
  });

  it("shows green change indicator for positive value_change_pct", async () => {
    mockFetchSuccess();
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("deck-card-1")).toBeDefined();
    });

    const changes = screen.getAllByTestId("deck-value-change");
    expect(changes[0].textContent).toContain("+5.2%");
    expect(changes[0].className).toContain("text-green-400");
  });

  it("shows red change indicator for negative value_change_pct", async () => {
    mockFetchSuccess();
    renderDeckList();

    await waitFor(() => {
      expect(screen.getByTestId("deck-card-3")).toBeDefined();
    });

    const changes = screen.getAllByTestId("deck-value-change");
    const negativeChange = changes.find((el) => el.textContent?.includes("-3.1%"));
    expect(negativeChange).toBeDefined();
    expect(negativeChange!.className).toContain("text-red-400");
  });
});
