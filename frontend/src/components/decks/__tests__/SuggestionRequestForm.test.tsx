import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import {
  SuggestionRequestForm,
  toggleSuggestionColor,
} from "../SuggestionRequestForm";
import { createDeckSuggestion } from "../../../api/deckSuggestions";
import type { ApiResponse, CommanderSearchResult } from "../../../types/api";
import type { DeckSuggestion } from "../../../types/deckSuggestions";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

vi.mock("../../../api/deckSuggestions", async () => {
  const actual = await vi.importActual<
    typeof import("../../../api/deckSuggestions")
  >("../../../api/deckSuggestions");
  return { ...actual, createDeckSuggestion: vi.fn() };
});

const atraxa: CommanderSearchResult = {
  card_id: 7,
  name_en: "Atraxa",
  name_pt: "Atraxa, Voz dos Pretores",
  set_code: "cm2",
  collector_number: "10",
  color_identity: "WUBG",
  mana_cost: "{G}{W}{U}{B}",
  type_line: "Legendary Creature — Phyrexian Angel Horror",
  rarity: "mythic",
  image_uri: null,
};

vi.mock("../CommanderSearch", () => ({
  CommanderSearch: ({
    selected,
    onSelect,
    onClear,
  }: {
    selected: CommanderSearchResult | null;
    onSelect: (c: CommanderSearchResult) => void;
    onClear: () => void;
  }) => (
    <div data-testid="commander-search-stub">
      <button data-testid="stub-select" onClick={() => onSelect(atraxa)}>
        pick
      </button>
      <button data-testid="stub-clear" onClick={onClear}>
        clear
      </button>
      {selected && <span data-testid="stub-selected">{selected.name_en}</span>}
    </div>
  ),
}));

const mockedCreate = vi.mocked(createDeckSuggestion);

function makeSuggestion(overrides: Partial<DeckSuggestion> = {}): DeckSuggestion {
  return {
    id: 42,
    format_name: "commander",
    commander_card_id: 7,
    commander_name: "Atraxa",
    colors: ["W", "U", "B", "G"],
    archetype: null,
    notes: null,
    status: "pending",
    error_message: null,
    saved_deck_id: null,
    created_at: "2026-09-24T10:00:00",
    processed_at: null,
    summary: null,
    ...overrides,
  };
}

function ok(data: DeckSuggestion): ApiResponse<DeckSuggestion> {
  return { data, errors: [], meta: {} } as unknown as ApiResponse<DeckSuggestion>;
}

function fail(message: string): ApiResponse<DeckSuggestion> {
  return {
    data: null,
    errors: [{ code: "VALIDATION_LIMIT_EXCEEDED", message }],
    meta: {},
  } as unknown as ApiResponse<DeckSuggestion>;
}

const submit = () => screen.getByTestId("suggestion-submit");
const notes = () => screen.getByTestId("suggestion-notes") as HTMLTextAreaElement;

async function clickSubmit() {
  await act(async () => {
    fireEvent.click(submit());
  });
}

describe("toggleSuggestionColor", () => {
  it("adds colors in WUBRG order", () => {
    expect(toggleSuggestionColor(["G"], "R")).toEqual(["R", "G"]);
    expect(toggleSuggestionColor(["R", "G"], "W")).toEqual(["W", "R", "G"]);
  });

  it("removes a selected color", () => {
    expect(toggleSuggestionColor(["R", "G"], "R")).toEqual(["G"]);
  });

  it("C clears WUBRG and WUBRG clears C", () => {
    expect(toggleSuggestionColor(["W", "U"], "C")).toEqual(["C"]);
    expect(toggleSuggestionColor(["C"], "B")).toEqual(["B"]);
    expect(toggleSuggestionColor(["C"], "C")).toEqual([]);
  });
});

