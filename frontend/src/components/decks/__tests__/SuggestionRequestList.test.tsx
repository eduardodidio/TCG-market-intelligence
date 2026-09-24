import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import {
  SuggestionRequestList,
  formatLabel,
  suggestionLabel,
} from "../SuggestionRequestList";
import type { DeckSuggestion } from "../../../types/deckSuggestions";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

function mockDeckSuggestion(overrides: Partial<DeckSuggestion> = {}): DeckSuggestion {
  return {
    id: 1,
    format_name: "commander",
    commander_card_id: 100,
    commander_name: "Atraxa, Praetors' Voice",
    colors: [],
    archetype: null,
    notes: null,
    status: "pending",
    error_message: null,
    saved_deck_id: null,
    created_at: "2026-09-20T10:00:00Z",
    processed_at: null,
    summary: null,
    ...overrides,
  };
}

const mockDeckSuggestionList: DeckSuggestion[] = [
  mockDeckSuggestion({ id: 1, status: "pending" }),
  mockDeckSuggestion({
    id: 2,
    status: "processing",
    format_name: "modern",
    commander_card_id: null,
    commander_name: null,
    colors: ["U", "R"],
    archetype: "tempo",
  }),
  mockDeckSuggestion({
    id: 3,
    status: "done",
    processed_at: "2026-09-21T03:00:00Z",
    summary: {
      total_cards: 100,
      owned_cards: 61,
      missing_cards: 39,
      missing_cost_brl: 412.5,
      unresolved_count: 0,
    },
  }),
  mockDeckSuggestion({
    id: 4,
    status: "failed",
    error_message: "Claude timeout",
  }),
];

function renderList(props: Partial<Parameters<typeof SuggestionRequestList>[0]> = {}) {
  const handlers = {
    onSelect: vi.fn(),
    onRefresh: vi.fn(),
    onDelete: vi.fn(),
  };
  render(
    <SuggestionRequestList
      items={mockDeckSuggestionList}
      selectedId={null}
      loading={false}
      {...handlers}
      {...props}
    />,
  );
  return handlers;
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("SuggestionRequestList", () => {
  it("renders one row per item with the matching status badge", () => {
    renderList();
    expect(screen.getByTestId("suggestion-list")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-status-1")).toHaveTextContent("Na fila");
    expect(screen.getByTestId("suggestion-status-2")).toHaveTextContent("Processando");
    expect(screen.getByTestId("suggestion-status-3")).toHaveTextContent("Pronto");
    expect(screen.getByTestId("suggestion-status-4")).toHaveTextContent("Falhou");
    expect(screen.getByTestId("suggestion-status-1").className).toMatch(/amber/);
    expect(screen.getByTestId("suggestion-status-2").className).toMatch(/cyan/);
    expect(screen.getByTestId("suggestion-status-3").className).toMatch(/green/);
    expect(screen.getByTestId("suggestion-status-4").className).toMatch(/red/);
  });

  it("calls onSelect with the row id on click", () => {
    const { onSelect } = renderList();
    fireEvent.click(
      within(screen.getByTestId("suggestion-row-2")).getByText("UR · tempo"),
    );
    expect(onSelect).toHaveBeenCalledWith(2);
  });

  it("highlights the selected row only", () => {
    renderList({ selectedId: 3 });
    expect(screen.getByTestId("suggestion-row-3")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("suggestion-row-3").className).toMatch(/border-cyan-400/);
    expect(screen.getByTestId("suggestion-row-1")).toHaveAttribute("aria-selected", "false");
    expect(screen.getByTestId("suggestion-row-1").className).not.toMatch(/border-cyan-400/);
  });

  it("shows format, commander label and created date", () => {
    renderList();
    const row = screen.getByTestId("suggestion-row-1");
    expect(row).toHaveTextContent("Commander");
    expect(row).toHaveTextContent("Atraxa, Praetors' Voice");
    expect(row).toHaveTextContent("20/09/2026");
    expect(screen.getByTestId("suggestion-row-2")).toHaveTextContent("Modern");
  });

  it("shows the owned/total text for a done item with summary", () => {
    renderList();
    expect(screen.getByTestId("suggestion-owned-3")).toHaveTextContent("61/100 na coleção");
    expect(screen.queryByTestId("suggestion-owned-1")).not.toBeInTheDocument();
  });

  it("hides owned/total for a done item without summary", () => {
    renderList({ items: [mockDeckSuggestion({ id: 9, status: "done", summary: null })] });
    expect(screen.queryByTestId("suggestion-owned-9")).not.toBeInTheDocument();
  });

  it("shows the error message as tooltip on failed rows only", () => {
    renderList();
    expect(screen.getByTestId("suggestion-status-4")).toHaveAttribute("title", "Claude timeout");
    expect(screen.getByTestId("suggestion-status-1")).not.toHaveAttribute("title");
  });

  it("renders delete only for pending rows", () => {
    renderList();
    expect(screen.getByTestId("suggestion-delete-1")).toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-delete-2")).not.toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-delete-3")).not.toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-delete-4")).not.toBeInTheDocument();
  });

  it("calls onDelete after confirmation without selecting the row", () => {
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const { onDelete, onSelect } = renderList();
    fireEvent.click(screen.getByTestId("suggestion-delete-1"));
    expect(confirmSpy).toHaveBeenCalledTimes(1);
    expect(onDelete).toHaveBeenCalledWith(1);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("does not call onDelete when confirmation is cancelled", () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const { onDelete } = renderList();
    fireEvent.click(screen.getByTestId("suggestion-delete-1"));
    expect(onDelete).not.toHaveBeenCalled();
  });

  it("calls onRefresh when the refresh button is clicked", () => {
    const { onRefresh } = renderList();
    fireEvent.click(screen.getByTestId("suggestion-refresh"));
    expect(onRefresh).toHaveBeenCalledTimes(1);
  });

  it("shows the empty state for an empty list", () => {
    renderList({ items: [] });
    expect(screen.getByTestId("suggestion-list-empty")).toBeInTheDocument();
    expect(screen.getByText("Nenhum pedido ainda")).toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-list-loading")).not.toBeInTheDocument();
  });

  it("shows only the spinner (no empty state) while loading an empty list", () => {
    renderList({ items: [], loading: true });
    expect(screen.getByTestId("suggestion-list-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-list-empty")).not.toBeInTheDocument();
  });

  it("keeps items visible alongside the spinner while loading", () => {
    renderList({ loading: true });
    expect(screen.getByTestId("suggestion-list-loading")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-row-1")).toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-list-empty")).not.toBeInTheDocument();
    expect(screen.getByTestId("suggestion-refresh")).toBeDisabled();
  });
});

describe("label helpers", () => {
  it("uses the commander name when present", () => {
    expect(suggestionLabel(mockDeckSuggestion())).toBe("Atraxa, Praetors' Voice");
  });

  it("joins colors and archetype for non-commander requests", () => {
    expect(
      suggestionLabel(
        mockDeckSuggestion({ commander_name: null, colors: ["W", "B"], archetype: "control" }),
      ),
    ).toBe("WB · control");
  });

  it("omits the separator when a part is missing", () => {
    expect(
      suggestionLabel(mockDeckSuggestion({ commander_name: null, colors: ["C"], archetype: null })),
    ).toBe("C");
    expect(
      suggestionLabel(mockDeckSuggestion({ commander_name: null, colors: [], archetype: "ramp" })),
    ).toBe("ramp");
  });

  it("maps known formats and capitalizes unknown ones", () => {
    expect(formatLabel("pauper")).toBe("Pauper");
    expect(formatLabel("brawl")).toBe("Brawl");
  });
});
