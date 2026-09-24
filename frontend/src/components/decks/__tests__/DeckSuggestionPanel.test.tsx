import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  within,
  act,
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { DeckSuggestionPanel } from "../DeckSuggestionPanel";
import {
  createDeckSuggestion,
  deleteDeckSuggestion,
  getDeckSuggestion,
  listDeckSuggestions,
} from "../../../api/deckSuggestions";
import type { ApiResponse } from "../../../types/api";
import type {
  DeckSuggestion,
  SuggestionResult,
} from "../../../types/deckSuggestions";

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
  return {
    ...actual,
    listDeckSuggestions: vi.fn(),
    getDeckSuggestion: vi.fn(),
    createDeckSuggestion: vi.fn(),
    deleteDeckSuggestion: vi.fn(),
    saveDeckSuggestion: vi.fn(),
  };
});

vi.mock("../../../api/decks", () => ({
  searchCommanders: vi.fn(() => Promise.resolve({ data: [], errors: [] })),
}));

const mockList = vi.mocked(listDeckSuggestions);
const mockGet = vi.mocked(getDeckSuggestion);
const mockCreate = vi.mocked(createDeckSuggestion);
const mockDelete = vi.mocked(deleteDeckSuggestion);

function ok<T>(data: T): ApiResponse<T> {
  return { data, errors: [] } as unknown as ApiResponse<T>;
}

function fail<T>(message: string): ApiResponse<T> {
  return {
    data: null,
    errors: [{ code: "ERR", message }],
  } as unknown as ApiResponse<T>;
}

function mockResult(): SuggestionResult {
  return {
    deck_name: "Atraxa Superfriends",
    strategy: "Proliferate planeswalkers.",
    format_name: "commander",
    commander: { name_en: "Atraxa, Praetors' Voice", card_id: 123 },
    cards: [
      {
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
      },
    ],
    summary: {
      total_cards: 1,
      owned_cards: 1,
      missing_cards: 0,
      missing_cost_brl: 0,
      unresolved_count: 0,
    },
    unresolved: [],
    warnings: [],
    provider: "cli",
    model: "claude-sonnet-5",
    generated_at: "2026-09-25T03:00:12",
  };
}

function mockDeckSuggestion(
  overrides: Partial<DeckSuggestion> = {},
): DeckSuggestion {
  return {
    id: 1,
    format_name: "commander",
    commander_card_id: 123,
    commander_name: "Atraxa, Praetors' Voice",
    colors: ["W", "U", "B", "G"],
    archetype: null,
    notes: null,
    status: "pending",
    error_message: null,
    saved_deck_id: null,
    created_at: "2026-09-24T12:00:00",
    processed_at: null,
    summary: null,
    ...overrides,
  };
}

const pendingItem = mockDeckSuggestion({ id: 1, status: "pending" });
const doneItem = mockDeckSuggestion({
  id: 2,
  status: "done",
  processed_at: "2026-09-25T03:00:12",
  summary: mockResult().summary,
});
const mockDeckSuggestionList = [pendingItem, doneItem];

function renderPanel() {
  return render(
    <MemoryRouter>
      <DeckSuggestionPanel />
    </MemoryRouter>,
  );
}

function selectRow(id: number) {
  const row = screen.getByTestId(`suggestion-row-${id}`);
  fireEvent.click(within(row).getAllByRole("button")[0]);
}

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