describe("SuggestionRequestForm", () => {
  let onCreated: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockedCreate.mockReset();
    onCreated = vi.fn();
  });

  const renderForm = () =>
    render(<SuggestionRequestForm onCreated={onCreated} />);

  it("commander format shows the search + notes only", () => {
    renderForm();
    expect(screen.getByTestId("suggestion-form")).toBeInTheDocument();
    expect(screen.getByTestId("commander-search-stub")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-notes")).toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-color-W")).toBeNull();
    expect(screen.queryByTestId("suggestion-archetype-aggro")).toBeNull();
  });

  it("other formats show colors + archetype + notes, no commander search", () => {
    renderForm();
    fireEvent.click(screen.getByTestId("suggestion-format-modern"));
    expect(screen.queryByTestId("commander-search-stub")).toBeNull();
    for (const c of ["W", "U", "B", "R", "G", "C"]) {
      expect(screen.getByTestId(`suggestion-color-${c}`)).toBeInTheDocument();
    }
    for (const a of ["aggro", "control", "midrange", "combo", "tempo", "ramp"]) {
      expect(screen.getByTestId(`suggestion-archetype-${a}`)).toBeInTheDocument();
    }
    expect(screen.getByTestId("suggestion-notes")).toBeInTheDocument();
  });

  it("happy: commander + notes sends commander_card_id and notes", async () => {
    const created = makeSuggestion({ notes: "Superfriends" });
    mockedCreate.mockResolvedValue(ok(created));
    renderForm();

    expect(submit()).toBeDisabled();
    fireEvent.click(screen.getByTestId("stub-select"));
    fireEvent.change(notes(), { target: { value: "  Superfriends  " } });
    expect(submit()).toBeEnabled();
    await clickSubmit();

    expect(mockedCreate).toHaveBeenCalledWith({
      format_name: "commander",
      commander_card_id: 7,
      notes: "Superfriends",
    });
    expect(onCreated).toHaveBeenCalledWith(created);
    expect(screen.getByTestId("suggestion-success")).toBeInTheDocument();
  });

  it("happy: modern + R,G + aggro sends the matching body", async () => {
    mockedCreate.mockResolvedValue(
      ok(makeSuggestion({ format_name: "modern", colors: ["R", "G"] })),
    );
    renderForm();
    fireEvent.click(screen.getByTestId("suggestion-format-modern"));
    fireEvent.click(screen.getByTestId("suggestion-color-G"));
    fireEvent.click(screen.getByTestId("suggestion-color-R"));
    fireEvent.click(screen.getByTestId("suggestion-archetype-aggro"));
    await clickSubmit();

    expect(mockedCreate).toHaveBeenCalledWith({
      format_name: "modern",
      colors: ["R", "G"],
      archetype: "aggro",
      notes: null,
    });
  });

  it("on success resets the fields but keeps the format", async () => {
    mockedCreate.mockResolvedValue(ok(makeSuggestion({ format_name: "modern" })));
    renderForm();
    fireEvent.click(screen.getByTestId("suggestion-format-modern"));
    fireEvent.click(screen.getByTestId("suggestion-color-R"));
    fireEvent.click(screen.getByTestId("suggestion-archetype-aggro"));
    fireEvent.change(notes(), { target: { value: "burn" } });
    await clickSubmit();

    expect(screen.getByTestId("suggestion-format-modern")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("suggestion-color-R")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByTestId("suggestion-archetype-aggro")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(notes().value).toBe("");
    expect(submit()).toBeDisabled();
  });

  it("switching format resets the format-specific fields", () => {
    renderForm();
    fireEvent.click(screen.getByTestId("stub-select"));
    expect(screen.getByTestId("stub-selected")).toHaveTextContent("Atraxa");
    fireEvent.change(notes(), { target: { value: "hello" } });

    fireEvent.click(screen.getByTestId("suggestion-format-modern"));
    fireEvent.click(screen.getByTestId("suggestion-color-U"));
    fireEvent.click(screen.getByTestId("suggestion-archetype-control"));
    expect(notes().value).toBe("");

    fireEvent.click(screen.getByTestId("suggestion-format-pauper"));
    expect(screen.getByTestId("suggestion-color-U")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByTestId("suggestion-archetype-control")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(submit()).toBeDisabled();

    fireEvent.click(screen.getByTestId("suggestion-format-commander"));
    expect(screen.queryByTestId("stub-selected")).toBeNull();
    expect(submit()).toBeDisabled();
  });

  it("the C toggle clears the other colors and vice versa", () => {
    renderForm();
    fireEvent.click(screen.getByTestId("suggestion-format-standard"));
    fireEvent.click(screen.getByTestId("suggestion-color-W"));
    fireEvent.click(screen.getByTestId("suggestion-color-U"));
    fireEvent.click(screen.getByTestId("suggestion-color-C"));
    expect(screen.getByTestId("suggestion-color-C")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("suggestion-color-W")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByTestId("suggestion-color-U")).toHaveAttribute(
      "aria-pressed",
      "false",
    );

    fireEvent.click(screen.getByTestId("suggestion-color-B"));
    expect(screen.getByTestId("suggestion-color-C")).toHaveAttribute(
      "aria-pressed",
      "false",
    );
    expect(screen.getByTestId("suggestion-color-B")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("whitespace-only notes are sent as null", async () => {
    mockedCreate.mockResolvedValue(ok(makeSuggestion()));
    renderForm();
    fireEvent.click(screen.getByTestId("stub-select"));
    fireEvent.change(notes(), { target: { value: "   \n  " } });
    await clickSubmit();
    expect(mockedCreate).toHaveBeenCalledWith({
      format_name: "commander",
      commander_card_id: 7,
      notes: null,
    });
  });

  it("the counter updates as notes are typed", () => {
    renderForm();
    const counter = screen.getByTestId("suggestion-notes-counter");
    expect(counter).toHaveTextContent("0/1000");
    fireEvent.change(notes(), { target: { value: "abc" } });
    expect(counter).toHaveTextContent("3/1000");
  });

  it("notes allow exactly 1000 chars (maxLength)", () => {
    renderForm();
    expect(notes()).toHaveAttribute("maxLength", "1000");
    fireEvent.change(notes(), { target: { value: "x".repeat(1000) } });
    expect(screen.getByTestId("suggestion-notes-counter")).toHaveTextContent(
      "1000/1000",
    );
  });

  it("shows API error inline and keeps the values", async () => {
    mockedCreate.mockResolvedValue(fail("Too many open requests"));
    renderForm();
    fireEvent.click(screen.getByTestId("stub-select"));
    fireEvent.change(notes(), { target: { value: "keep me" } });
    await clickSubmit();

    expect(screen.getByTestId("suggestion-error")).toHaveTextContent(
      "Too many open requests",
    );
    expect(screen.queryByTestId("suggestion-success")).toBeNull();
    expect(onCreated).not.toHaveBeenCalled();
    expect(notes().value).toBe("keep me");
    expect(screen.getByTestId("stub-selected")).toHaveTextContent("Atraxa");
    expect(submit()).toBeEnabled();
  });

  it("a rejected promise shows a generic error and re-enables submit", async () => {
    mockedCreate.mockRejectedValue(new Error("network down"));
    renderForm();
    fireEvent.click(screen.getByTestId("suggestion-format-legacy"));
    fireEvent.click(screen.getByTestId("suggestion-color-B"));
    fireEvent.click(screen.getByTestId("suggestion-archetype-combo"));
    await clickSubmit();

    expect(screen.getByTestId("suggestion-error")).toHaveTextContent(
      "Could not register the request. Try again.",
    );
    expect(onCreated).not.toHaveBeenCalled();
    expect(screen.getByTestId("suggestion-color-B")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(submit()).toBeEnabled();
  });

  it("disables submit while submitting (no double submit)", async () => {
    let resolve!: (v: ApiResponse<DeckSuggestion>) => void;
    mockedCreate.mockReturnValue(
      new Promise<ApiResponse<DeckSuggestion>>((r) => {
        resolve = r;
      }),
    );
    renderForm();
    fireEvent.click(screen.getByTestId("stub-select"));
    await clickSubmit();
    expect(submit()).toBeDisabled();
    fireEvent.click(submit());
    expect(mockedCreate).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolve(ok(makeSuggestion()));
    });
    expect(onCreated).toHaveBeenCalledTimes(1);
  });

  it("boundary: no colors → disabled; no archetype → disabled", () => {
    renderForm();
    fireEvent.click(screen.getByTestId("suggestion-format-vintage"));
    expect(submit()).toBeDisabled();
    fireEvent.click(screen.getByTestId("suggestion-archetype-ramp"));
    expect(submit()).toBeDisabled();
    fireEvent.click(screen.getByTestId("suggestion-color-G"));
    expect(submit()).toBeEnabled();
    fireEvent.click(screen.getByTestId("suggestion-color-G"));
    expect(submit()).toBeDisabled();
  });

  it("boundary: commander not selected → disabled; cleared → disabled again", () => {
    renderForm();
    fireEvent.change(notes(), { target: { value: "notes only" } });
    expect(submit()).toBeDisabled();
    fireEvent.click(screen.getByTestId("stub-select"));
    expect(submit()).toBeEnabled();
    fireEvent.click(screen.getByTestId("stub-clear"));
    expect(submit()).toBeDisabled();
  });

  it("a new success/error clears the previous banner", async () => {
    mockedCreate
      .mockResolvedValueOnce(fail("Too many open requests"))
      .mockResolvedValueOnce(ok(makeSuggestion()));
    renderForm();
    fireEvent.click(screen.getByTestId("stub-select"));
    await clickSubmit();
    expect(screen.getByTestId("suggestion-error")).toBeInTheDocument();
    await clickSubmit();
    expect(screen.queryByTestId("suggestion-error")).toBeNull();
    expect(screen.getByTestId("suggestion-success")).toBeInTheDocument();
  });
});
