import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  SuggestionResultView,
  formatSuggestionPrice,
  getSuggestedCardImageUrl,
  groupSuggestedCards,
} from "../SuggestionResultView";
import type {
  DeckSuggestion,
  SuggestedCard,
  SuggestionResult,
} from "../../../types/deckSuggestions";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

const mockSave = vi.fn();
vi.mock("../../../api/deckSuggestions", () => ({
  saveDeckSuggestion: (...args: unknown[]) => mockSave(...args),
}));

function card(overrides: Partial<SuggestedCard> = {}): SuggestedCard {
  return {
    name_en: "Sol Ring",
    quantity: 1,
    category: "Ramp",
    reason: null,
    card_id: 55,
    set_code: "cmr",
    collector_number: "472",
    image_uri: null,
    is_owned: true,
    owned_quantity: 1,
    missing_quantity: 0,
    unit_price: 12.5,
    missing_cost: 0,
    ...overrides,
  };
}

function mockResult(overrides: Partial<SuggestionResult> = {}): SuggestionResult {
  return {
    deck_name: "Atraxa Superfriends",
    strategy: "Proliferate planeswalkers.",
    format_name: "commander",
    commander: { name_en: "Atraxa, Praetors' Voice", card_id: 123 },
    cards: [
      card({ name_en: "Atraxa, Praetors' Voice", category: "Commander", card_id: 123 }),
      card({ name_en: "Sol Ring", category: "Ramp" }),
      card({
        name_en: "Doubling Season",
        category: "Enchantment",
        card_id: 77,
        is_owned: false,
        owned_quantity: 0,
        missing_quantity: 1,
        unit_price: 300,
        missing_cost: 300,
      }),
      card({
        name_en: "Unpriced Thing",
        category: "Enchantment",
        card_id: 78,
        is_owned: false,
        owned_quantity: 0,
        missing_quantity: 1,
        unit_price: null,
        missing_cost: null,
      }),
      card({ name_en: "Forest", category: "Land", quantity: 10, card_id: 9 }),
    ],
    summary: {
      total_cards: 14,
      owned_cards: 12,
      missing_cards: 2,
      missing_cost_brl: 300,
      unresolved_count: 1,
    },
    unresolved: ["Nome Inventado"],
    warnings: ["Deck has 14 cards (expected 100)"],
    provider: "cli",
    model: "claude-sonnet-5",
    generated_at: "2026-09-25T03:00:12",
    ...overrides,
  };
}

function mockDeckSuggestion(overrides: Partial<DeckSuggestion> = {}): DeckSuggestion {
  return {
    id: 7,
    format_name: "commander",
    commander_card_id: 123,
    commander_name: "Atraxa, Praetors' Voice",
    colors: ["W", "U", "B", "G"],
    archetype: null,
    notes: null,
    status: "done",
    error_message: null,
    saved_deck_id: null,
    created_at: "2026-09-24T10:00:00",
    processed_at: "2026-09-25T03:00:12",
    summary: null,
    result: mockResult(),
    ...overrides,
  };
}

function renderView(s: DeckSuggestion, onSaved?: (id: number) => void) {
  return render(
    <MemoryRouter>
      <SuggestionResultView suggestion={s} onSaved={onSaved} />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  mockNavigate.mockReset();
  mockSave.mockReset();
});

describe("SuggestionResultView — non-done statuses", () => {
  it("pending shows the queue info", () => {
    renderView(mockDeckSuggestion({ status: "pending", result: null }));
    expect(screen.getByTestId("suggestion-result-pending")).toHaveTextContent(
      "Na fila – será gerado na próxima execução diária.",
    );
    expect(screen.queryByTestId("suggestion-result")).not.toBeInTheDocument();
  });

  it("processing shows the info box", () => {
    renderView(mockDeckSuggestion({ status: "processing", result: null }));
    expect(screen.getByTestId("suggestion-result-pending")).toBeInTheDocument();
  });

  it("failed shows error_message", () => {
    renderView(
      mockDeckSuggestion({ status: "failed", result: null, error_message: "Claude timeout" }),
    );
    expect(screen.getByTestId("suggestion-result-failed")).toHaveTextContent("Claude timeout");
  });

  it("done without a result falls back to the failed box", () => {
    renderView(mockDeckSuggestion({ result: null }));
    expect(screen.getByTestId("suggestion-result-failed")).toBeInTheDocument();
  });
});

