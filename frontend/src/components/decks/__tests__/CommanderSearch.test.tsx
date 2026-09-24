import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { CommanderSearch, getCommanderImageUrl } from "../CommanderSearch";
import { searchCommanders } from "../../../api/decks";
import type { ApiResponse, CommanderSearchResult } from "../../../types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

vi.mock("../../../api/decks", () => ({
  searchCommanders: vi.fn(),
}));

const mockedSearch = vi.mocked(searchCommanders);

const atraxa: CommanderSearchResult = {
  card_id: 100,
  name_en: "Atraxa, Praetors' Voice",
  name_pt: "Atraxa, Voz dos Pretores",
  set_code: "cm2",
  collector_number: "10",
  color_identity: "WUBG",
  mana_cost: "{G}{W}{U}{B}",
  type_line: "Legendary Creature — Phyrexian Angel Horror",
  rarity: "mythic",
  image_uri: null,
};

const krenko: CommanderSearchResult = {
  card_id: 200,
  name_en: "Krenko, Mob Boss",
  name_pt: "Krenko, Mob Boss",
  set_code: null,
  collector_number: null,
  color_identity: "R",
  mana_cost: "{2}{R}{R}",
  type_line: "Legendary Creature — Goblin Warrior",
  rarity: "rare",
  image_uri: "https://img.example/krenko.jpg",
};

function mockCommanderSearchResponse(
  data: CommanderSearchResult[] | null = [atraxa],
  errors: { message: string }[] = [],
): ApiResponse<CommanderSearchResult[]> {
  return { data, errors, meta: {} } as unknown as ApiResponse<
    CommanderSearchResult[]
  >;
}

function deferred<T>() {
  let resolve!: (v: T) => void;
  const promise = new Promise<T>((r) => {
    resolve = r;
  });
  return { promise, resolve };
}

function renderSearch(
  props: Partial<React.ComponentProps<typeof CommanderSearch>> = {},
) {
  const onSelect = vi.fn();
  const onClear = vi.fn();
  render(
    <CommanderSearch
      selected={null}
      onSelect={onSelect}
      onClear={onClear}
      {...props}
    />,
  );
  return { onSelect, onClear };
}

function type(value: string) {
  fireEvent.change(screen.getByTestId("commander-search"), {
    target: { value },
  });
}

async function flushDebounce() {
  await act(async () => {
    vi.advanceTimersByTime(300);
  });
}

