import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MetaDeckListResponse, MetaFormat } from "../../../types/metaDecks";
import { MetaDecksPanel } from "../MetaDecksPanel";
import { fail, makeCard, makeDeck, ok } from "./fixtures";

vi.mock("../../../api/metaDecks", () => ({
  fetchMetaFormats: vi.fn(),
  fetchMetaDecks: vi.fn(),
  fetchMetaDeck: vi.fn(),
}));

import { fetchMetaDeck, fetchMetaDecks, fetchMetaFormats } from "../../../api/metaDecks";

const mockFormats = vi.mocked(fetchMetaFormats);
const mockDecks = vi.mocked(fetchMetaDecks);
const mockDeck = vi.mocked(fetchMetaDeck);

function listResponse(overrides: Partial<MetaDeckListResponse> = {}): MetaDeckListResponse {
  const decks = overrides.decks ?? [
    makeDeck({ id: 1, rank: 1, archetype: "Boros Energy", total_value_brl: 1000 }),
    makeDeck({ id: 2, rank: 2, archetype: "Amulet Titan", total_value_brl: 2500.75 }),
    makeDeck({ id: 3, rank: 3, archetype: "Ruby Storm", total_value_brl: 99.9 }),
  ];
  return {
    format: "modern",
    snapshot_date: "2026-09-24",
    source: "MTGGoldfish",
    total: decks.length,
    decks,
    ...overrides,
  };
}

function renderPanel(format: MetaFormat = "modern", onFormatChange = vi.fn()) {
  const utils = render(
    <MemoryRouter>
      <MetaDecksPanel format={format} onFormatChange={onFormatChange} />
    </MemoryRouter>,
  );
  const rerender = (next: MetaFormat) =>
    utils.rerender(
      <MemoryRouter>
        <MetaDecksPanel format={next} onFormatChange={onFormatChange} />
      </MemoryRouter>,
    );
  return { ...utils, rerender, onFormatChange };
}

