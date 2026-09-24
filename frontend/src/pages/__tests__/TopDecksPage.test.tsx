import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { TopDecksPage } from "../TopDecksPage";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

const mockFetchDeckRanking = vi.fn();
vi.mock("../../api/deckRanking", () => ({
  fetchDeckRanking: (...args: unknown[]) => mockFetchDeckRanking(...args),
}));

vi.mock("../../components/meta/MetaDecksPanel", () => ({
  MetaDecksPanel: ({
    format,
    onFormatChange,
  }: {
    format: string;
    onFormatChange: (f: string) => void;
  }) => (
    <div data-testid="meta-panel-stub">
      <span data-testid="meta-panel-format">{format}</span>
      <button data-testid="meta-panel-pick-pauper" onClick={() => onFormatChange("pauper")}>
        pauper
      </button>
    </div>
  ),
}));

function LocationProbe() {
  const location = useLocation();
  return <div data-testid="location-search">{location.search}</div>;
}

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <TopDecksPage />
      <LocationProbe />
    </MemoryRouter>,
  );
}

function searchParams(): URLSearchParams {
  return new URLSearchParams(screen.getByTestId("location-search").textContent ?? "");
}

describe("TopDecksPage tabs", () => {
  beforeEach(() => {
    mockFetchDeckRanking.mockReset();
    mockFetchDeckRanking.mockResolvedValue({
      data: { decks: [], total: 0 },
      errors: [],
    });
  });

  it("defaults to the user's ranking and fetches it", async () => {
    renderAt("/decks/ranking");
    await waitFor(() => expect(mockFetchDeckRanking).toHaveBeenCalledTimes(1));
    expect(mockFetchDeckRanking).toHaveBeenCalledWith(
      expect.objectContaining({ sort_by: "total_value", period: "30d", offset: 0 }),
    );
    expect(screen.getByTestId("topdecks-tab-mine")).toHaveAttribute("aria-selected", "true");
    expect(screen.getByTestId("topdecks-tab-meta")).toHaveAttribute("aria-selected", "false");
    expect(screen.getByTestId("sort-select")).toBeInTheDocument();
    expect(screen.getByTestId("period-selector")).toBeInTheDocument();
    expect(screen.queryByTestId("meta-panel-stub")).not.toBeInTheDocument();
    expect(await screen.findByTestId("ranking-empty")).toBeInTheDocument();
  });

  it("switching to the Mercado tab sets view=meta, renders the panel, and preserves other params", async () => {
    renderAt("/decks/ranking?sort_by=card_count&period=7d");
    await waitFor(() => expect(mockFetchDeckRanking).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByTestId("topdecks-tab-meta"));

    expect(screen.getByTestId("meta-panel-stub")).toBeInTheDocument();
    expect(screen.getByTestId("meta-panel-format")).toHaveTextContent("commander");
    expect(screen.getByTestId("topdecks-tab-meta")).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByTestId("sort-select")).not.toBeInTheDocument();
    expect(screen.queryByTestId("period-selector")).not.toBeInTheDocument();
    expect(screen.getByText("Top Decks do Mercado")).toBeInTheDocument();

    const params = searchParams();
    expect(params.get("view")).toBe("meta");
    expect(params.get("sort_by")).toBe("card_count");
    expect(params.get("period")).toBe("7d");
    expect(mockFetchDeckRanking).toHaveBeenCalledTimes(1);
  });

  it("deep-link view=meta&format=modern renders the panel with modern and never fetches the ranking", () => {
    renderAt("/decks/ranking?view=meta&format=modern");
    expect(screen.getByTestId("meta-panel-format")).toHaveTextContent("modern");
    expect(mockFetchDeckRanking).not.toHaveBeenCalled();
  });

  it("view=meta without format defaults to commander", () => {
    renderAt("/decks/ranking?view=meta");
    expect(screen.getByTestId("meta-panel-format")).toHaveTextContent("commander");
  });

  it("invalid format in URL falls back to commander", () => {
    renderAt("/decks/ranking?view=meta&format=brawl");
    expect(screen.getByTestId("meta-panel-format")).toHaveTextContent("commander");
  });

  it("onFormatChange updates format in the URL", () => {
    renderAt("/decks/ranking?view=meta&format=modern");
    fireEvent.click(screen.getByTestId("meta-panel-pick-pauper"));
    expect(searchParams().get("format")).toBe("pauper");
    expect(searchParams().get("view")).toBe("meta");
    expect(screen.getByTestId("meta-panel-format")).toHaveTextContent("pauper");
  });

  it("unknown view is treated as mine", async () => {
    renderAt("/decks/ranking?view=xyz");
    await waitFor(() => expect(mockFetchDeckRanking).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId("topdecks-tab-mine")).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByTestId("meta-panel-stub")).not.toBeInTheDocument();
  });

  it("switching back to mine re-renders the ranking and keeps format in the URL", async () => {
    renderAt("/decks/ranking?view=meta&format=legacy");
    expect(mockFetchDeckRanking).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("topdecks-tab-mine"));
    await waitFor(() => expect(mockFetchDeckRanking).toHaveBeenCalledTimes(1));
    expect(searchParams().get("view")).toBe("mine");
    expect(searchParams().get("format")).toBe("legacy");
    expect(screen.getByTestId("sort-select")).toBeInTheDocument();
  });
});
