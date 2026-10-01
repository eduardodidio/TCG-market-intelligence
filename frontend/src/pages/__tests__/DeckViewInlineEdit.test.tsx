import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { DeckView } from "../DeckView";
import * as decksApi from "../../api/decks";
import type { DeckDetail } from "../../types/api";

vi.mock("../../api/decks", () => ({
  fetchDeck: vi.fn(),
  deleteDeck: vi.fn(),
  updateDeck: vi.fn(),
}));

vi.mock("../../api/deckRanking", () => ({
  fetchDeckValue: vi.fn().mockResolvedValue({ data: null, errors: [] }),
}));

vi.mock("../../api/collection", () => ({
  refreshCardPriceLiga: vi.fn(),
}));

vi.mock("recharts", () => ({
  AreaChart: () => null,
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  Tooltip: () => null,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
}));

vi.mock("../../components/DeckEvaluationPanel", () => ({
  DeckEvaluationPanel: () => <div data-testid="mock-eval-panel" />,
}));

vi.mock("../../components/GoldfishPanel", () => ({
  GoldfishPanel: () => <div data-testid="mock-goldfish-panel" />,
}));

const mockDeck: DeckDetail = {
  id: 1,
  name: "My EDH Deck",
  description: "A commander deck",
  cards: [],
  total_cards: 100,
  unique_cards: 60,
  owned_cards: 50,
  ownership_pct: 83,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderDeckView() {
  return render(
    <MemoryRouter initialEntries={["/decks/1"]}>
      <Routes>
        <Route path="/decks/:id" element={<DeckView />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("DeckView inline edit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(decksApi.fetchDeck).mockResolvedValue({
      data: mockDeck,
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });
    vi.mocked(decksApi.updateDeck).mockResolvedValue({
      data: mockDeck,
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });
  });

  it("renders deck title as clickable text", async () => {
    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-title")).toBeInTheDocument();
    });
    expect(screen.getByTestId("deck-title")).toHaveTextContent("My EDH Deck");
  });

  it("clicking name activates edit mode", async () => {
    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-title")).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId("deck-title"));
    expect(screen.getByTestId("deck-title-input")).toBeInTheDocument();
    expect(screen.getByTestId("deck-title-input")).toHaveValue("My EDH Deck");
  });

  it("pressing Enter saves name and exits edit mode", async () => {
    vi.mocked(decksApi.updateDeck).mockResolvedValue({
      data: { ...mockDeck, name: "New Name" },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-title")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("deck-title"));
    const input = screen.getByTestId("deck-title-input");
    fireEvent.change(input, { target: { value: "New Name" } });
    fireEvent.keyDown(input, { key: "Enter" });

    await waitFor(() => {
      expect(decksApi.updateDeck).toHaveBeenCalledWith(1, { name: "New Name" });
    });
    expect(screen.queryByTestId("deck-title-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("deck-title")).toHaveTextContent("New Name");
  });

  it("pressing Escape reverts name and exits edit mode", async () => {
    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-title")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("deck-title"));
    const input = screen.getByTestId("deck-title-input");
    fireEvent.change(input, { target: { value: "Changed Name" } });
    fireEvent.keyDown(input, { key: "Escape" });

    expect(screen.queryByTestId("deck-title-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("deck-title")).toHaveTextContent("My EDH Deck");
    expect(decksApi.updateDeck).not.toHaveBeenCalled();
  });

  it("renders deck description as clickable text", async () => {
    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-description")).toBeInTheDocument();
    });
    expect(screen.getByTestId("deck-description")).toHaveTextContent("A commander deck");
  });

  it("clicking description activates edit mode", async () => {
    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-description")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("deck-description"));
    expect(screen.getByTestId("deck-description-input")).toBeInTheDocument();
    expect(screen.getByTestId("deck-description-input")).toHaveValue("A commander deck");
  });

  it("pressing Enter in description saves and exits edit mode", async () => {
    vi.mocked(decksApi.updateDeck).mockResolvedValue({
      data: { ...mockDeck, description: "Updated desc" },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-description")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("deck-description"));
    const textarea = screen.getByTestId("deck-description-input");
    fireEvent.change(textarea, { target: { value: "Updated desc" } });
    fireEvent.keyDown(textarea, { key: "Enter" });

    await waitFor(() => {
      expect(decksApi.updateDeck).toHaveBeenCalledWith(1, {
        description: "Updated desc",
      });
    });
  });

  it("pressing Escape in description reverts and exits edit mode", async () => {
    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-description")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("deck-description"));
    const textarea = screen.getByTestId("deck-description-input");
    fireEvent.change(textarea, { target: { value: "Changed" } });
    fireEvent.keyDown(textarea, { key: "Escape" });

    expect(screen.queryByTestId("deck-description-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("deck-description")).toHaveTextContent("A commander deck");
    expect(decksApi.updateDeck).not.toHaveBeenCalled();
  });

  it("shows add description placeholder when no description", async () => {
    vi.mocked(decksApi.fetchDeck).mockResolvedValue({
      data: { ...mockDeck, description: null },
      meta: { cursor: null, total: null, offset: null, request_id: "r1" },
      errors: [],
    });

    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-description")).toBeInTheDocument();
    });
    expect(screen.getByTestId("deck-description")).toHaveTextContent("Add description...");
  });

  it("does not call updateDeck when name unchanged", async () => {
    renderDeckView();
    await waitFor(() => {
      expect(screen.getByTestId("deck-title")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId("deck-title"));
    const input = screen.getByTestId("deck-title-input");
    // Don't change the value, just blur
    fireEvent.blur(input);

    expect(decksApi.updateDeck).not.toHaveBeenCalled();
  });
});