describe("SuggestionResultView — done", () => {
  it("renders strategy, summary tiles, grouped cards and badges", () => {
    renderView(mockDeckSuggestion());
    expect(screen.getByTestId("suggestion-result")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-strategy")).toHaveTextContent(
      "Proliferate planeswalkers.",
    );
    expect(screen.getByTestId("suggestion-commander")).toHaveTextContent("Atraxa");

    const summary = screen.getByTestId("suggestion-summary");
    expect(summary.children).toHaveLength(4);
    expect(screen.getByTestId("suggestion-summary-total")).toHaveTextContent("14");
    expect(screen.getByTestId("suggestion-summary-owned")).toHaveTextContent("12");
    expect(screen.getByTestId("suggestion-summary-missing")).toHaveTextContent("2");
    expect(screen.getByTestId("suggestion-summary-cost")).toHaveTextContent(/R\$\s*300,00/);

    expect(screen.getByTestId("suggestion-card-1")).toHaveTextContent("Na coleção");
    expect(screen.getByTestId("suggestion-card-2")).toHaveTextContent(/R\$\s*300,00/);
    expect(screen.getByTestId("suggestion-card-3")).toHaveTextContent("—");

    // Order: Commander first, Land last.
    const rows = screen.getAllByTestId(/^suggestion-card-\d+$/);
    expect(rows[0]).toHaveTextContent("Atraxa");
    expect(rows[rows.length - 1]).toHaveTextContent("Forest");

    expect(screen.getByTestId("suggestion-unresolved")).toHaveTextContent("Nome Inventado");
    expect(screen.getByTestId("suggestion-warnings")).toHaveTextContent(
      "Deck has 14 cards",
    );
    expect(screen.getByTestId("suggestion-deck-name-input")).toHaveValue(
      "Atraxa Superfriends",
    );
  });

  it("missing_cost_brl null renders an em dash", () => {
    const result = mockResult();
    result.summary = { ...result.summary, missing_cost_brl: null };
    renderView(mockDeckSuggestion({ result }));
    expect(screen.getByTestId("suggestion-summary-cost")).toHaveTextContent("—");
  });

  it("hides unresolved/warnings when empty and renders without a commander", () => {
    renderView(
      mockDeckSuggestion({
        format_name: "modern",
        result: mockResult({
          format_name: "modern",
          commander: null,
          unresolved: [],
          warnings: [],
          cards: [card({ category: "Creature" })],
        }),
      }),
    );
    expect(screen.queryByTestId("suggestion-unresolved")).not.toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-warnings")).not.toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-commander")).not.toBeInTheDocument();
    expect(screen.getByTestId("suggestion-card-0")).toBeInTheDocument();
  });

  it("renders 100 cards without crashing", () => {
    const cards = Array.from({ length: 100 }, (_, i) =>
      card({ name_en: `Card ${i}`, card_id: i, category: i % 3 ? "Creature" : "Land" }),
    );
    renderView(mockDeckSuggestion({ result: mockResult({ cards }) }));
    expect(screen.getAllByTestId(/^suggestion-card-\d+$/)).toHaveLength(100);
  });

  it("shows 'Ver deck salvo' link when already saved", () => {
    renderView(mockDeckSuggestion({ saved_deck_id: 99 }));
    const link = screen.getByTestId("suggestion-view-deck");
    expect(link).toHaveAttribute("href", "/decks/99");
    expect(screen.queryByTestId("suggestion-save-btn")).not.toBeInTheDocument();
  });
});

