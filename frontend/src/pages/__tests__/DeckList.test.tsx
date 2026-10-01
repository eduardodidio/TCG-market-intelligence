import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeckList } from "../DeckList";
import * as decksApi from "../../api/decks";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>(
    "react-router-dom",
  );
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("../../api/decks", () => ({
  fetchDecks: vi.fn(),
  createDeck: vi.fn(),
}));

vi.mock("../../components/DeckImportModal", () => ({
  DeckImportModal: () => <div data-testid="mock-deck-import-modal" />,
}));

describe("DeckList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(decksApi.fetchDecks).mockResolvedValue({
      data: [
        {
          id: 1,
          name: "Test Deck",
          description: null,
          total_cards: 100,
          unique_cards: 60,
          owned_cards: 50,
          ownership_pct: 83,
          total_value: 500.0,
          value_change_pct: 2.5,
          created_at: "2026-01-01",
          updated_at: "2026-01-01",
        },
      ],
      meta: { cursor: null, total: 1, offset: null, request_id: "r1" },
      errors: [],
    });
  });

  it("renders the New Deck button", async () => {
    render(
      <MemoryRouter>
        <DeckList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("new-deck-btn")).toBeInTheDocument();
    });
  });

  it("renders the Import Deck button", async () => {
    render(
      <MemoryRouter>
        <DeckList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("import-deck-btn")).toBeInTheDocument();
    });
  });

  it("clicking New Deck opens create modal", async () => {
    render(
      <MemoryRouter>
        <DeckList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("new-deck-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("new-deck-btn"));

    expect(screen.getByTestId("deck-create-modal")).toBeInTheDocument();
  });

  it("navigates to new deck on creation success", async () => {
    vi.mocked(decksApi.createDeck).mockResolvedValue({
      data: { deck_id: 99, name: "New Deck", description: null },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    render(
      <MemoryRouter>
        <DeckList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("new-deck-btn")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("new-deck-btn"));
    fireEvent.change(screen.getByTestId("create-deck-name-input"), {
      target: { value: "New Deck" },
    });
    fireEvent.click(screen.getByTestId("submit-create-btn"));

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/decks/99");
    });
  });

  it("shows empty state with New Deck action when no decks", async () => {
    vi.mocked(decksApi.fetchDecks).mockResolvedValue({
      data: [],
      meta: { cursor: null, total: 0, offset: null, request_id: "r1" },
      errors: [],
    });

    render(
      <MemoryRouter>
        <DeckList />
      </MemoryRouter>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("deck-empty-state")).toBeInTheDocument();
    });

    // The empty state should contain both New Deck and Import Deck actions
    // "New Deck" appears in both the header button and the empty state action
    expect(screen.getAllByText("New Deck").length).toBeGreaterThanOrEqual(2);
    expect(screen.getAllByText("Import Deck").length).toBeGreaterThanOrEqual(2);
  });
});