describe("DeckSuggestionPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockList.mockResolvedValue(ok(mockDeckSuggestionList));
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads the list on mount and shows a placeholder with no selection", async () => {
    renderPanel();
    expect(screen.getByTestId("suggestion-form")).toBeInTheDocument();
    await screen.findByTestId("suggestion-row-1");
    expect(screen.getByTestId("suggestion-row-2")).toBeInTheDocument();
    expect(mockList).toHaveBeenCalledTimes(1);
    expect(
      screen.getByTestId("suggestion-panel-placeholder"),
    ).toBeInTheDocument();
  });

  it("selecting a done item fetches the detail and shows the result with the save button", async () => {
    mockGet.mockResolvedValue(ok({ ...doneItem, result: mockResult() }));
    renderPanel();
    await screen.findByTestId("suggestion-row-2");

    selectRow(2);

    expect(mockGet).toHaveBeenCalledWith(2);
    expect(await screen.findByTestId("suggestion-result")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-save-btn")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-row-2")).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });

  it("selecting a pending item shows the pending message", async () => {
    mockGet.mockResolvedValue(ok(pendingItem));
    renderPanel();
    await screen.findByTestId("suggestion-row-1");
    selectRow(1);
    expect(
      await screen.findByTestId("suggestion-result-pending"),
    ).toBeInTheDocument();
  });

  it("creating a request prepends it as pending, selects it and shows the success banner", async () => {
    mockList.mockResolvedValue(ok([]));
    const created = mockDeckSuggestion({
      id: 10,
      format_name: "standard",
      commander_card_id: null,
      commander_name: null,
      colors: ["R"],
      archetype: "aggro",
    });
    mockCreate.mockResolvedValue(ok(created));
    renderPanel();
    await screen.findByTestId("suggestion-list-empty");

    fireEvent.click(screen.getByTestId("suggestion-format-standard"));
    fireEvent.click(screen.getByTestId("suggestion-color-R"));
    fireEvent.click(screen.getByTestId("suggestion-archetype-aggro"));
    fireEvent.click(screen.getByTestId("suggestion-submit"));

    expect(await screen.findByTestId("suggestion-row-10")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-success")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-status-10")).toHaveTextContent(
      "Na fila",
    );
    expect(screen.getByTestId("suggestion-row-10")).toHaveAttribute(
      "aria-selected",
      "true",
    );
    expect(screen.getByTestId("suggestion-result-pending")).toBeInTheDocument();
    expect(mockGet).not.toHaveBeenCalled();
  });

  it("prepends new requests above existing ones", async () => {
    const created = mockDeckSuggestion({ id: 3 });
    mockCreate.mockResolvedValue(ok(created));
    renderPanel();
    await screen.findByTestId("suggestion-row-1");

    fireEvent.click(screen.getByTestId("suggestion-format-modern"));
    fireEvent.click(screen.getByTestId("suggestion-color-U"));
    fireEvent.click(screen.getByTestId("suggestion-archetype-control"));
    fireEvent.click(screen.getByTestId("suggestion-submit"));

    await screen.findByTestId("suggestion-row-3");
    const rows = screen
      .getAllByTestId(/^suggestion-row-/)
      .map((el) => el.getAttribute("data-testid"));
    expect(rows).toEqual([
      "suggestion-row-3",
      "suggestion-row-1",
      "suggestion-row-2",
    ]);
  });

  it("shows an error banner when the list fails and the form stays usable", async () => {
    mockList.mockResolvedValue(fail("List exploded"));
    renderPanel();
    expect(await screen.findByText("List exploded")).toBeInTheDocument();
    expect(screen.getByTestId("error-banner")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("suggestion-format-standard"));
    fireEvent.click(screen.getByTestId("suggestion-color-G"));
    fireEvent.click(screen.getByTestId("suggestion-archetype-ramp"));
    expect(screen.getByTestId("suggestion-submit")).toBeEnabled();
  });

  it("shows an error banner when the list request throws", async () => {
    mockList.mockRejectedValue(new Error("boom"));
    renderPanel();
    expect(await screen.findByText("boom")).toBeInTheDocument();
  });

  it("shows an error in the result area when the detail fetch fails", async () => {
    mockGet.mockResolvedValue(fail("Detail not found"));
    renderPanel();
    await screen.findByTestId("suggestion-row-2");
    selectRow(2);
    const area = screen.getByTestId("suggestion-result-area");
    expect(await within(area).findByText("Detail not found")).toBeInTheDocument();
    expect(within(area).getByTestId("error-banner")).toBeInTheDocument();
  });

  it("deleting the selected item removes it and clears the selection", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockGet.mockResolvedValue(ok(pendingItem));
    mockDelete.mockResolvedValue(undefined);
    renderPanel();
    await screen.findByTestId("suggestion-row-1");
    selectRow(1);
    await screen.findByTestId("suggestion-result-pending");

    fireEvent.click(screen.getByTestId("suggestion-delete-1"));

    await waitFor(() =>
      expect(screen.queryByTestId("suggestion-row-1")).not.toBeInTheDocument(),
    );
    expect(mockDelete).toHaveBeenCalledWith(1);
    expect(
      screen.getByTestId("suggestion-panel-placeholder"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-row-2")).toBeInTheDocument();
  });

  it("keeps the item and shows an error when delete fails", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(true);
    mockDelete.mockRejectedValue(new Error("Delete failed"));
    renderPanel();
    await screen.findByTestId("suggestion-row-1");
    fireEvent.click(screen.getByTestId("suggestion-delete-1"));
    expect(await screen.findByText("Delete failed")).toBeInTheDocument();
    expect(screen.getByTestId("suggestion-row-1")).toBeInTheDocument();
  });

  it("refresh reloads the list and the selected detail", async () => {
    mockGet.mockResolvedValue(ok(pendingItem));
    renderPanel();
    await screen.findByTestId("suggestion-row-1");
    selectRow(1);
    await screen.findByTestId("suggestion-result-pending");

    const processed: DeckSuggestion = {
      ...pendingItem,
      status: "done",
      result: mockResult(),
      summary: mockResult().summary,
    };
    mockList.mockResolvedValue(ok([processed, doneItem]));
    mockGet.mockResolvedValue(ok(processed));

    fireEvent.click(screen.getByTestId("suggestion-refresh"));

    expect(await screen.findByTestId("suggestion-result")).toBeInTheDocument();
    expect(mockList).toHaveBeenCalledTimes(2);
    expect(mockGet).toHaveBeenCalledTimes(2);
    expect(mockGet).toHaveBeenLastCalledWith(1);
  });

  it("rapid selection changes: the last selection wins", async () => {
    const first = deferred<ApiResponse<DeckSuggestion>>();
    const second = deferred<ApiResponse<DeckSuggestion>>();
    mockGet
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    renderPanel();
    await screen.findByTestId("suggestion-row-1");

    selectRow(1);
    selectRow(2);

    await act(async () => {
      second.resolve(ok({ ...doneItem, result: mockResult() }));
    });
    expect(await screen.findByTestId("suggestion-result")).toBeInTheDocument();

    // The stale response for item 1 arrives late and must be ignored.
    await act(async () => {
      first.resolve(ok(pendingItem));
    });
    expect(screen.getByTestId("suggestion-result")).toBeInTheDocument();
    expect(
      screen.queryByTestId("suggestion-result-pending"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("suggestion-row-2")).toHaveAttribute(
      "aria-selected",
      "true",
    );
  });
});
