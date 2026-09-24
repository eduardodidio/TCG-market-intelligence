import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { MetaDeckSummary } from "../../../types/metaDecks";
import { MetaDeckRow } from "../MetaDeckRow";
import { fail, makeCard, makeDeck, ok } from "./fixtures";

vi.mock("../../../api/metaDecks", () => ({
  fetchMetaFormats: vi.fn(),
  fetchMetaDecks: vi.fn(),
  fetchMetaDeck: vi.fn(),
}));

import { fetchMetaDeck } from "../../../api/metaDecks";

const mockFetchMetaDeck = vi.mocked(fetchMetaDeck);

function renderRow(deck: MetaDeckSummary, expanded = false, onToggle = vi.fn()) {
  const utils = render(
    <MemoryRouter>
      <MetaDeckRow deck={deck} expanded={expanded} onToggle={onToggle} />
    </MemoryRouter>,
  );
  const rerender = (nextExpanded: boolean) =>
    utils.rerender(
      <MemoryRouter>
        <MetaDeckRow deck={deck} expanded={nextExpanded} onToggle={onToggle} />
      </MemoryRouter>,
    );
  return { ...utils, rerender, onToggle };
}

describe("MetaDeckRow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders rank, name, colors, meta share, BRL value, owned bar and missing value", () => {
    renderRow(makeDeck());
    expect(screen.getByTestId("meta-deck-rank")).toHaveTextContent("#1");
    expect(screen.getByTestId("meta-deck-name")).toHaveTextContent("Boros Energy");
    expect(screen.getByTestId("meta-deck-color-W")).toBeInTheDocument();
    expect(screen.getByTestId("meta-deck-color-R")).toBeInTheDocument();
    expect(screen.getByTestId("meta-deck-share")).toHaveTextContent("12.5");
    expect(screen.queryByTestId("meta-deck-count")).not.toBeInTheDocument();
    expect(screen.getByTestId("meta-deck-value").textContent).toMatch(/R\$\s*1\.234,50/);
    expect(screen.getByTestId("meta-owned-bar")).toHaveStyle({ width: "40%" });
    expect(screen.getByTestId("meta-deck-missing").textContent).toMatch(/R\$\s*700,00/);
    expect(screen.queryByTestId("meta-owned-login-cta")).not.toBeInTheDocument();
    expect(mockFetchMetaDeck).not.toHaveBeenCalled();
  });

  it("uses commander name and deck count for Commander decks without meta share", () => {
    renderRow(
      makeDeck({ commander_name: "Atraxa, Grand Unifier", meta_share_pct: null, deck_count: 321 }),
    );
    expect(screen.getByTestId("meta-deck-name")).toHaveTextContent("Atraxa, Grand Unifier");
    expect(screen.getByTestId("meta-deck-count")).toHaveTextContent("321");
    expect(screen.queryByTestId("meta-deck-share")).not.toBeInTheDocument();
  });

  it("hides owned bar and shows login CTA when owned_pct is null", () => {
    renderRow(makeDeck({ owned_pct: null, missing_value_brl: null }));
    expect(screen.queryByTestId("meta-owned-bar")).not.toBeInTheDocument();
    expect(screen.queryByTestId("meta-deck-missing")).not.toBeInTheDocument();
    expect(screen.getByTestId("meta-owned-login-cta")).toBeInTheDocument();
  });

  it("shows — when total_value_brl is null", () => {
    renderRow(makeDeck({ total_value_brl: null }));
    expect(screen.getByTestId("meta-deck-value")).toHaveTextContent("—");
  });

  it("clamps owned bar width to 0..100", () => {
    renderRow(makeDeck({ owned_pct: 150 }));
    expect(screen.getByTestId("meta-owned-bar")).toHaveStyle({ width: "100%" });
  });

  it("renders colorless pip when colors is null", () => {
    renderRow(makeDeck({ colors: null }));
    expect(screen.getByTestId("meta-deck-color-C")).toBeInTheDocument();
  });

  it("external source link is safe", () => {
    renderRow(makeDeck());
    const link = screen.getByTestId("meta-deck-source-link");
    expect(link).toHaveAttribute("href", "https://example.com/deck/1");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("clicking the row calls onToggle", () => {
    const { onToggle } = renderRow(makeDeck());
    fireEvent.click(screen.getByTestId("meta-deck-toggle"));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("when expanded, lazily loads and renders the decklist once", async () => {
    mockFetchMetaDeck.mockResolvedValue(
      ok({ ...makeDeck(), cards: [makeCard({ name: "Lightning Bolt" })] }),
    );
    const { rerender } = renderRow(makeDeck(), true);
    expect(screen.getByTestId("meta-deck-detail-loading")).toBeInTheDocument();
    expect(await screen.findByTestId("meta-card-list")).toBeInTheDocument();
    expect(mockFetchMetaDeck).toHaveBeenCalledWith(1, expect.objectContaining({ signal: expect.anything() }));

    rerender(false);
    expect(screen.queryByTestId("meta-deck-detail")).not.toBeInTheDocument();
    rerender(true);
    expect(screen.getByTestId("meta-card-list")).toBeInTheDocument();
    expect(mockFetchMetaDeck).toHaveBeenCalledTimes(1);
  });

  it("detail failure shows inline error and retry refetches", async () => {
    mockFetchMetaDeck.mockResolvedValueOnce(fail("detail down"));
    renderRow(makeDeck(), true);
    const err = await screen.findByTestId("meta-deck-detail-error");
    expect(err).toHaveTextContent("detail down");

    mockFetchMetaDeck.mockResolvedValueOnce(ok({ ...makeDeck(), cards: [makeCard()] }));
    fireEvent.click(screen.getByTestId("meta-deck-detail-retry"));
    await waitFor(() => expect(screen.getByTestId("meta-card-list")).toBeInTheDocument());
    expect(mockFetchMetaDeck).toHaveBeenCalledTimes(2);
  });

  it("detail rejection (network) shows inline error", async () => {
    mockFetchMetaDeck.mockRejectedValueOnce(new Error("socket closed"));
    renderRow(makeDeck(), true);
    expect(await screen.findByTestId("meta-deck-detail-error")).toHaveTextContent("socket closed");
  });
});