describe("MetaDecksPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFormats.mockResolvedValue(
      ok({
        formats: [
          { format: "commander", latest_snapshot_date: "2026-09-24", deck_count: 50 },
          { format: "modern", latest_snapshot_date: "2026-09-24", deck_count: 3 },
        ],
      }),
    );
  });

  it("shows skeleton while loading", () => {
    mockFormats.mockReturnValue(new Promise(() => {}));
    mockDecks.mockReturnValue(new Promise(() => {}));
    renderPanel();
    expect(screen.getAllByTestId("meta-decks-skeleton")).toHaveLength(3);
  });

  it("renders decks in rank order with formatted BRL and footer", async () => {
    mockDecks.mockResolvedValue(ok(listResponse()));
    renderPanel();
    const list = await screen.findByTestId("meta-decks-list");
    const ranks = within(list).getAllByTestId("meta-deck-rank").map((el) => el.textContent);
    expect(ranks).toEqual(["#1", "#2", "#3"]);
    const values = within(list).getAllByTestId("meta-deck-value").map((el) => el.textContent);
    expect(values[1]).toMatch(/R\$\s*2\.500,75/);
    expect(screen.getByTestId("meta-decks-footer")).toHaveTextContent("MTGGoldfish");
    expect(screen.getByTestId("meta-decks-footer")).toHaveTextContent("24/09/2026");
    expect(mockDecks).toHaveBeenCalledWith(
      { format: "modern", limit: 20, offset: 0 },
      expect.objectContaining({ signal: expect.anything() }),
    );
    expect(screen.queryByTestId("meta-load-more-btn")).not.toBeInTheDocument();
  });

  it("loads formats once and disables formats without snapshot", async () => {
    mockDecks.mockResolvedValue(ok(listResponse()));
    const { rerender } = renderPanel();
    await waitFor(() => expect(screen.getByTestId("meta-format-pauper")).toBeDisabled());
    expect(screen.getByTestId("meta-format-commander")).not.toBeDisabled();
    rerender("commander");
    await waitFor(() => expect(mockDecks).toHaveBeenCalledTimes(2));
    expect(mockFormats).toHaveBeenCalledTimes(1);
  });

  it("clicking a pill calls onFormatChange; format prop change refetches", async () => {
    mockDecks.mockResolvedValue(ok(listResponse()));
    const { rerender, onFormatChange } = renderPanel();
    await screen.findByTestId("meta-decks-list");
    await waitFor(() => expect(screen.getByTestId("meta-format-commander")).not.toBeDisabled());
    fireEvent.click(screen.getByTestId("meta-format-commander"));
    expect(onFormatChange).toHaveBeenCalledWith("commander");

    rerender("commander");
    await waitFor(() =>
      expect(mockDecks).toHaveBeenLastCalledWith(
        { format: "commander", limit: 20, offset: 0 },
        expect.anything(),
      ),
    );
  });

  it("disabled pill does not trigger onFormatChange", async () => {
    mockDecks.mockResolvedValue(ok(listResponse()));
    const { onFormatChange } = renderPanel();
    await waitFor(() => expect(screen.getByTestId("meta-format-legacy")).toBeDisabled());
    fireEvent.click(screen.getByTestId("meta-format-legacy"));
    expect(onFormatChange).not.toHaveBeenCalled();
  });

  it("shows EmptyState when list is empty", async () => {
    mockDecks.mockResolvedValue(ok(listResponse({ decks: [], total: 0, source: null, snapshot_date: null })));
    renderPanel();
    expect(await screen.findByTestId("meta-decks-empty")).toBeInTheDocument();
    expect(screen.getByTestId("empty-state")).toBeInTheDocument();
  });

  it("shows ErrorBanner on API errors and retry refetches", async () => {
    mockDecks.mockResolvedValueOnce(fail("server down"));
    renderPanel();
    const banner = await screen.findByTestId("error-banner");
    expect(banner).toHaveTextContent("server down");
    expect(screen.queryByTestId("meta-decks-empty")).not.toBeInTheDocument();

    mockDecks.mockResolvedValueOnce(ok(listResponse()));
    fireEvent.click(within(banner).getByRole("button"));
    expect(await screen.findByTestId("meta-decks-list")).toBeInTheDocument();
    expect(screen.queryByTestId("error-banner")).not.toBeInTheDocument();
    expect(mockDecks).toHaveBeenCalledTimes(2);
  });

  it("formats endpoint failure is non-fatal (pills stay enabled)", async () => {
    mockFormats.mockRejectedValue(new Error("nope"));
    mockDecks.mockResolvedValue(ok(listResponse()));
    renderPanel();
    await screen.findByTestId("meta-decks-list");
    expect(screen.getByTestId("meta-format-legacy")).not.toBeDisabled();
  });

  it("load more appends next page and disappears when all loaded", async () => {
    const page1 = Array.from({ length: 20 }, (_, i) => makeDeck({ id: i + 1, rank: i + 1 }));
    const page2 = [makeDeck({ id: 21, rank: 21 })];
    mockDecks
      .mockResolvedValueOnce(ok(listResponse({ decks: page1, total: 21 })))
      .mockResolvedValueOnce(ok(listResponse({ decks: page2, total: 21 })));
    renderPanel();
    const btn = await screen.findByTestId("meta-load-more-btn");
    fireEvent.click(btn);
    await waitFor(() => expect(screen.getByTestId("meta-deck-row-21")).toBeInTheDocument());
    expect(screen.getAllByTestId("meta-deck-rank")).toHaveLength(21);
    expect(mockDecks).toHaveBeenLastCalledWith(
      { format: "modern", limit: 20, offset: 20 },
      expect.anything(),
    );
    expect(screen.queryByTestId("meta-load-more-btn")).not.toBeInTheDocument();
  });

  it("expands a deck showing grouped cards; second click collapses", async () => {
    mockDecks.mockResolvedValue(ok(listResponse()));
    mockDeck.mockResolvedValue(
      ok({
        ...makeDeck({ id: 2 }),
        cards: [
          makeCard({ name: "Primeval Titan", board: "main" }),
          makeCard({ name: "Force of Vigor", board: "side" }),
        ],
      }),
    );
    renderPanel();
    const row = await screen.findByTestId("meta-deck-row-2");
    fireEvent.click(within(row).getByTestId("meta-deck-toggle"));
    expect(await within(row).findByTestId("meta-board-main")).toBeInTheDocument();
    expect(within(row).getByTestId("meta-board-side")).toBeInTheDocument();
    expect(mockDeck).toHaveBeenCalledWith(2, expect.anything());

    fireEvent.click(within(row).getByTestId("meta-deck-toggle"));
    expect(within(row).queryByTestId("meta-deck-detail")).not.toBeInTheDocument();
  });

  it("detail failure shows inline message while the list stays visible", async () => {
    mockDecks.mockResolvedValue(ok(listResponse()));
    mockDeck.mockResolvedValue(fail("detail down"));
    renderPanel();
    const row = await screen.findByTestId("meta-deck-row-1");
    fireEvent.click(within(row).getByTestId("meta-deck-toggle"));
    expect(await within(row).findByTestId("meta-deck-detail-error")).toBeInTheDocument();
    expect(screen.getByTestId("meta-decks-list")).toBeInTheDocument();
    expect(screen.getByTestId("meta-deck-row-3")).toBeInTheDocument();
    expect(screen.queryByTestId("error-banner")).not.toBeInTheDocument();
  });
});
