import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { TopDecksPreview } from "../TopDecksPreview";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

const mockApiGet = vi.fn();
vi.mock("../../api/client", () => ({
  apiGet: (...args: unknown[]) => mockApiGet(...args),
}));

vi.mock("../DeckSparkline", () => ({
  DeckSparkline: () => <div data-testid="sparkline-stub" />,
}));

function renderPreview() {
  return render(
    <MemoryRouter>
      <TopDecksPreview period="30d" currency="BRL" />
    </MemoryRouter>,
  );
}

const deck = {
  id: 7,
  name: "Atraxa",
  total_value: 1234.5,
  value_change_pct: 2.5,
  sparkline: [],
};

describe("TopDecksPreview meta link", () => {
  beforeEach(() => {
    mockApiGet.mockReset();
  });

  it("shows the metagame link pointing to /decks/ranking?view=meta when decks exist", async () => {
    mockApiGet.mockResolvedValue({ data: { decks: [deck], total: 1 }, errors: [] });
    renderPreview();
    const link = await screen.findByTestId("top-decks-preview-meta-link");
    expect(link).toHaveAttribute("href", "/decks/ranking?view=meta");
    expect(screen.getByText("Atraxa")).toBeInTheDocument();
  });

  it("still renders nothing when the user has no decks", async () => {
    mockApiGet.mockResolvedValue({ data: { decks: [], total: 0 }, errors: [] });
    const { container } = renderPreview();
    await vi.waitFor(() => expect(mockApiGet).toHaveBeenCalled());
    await vi.waitFor(() => expect(container.querySelector("[data-testid='top-decks-preview']")).toBeNull());
    expect(screen.queryByTestId("top-decks-preview-meta-link")).not.toBeInTheDocument();
  });
});
