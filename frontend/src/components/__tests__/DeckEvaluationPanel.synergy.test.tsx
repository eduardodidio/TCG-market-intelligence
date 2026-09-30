import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { DeckEvaluationPanel } from "../DeckEvaluationPanel";
import type { DeckEvaluation } from "../../types/api";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

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

const baseMockEval: DeckEvaluation = {
  deck_id: 1,
  mana_curve: [{ cmc: 2, count: 10 }],
  type_distribution: [{ type_name: "Creature", count: 30 }],
  color_distribution: [{ color: "G", pip_count: 20 }],
  land_count: 37,
  nonland_count: 63,
  total_cards: 100,
  avg_cmc: 2.85,
  color_identity: ["G"],
  legality: null,
  budget: null,
  suggestions: [],
  synergy_score: null,
  role_coverage: [],
  tribal_density: null,
};

let mockFetchResult: { data: DeckEvaluation | null; errors: { message: string }[] };

const mockFetchDeckEvaluation = vi.fn(() => Promise.resolve(mockFetchResult));

vi.mock("../../api/decks", () => ({
  fetchDeckEvaluation: (...args: unknown[]) => mockFetchDeckEvaluation(...args),
}));

describe("DeckEvaluationPanel synergy features", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows synergy score section when synergy_score is present", async () => {
    mockFetchResult = {
      data: { ...baseMockEval, synergy_score: 0.65 },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("synergy-score-section")).toBeInTheDocument();
    });

    expect(screen.getByTestId("synergy-score-value")).toHaveTextContent("65%");
  });

  it("does not show synergy score section when null", async () => {
    mockFetchResult = {
      data: { ...baseMockEval, synergy_score: null },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("deck-evaluation-panel")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("synergy-score-section")).not.toBeInTheDocument();
  });

  it("shows tribal density when present", async () => {
    mockFetchResult = {
      data: { ...baseMockEval, synergy_score: 0.5, tribal_density: 0.75 },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("tribal-density-line")).toBeInTheDocument();
    });

    expect(screen.getByTestId("tribal-density-line")).toHaveTextContent("75%");
  });

  it("shows role coverage chart when roles present", async () => {
    mockFetchResult = {
      data: {
        ...baseMockEval,
        role_coverage: [
          { role: "draw", count: 10 },
          { role: "removal", count: 8 },
          { role: "ramp", count: 5 },
        ],
      },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("role-coverage-section")).toBeInTheDocument();
    });
  });

  it("does not show role coverage when empty", async () => {
    mockFetchResult = {
      data: { ...baseMockEval, role_coverage: [] },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("deck-evaluation-panel")).toBeInTheDocument();
    });

    expect(screen.queryByTestId("role-coverage-section")).not.toBeInTheDocument();
  });

  it("uses green color for high synergy score", async () => {
    mockFetchResult = {
      data: { ...baseMockEval, synergy_score: 0.8 },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("synergy-score-bar")).toBeInTheDocument();
    });

    const bar = screen.getByTestId("synergy-score-bar");
    expect(bar.className).toContain("bg-green-500");
  });

  it("uses red color for low synergy score", async () => {
    mockFetchResult = {
      data: { ...baseMockEval, synergy_score: 0.1 },
      errors: [],
    };

    render(<DeckEvaluationPanel deckId={1} />);

    await waitFor(() => {
      expect(screen.getByTestId("synergy-score-bar")).toBeInTheDocument();
    });

    const bar = screen.getByTestId("synergy-score-bar");
    expect(bar.className).toContain("bg-red-500");
  });
});
