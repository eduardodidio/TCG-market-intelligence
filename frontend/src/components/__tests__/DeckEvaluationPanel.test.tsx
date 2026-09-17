import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { DeckEvaluationPanel } from "../DeckEvaluationPanel";
import type { DeckEvaluation } from "../../types/api";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

// Mock recharts to avoid rendering issues in tests
vi.mock("recharts", () => ({
  BarChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="bar-chart">{children}</div>
  ),
  Bar: () => <div data-testid="bar" />,
  XAxis: () => <div />,
  YAxis: () => <div />,
  Tooltip: () => <div />,
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  ),
  PieChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="pie-chart">{children}</div>
  ),
  Pie: () => <div data-testid="pie" />,
  Cell: () => <div />,
  Legend: () => <div />,
}));

const mockEvaluation: DeckEvaluation = {
  deck_id: 1,
  mana_curve: [
    { cmc: 1, count: 10 },
    { cmc: 2, count: 15 },
    { cmc: 3, count: 8 },
  ],
  type_distribution: [
    { type_name: "Creature", count: 30 },
    { type_name: "Instant", count: 10 },
    { type_name: "Land", count: 37 },
  ],
  color_distribution: [
    { color: "U", pip_count: 20 },
    { color: "W", pip_count: 15 },
  ],
  land_count: 37,
  nonland_count: 63,
  total_cards: 100,
  avg_cmc: 2.85,
  color_identity: ["U", "W"],
  legality: {
    format: "commander",
    is_legal: true,
    illegal_cards: [],
    singleton_violations: [],
    card_count_valid: true,
  },
  budget: {
    total_value: 450.0,
    most_expensive: [
      { name_en: "Mana Crypt", price: 120.0, quantity: 1 },
      { name_en: "Cyclonic Rift", price: 80.0, quantity: 1 },
    ],
    price_tiers: { budget: 30, mid: 20, premium: 8, chase: 5 },
  },
  suggestions: ["Consider adding more card draw."],
};

let mockFetchResult: { data: DeckEvaluation | null; errors: { message: string }[] };

const mockFetchDeckEvaluation = vi.fn(() => Promise.resolve(mockFetchResult));

vi.mock("../../api/decks", () => ({
  fetchDeckEvaluation: (...args: unknown[]) => mockFetchDeckEvaluation(...args),
}));

describe("DeckEvaluationPanel", () => {
  beforeEach(() => {
    mockFetchResult = { data: mockEvaluation, errors: [] };
    mockFetchDeckEvaluation.mockClear();
    mockFetchDeckEvaluation.mockImplementation(() => Promise.resolve(mockFetchResult));
  });

  it("renders loading skeleton initially", () => {
    // Make the fetch never resolve to keep loading state
    mockFetchDeckEvaluation.mockReturnValue(new Promise(() => {}));

    render(<DeckEvaluationPanel deckId={1} />);
    expect(screen.getByTestId("evaluation-loading")).toBeInTheDocument();
  });

  it("renders mana curve chart section", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("mana-curve-section")).toBeInTheDocument();
    });
    expect(screen.getByTestId("avg-cmc")).toHaveTextContent("2.85");
  });

  it("renders type distribution pie chart", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("type-dist-section")).toBeInTheDocument();
    });
  });

  it("renders color distribution", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("color-dist-section")).toBeInTheDocument();
    });
  });

  it("renders legality badge (legal)", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("legality-badge-legal")).toBeInTheDocument();
    });
  });

  it("renders legality badge (illegal)", async () => {
    mockFetchResult = {
      data: {
        ...mockEvaluation,
        legality: {
          format: "standard",
          is_legal: false,
          illegal_cards: [{ name_en: "Sol Ring", status: "not_legal" }],
          singleton_violations: [],
          card_count_valid: true,
        },
      },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(
        screen.getByTestId("legality-badge-illegal"),
      ).toBeInTheDocument();
    });
    expect(screen.getByTestId("illegal-cards-list")).toBeInTheDocument();
  });

  it("renders budget section with total value", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("budget-section")).toBeInTheDocument();
    });
    expect(screen.getByTestId("budget-total-value")).toHaveTextContent(
      "R$ 450.00",
    );
  });

  it("renders most expensive cards list", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(
        screen.getByTestId("expensive-cards-list"),
      ).toBeInTheDocument();
    });
  });

  it("renders suggestions section", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("suggestions-section")).toBeInTheDocument();
    });
  });

  it("renders error state", async () => {
    mockFetchResult = {
      data: null,
      errors: [{ message: "Something went wrong" }],
    };

    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("evaluation-error")).toBeInTheDocument();
    });
  });

  it("shows format selector and responds to changes", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("format-selector")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByTestId("format-selector"), {
      target: { value: "standard" },
    });

    // Should trigger a new fetch with "standard"
    await waitFor(() => {
      const calls = mockFetchDeckEvaluation.mock.calls;
      const lastCall = calls[calls.length - 1];
      expect(lastCall[1]).toBe("standard");
    });
  });

  it("renders composition stats", async () => {
    render(<DeckEvaluationPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("eval-total-cards")).toHaveTextContent("100");
    });
    expect(screen.getByTestId("eval-land-count")).toHaveTextContent("37");
    expect(screen.getByTestId("eval-nonland-count")).toHaveTextContent("63");
  });
});