describe("CommanderSearch", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    mockedSearch.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("searches once after 300ms and selects an option", async () => {
    mockedSearch.mockResolvedValue(mockCommanderSearchResponse());
    const { onSelect } = renderSearch();
    type("atr");
    await act(async () => {
      vi.advanceTimersByTime(299);
    });
    expect(mockedSearch).not.toHaveBeenCalled();
    await flushDebounce();
    expect(mockedSearch).toHaveBeenCalledTimes(1);
    expect(mockedSearch).toHaveBeenCalledWith("atr");
    const option = screen.getByTestId("commander-option-100");
    expect(option).toHaveTextContent("Atraxa, Praetors' Voice");
    fireEvent.click(option);
    expect(onSelect).toHaveBeenCalledWith(atraxa);
    expect(screen.queryByTestId("commander-search-loading")).toBeNull();
  });

  it("does not search for a single character (trimmed)", async () => {
    renderSearch();
    type("a");
    await flushDebounce();
    type(" a  ");
    await flushDebounce();
    expect(mockedSearch).not.toHaveBeenCalled();
    expect(screen.queryByTestId("commander-search-empty")).toBeNull();
  });

  it("debounces fast typing into a single call", async () => {
    mockedSearch.mockResolvedValue(mockCommanderSearchResponse());
    renderSearch();
    type("a");
    type("at");
    await act(async () => {
      vi.advanceTimersByTime(100);
    });
    type("atr");
    await flushDebounce();
    expect(mockedSearch).toHaveBeenCalledTimes(1);
    expect(mockedSearch).toHaveBeenCalledWith("atr");
  });

  it("shows name_pt only when it differs from name_en", async () => {
    mockedSearch.mockResolvedValue(
      mockCommanderSearchResponse([atraxa, krenko]),
    );
    renderSearch();
    type("kr");
    await flushDebounce();
    expect(screen.getByTestId("commander-option-100")).toHaveTextContent(
      "Atraxa, Voz dos Pretores",
    );
    const krenkoOpt = screen.getByTestId("commander-option-200");
    expect(krenkoOpt.querySelectorAll("p")).toHaveLength(2);
    expect(krenkoOpt.querySelector("img")).toHaveAttribute(
      "src",
      "https://img.example/krenko.jpg",
    );
  });

  it("renders the selected chip and calls onClear", () => {
    const { onClear } = renderSearch({ selected: atraxa });
    const chip = screen.getByTestId("selected-commander");
    expect(chip).toHaveTextContent("Atraxa, Praetors' Voice");
    expect(chip).toHaveTextContent("WUBG");
    fireEvent.click(screen.getByTestId("selected-commander-clear"));
    expect(onClear).toHaveBeenCalledTimes(1);
  });

  it("shows the loading state while the request is pending", async () => {
    const d = deferred<ApiResponse<CommanderSearchResult[]>>();
    mockedSearch.mockReturnValue(d.promise);
    renderSearch();
    type("atr");
    await flushDebounce();
    expect(screen.getByTestId("commander-search-loading")).toBeInTheDocument();
    await act(async () => {
      d.resolve(mockCommanderSearchResponse());
    });
    expect(screen.queryByTestId("commander-search-loading")).toBeNull();
  });

  it("shows the error message from an error envelope", async () => {
    mockedSearch.mockResolvedValue(
      mockCommanderSearchResponse(null, [{ message: "boom" }]),
    );
    renderSearch();
    type("atr");
    await flushDebounce();
    expect(screen.getByTestId("commander-search-error")).toHaveTextContent(
      "boom",
    );
    expect(screen.queryByTestId("commander-search-loading")).toBeNull();
    expect(screen.queryByTestId("commander-search-empty")).toBeNull();
  });

  it("shows an error and clears loading when the promise rejects", async () => {
    mockedSearch.mockRejectedValue(new Error("network down"));
    renderSearch();
    type("atr");
    await flushDebounce();
    expect(screen.getByTestId("commander-search-error")).toHaveTextContent(
      "network down",
    );
    expect(screen.queryByTestId("commander-search-loading")).toBeNull();
  });

  it("shows the empty state when a search returns 0 results", async () => {
    mockedSearch.mockResolvedValue(mockCommanderSearchResponse([]));
    renderSearch();
    type("zzz");
    await flushDebounce();
    expect(screen.getByTestId("commander-search-empty")).toHaveTextContent(
      "zzz",
    );
    // Shortening below the minimum hides the empty state again.
    type("z");
    await flushDebounce();
    expect(screen.queryByTestId("commander-search-empty")).toBeNull();
  });

  it("ignores out-of-order (stale) responses", async () => {
    const first = deferred<ApiResponse<CommanderSearchResult[]>>();
    const second = deferred<ApiResponse<CommanderSearchResult[]>>();
    mockedSearch
      .mockReturnValueOnce(first.promise)
      .mockReturnValueOnce(second.promise);
    renderSearch();
    type("atr");
    await flushDebounce();
    type("kren");
    await flushDebounce();
    expect(mockedSearch).toHaveBeenCalledTimes(2);

    await act(async () => {
      second.resolve(mockCommanderSearchResponse([krenko]));
    });
    await act(async () => {
      first.resolve(mockCommanderSearchResponse([atraxa]));
    });

    expect(screen.getByTestId("commander-option-200")).toBeInTheDocument();
    expect(screen.queryByTestId("commander-option-100")).toBeNull();
    expect(screen.queryByTestId("commander-search-loading")).toBeNull();
  });

  it("drops a pending response once the query goes below the minimum", async () => {
    const d = deferred<ApiResponse<CommanderSearchResult[]>>();
    mockedSearch.mockReturnValue(d.promise);
    renderSearch();
    type("atr");
    await flushDebounce();
    type("a");
    await act(async () => {
      d.resolve(mockCommanderSearchResponse([atraxa]));
    });
    expect(screen.queryByTestId("commander-option-100")).toBeNull();
    expect(screen.queryByTestId("commander-search-loading")).toBeNull();
  });
});

describe("getCommanderImageUrl", () => {
  it("prefers image_uri", () => {
    expect(getCommanderImageUrl(krenko)).toBe("https://img.example/krenko.jpg");
  });

  it("falls back to a Scryfall URL from set/collector", () => {
    expect(getCommanderImageUrl(atraxa)).toBe(
      "https://api.scryfall.com/cards/cm2/10?format=image&version=small",
    );
  });

  it("returns null without image or set/collector", () => {
    expect(
      getCommanderImageUrl({ ...krenko, image_uri: null }),
    ).toBeNull();
  });
});