describe("SuggestionResultView — save", () => {
  it("saves with the typed name and navigates", async () => {
    mockSave.mockResolvedValue({ data: { deck_id: 42 }, errors: [] });
    const onSaved = vi.fn();
    renderView(mockDeckSuggestion(), onSaved);
    fireEvent.change(screen.getByTestId("suggestion-deck-name-input"), {
      target: { value: "Meu Deck" },
    });
    fireEvent.click(screen.getByTestId("suggestion-save-btn"));
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/decks/42"));
    expect(mockSave).toHaveBeenCalledWith(7, "Meu Deck");
    expect(onSaved).toHaveBeenCalledWith(42);
  });

  it("empty name falls back to result.deck_name", async () => {
    mockSave.mockResolvedValue({ data: { deck_id: 42 }, errors: [] });
    renderView(mockDeckSuggestion());
    fireEvent.change(screen.getByTestId("suggestion-deck-name-input"), {
      target: { value: "   " },
    });
    fireEvent.click(screen.getByTestId("suggestion-save-btn"));
    await waitFor(() =>
      expect(mockSave).toHaveBeenCalledWith(7, "Atraxa Superfriends"),
    );
  });

  it("disables the button while saving", async () => {
    let resolve!: (v: unknown) => void;
    mockSave.mockReturnValue(new Promise((r) => (resolve = r)));
    renderView(mockDeckSuggestion());
    fireEvent.click(screen.getByTestId("suggestion-save-btn"));
    await waitFor(() => expect(screen.getByTestId("suggestion-save-btn")).toBeDisabled());
    resolve({ data: { deck_id: 1 }, errors: [] });
    await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith("/decks/1"));
  });

  it("shows API errors inline without navigating", async () => {
    mockSave.mockResolvedValue({
      data: null,
      errors: [{ code: "RESOURCE_CONFLICT", message: "Sugestão não está pronta" }],
    });
    renderView(mockDeckSuggestion());
    fireEvent.click(screen.getByTestId("suggestion-save-btn"));
    expect(await screen.findByTestId("suggestion-save-error")).toHaveTextContent(
      "Sugestão não está pronta",
    );
    expect(mockNavigate).not.toHaveBeenCalled();
    expect(screen.getByTestId("suggestion-save-btn")).not.toBeDisabled();
  });

  it("shows thrown errors inline", async () => {
    mockSave.mockRejectedValue(new Error("Network down"));
    renderView(mockDeckSuggestion());
    fireEvent.click(screen.getByTestId("suggestion-save-btn"));
    expect(await screen.findByTestId("suggestion-save-error")).toHaveTextContent(
      "Network down",
    );
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("missing deck_id in response is an error", async () => {
    mockSave.mockResolvedValue({ data: null, errors: [] });
    renderView(mockDeckSuggestion());
    fireEvent.click(screen.getByTestId("suggestion-save-btn"));
    expect(await screen.findByTestId("suggestion-save-error")).toBeInTheDocument();
    expect(mockNavigate).not.toHaveBeenCalled();
  });
});

describe("helpers", () => {
  it("groupSuggestedCards orders commander first, land last, others alphabetical", () => {
    const groups = groupSuggestedCards([
      card({ category: "Land" }),
      card({ category: "Removal" }),
      card({ category: "Commander" }),
      card({ category: "Draw" }),
      card({ category: "" }),
    ]);
    expect(groups.map((g) => g.category)).toEqual([
      "Commander",
      "Draw",
      "Other",
      "Removal",
      "Land",
    ]);
    expect(groups[0].items[0].index).toBe(2);
  });

  it("getSuggestedCardImageUrl prefers image_uri then Scryfall fallback", () => {
    expect(getSuggestedCardImageUrl(card({ image_uri: "x.jpg" }))).toBe("x.jpg");
    expect(getSuggestedCardImageUrl(card())).toBe(
      "https://api.scryfall.com/cards/cmr/472?format=image&version=small",
    );
    expect(
      getSuggestedCardImageUrl(card({ set_code: null, collector_number: null })),
    ).toBeNull();
  });

  it("formatSuggestionPrice handles null and zero", () => {
    expect(formatSuggestionPrice(null)).toBe("—");
    expect(formatSuggestionPrice(undefined)).toBe("—");
    expect(formatSuggestionPrice(0)).toMatch(/R\$\s*0,00/);
  });
});
