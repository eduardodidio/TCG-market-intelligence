import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { GoldfishPanel } from "../GoldfishPanel";
import type { GoldfishResult } from "../../types/api";

// Mock react-i18next
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) =>
      (opts?.defaultValue as string) ?? key,
  }),
}));

// Mock recharts to avoid rendering issues in tests
vi.mock("recharts", () => ({
  LineChart: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="line-chart">{children}</div>
  ),
  Line: () => <div data-testid="line" />,
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
}));

const mockGoldfishResult: GoldfishResult = {
  deck_id: 1,
  opening_hand_quality: 0.78,
  avg_mana_by_turn: [1.2, 2.1, 2.9, 3.5, 4.1, 4.8, 5.3],
  mana_screw_rate: 0.12,
  mana_flood_rate: 0.08,
  avg_spells_cast_by_turn: [0.8, 1.2, 1.5, 1.8, 2.0, 2.1, 2.3],
  sample_hands: [
    {
      cards: ["Sol Ring", "Command Tower", "Arcane Signet", "Lightning Bolt", "Counterspell", "Island", "Mountain"],
      quality: 0.92,
      land_count: 3,
    },
    {
      cards: ["Forest", "Plains", "Swamp", "Dark Ritual", "Mana Crypt", "Brainstorm", "Ponder"],
      quality: 0.65,
      land_count: 3,
    },
    {
      cards: ["Mountain", "Mountain", "Mountain", "Forest", "Forest", "Island", "Swamp"],
      quality: 0.15,
      land_count: 7,
    },
  ],
  total_simulations: 100,
  total_turns: 7,
};

let mockFetchResult: { data: GoldfishResult | null; errors: { message: string }[] };

const mockFetchGoldfish = vi.fn((_deckId: number) => Promise.resolve(mockFetchResult));

vi.mock("../../api/decks", () => ({
  fetchGoldfish: (deckId: number) => mockFetchGoldfish(deckId),
}));

describe("GoldfishPanel", () => {
  beforeEach(() => {
    mockFetchResult = { data: mockGoldfishResult, errors: [] };
    mockFetchGoldfish.mockClear();
    mockFetchGoldfish.mockImplementation(() => Promise.resolve(mockFetchResult));
  });

  it("renders loading skeleton initially", () => {
    // Make the fetch never resolve to keep loading state
    mockFetchGoldfish.mockReturnValue(new Promise(() => {}));

    render(<GoldfishPanel deckId={1} />);
    expect(screen.getByTestId("goldfish-loading")).toBeInTheDocument();
  });

  it("renders opening hand quality with correct percentage", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("opening-hand-quality-section")).toBeInTheDocument();
    });
    expect(screen.getByTestId("quality-value")).toHaveTextContent("78%");
  });

  it("renders screw and flood rate badges", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("screw-flood-section")).toBeInTheDocument();
    });
    expect(screen.getByTestId("screw-rate-badge")).toHaveTextContent("12%");
    expect(screen.getByTestId("flood-rate-badge")).toHaveTextContent("8%");
  });

  it("renders mana by turn chart section", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("mana-by-turn-section")).toBeInTheDocument();
    });
    expect(screen.getByTestId("line-chart")).toBeInTheDocument();
  });

  it("renders spells by turn chart section", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("spells-by-turn-section")).toBeInTheDocument();
    });
    expect(screen.getByTestId("bar-chart")).toBeInTheDocument();
  });

  it("renders sample hands with card names", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("sample-hands-section")).toBeInTheDocument();
    });
    // Should see card names from the best hand
    expect(screen.getByText("Sol Ring")).toBeInTheDocument();
    expect(screen.getByText("Command Tower")).toBeInTheDocument();
    // Should see card names from the worst hand
    expect(screen.getAllByText("Mountain").length).toBeGreaterThan(0);
  });

  it("renders 3 sample hands (best, median, worst)", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("sample-hands-section")).toBeInTheDocument();
    });
    // Best hand
    expect(screen.getByTestId("sample-hand-decks.goldfish.besthand")).toBeInTheDocument();
    // Median hand
    expect(screen.getByTestId("sample-hand-decks.goldfish.medianhand")).toBeInTheDocument();
    // Worst hand
    expect(screen.getByTestId("sample-hand-decks.goldfish.worsthand")).toBeInTheDocument();
  });

  it("simulate again button triggers re-fetch", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("simulate-again-btn")).toBeInTheDocument();
    });

    expect(mockFetchGoldfish).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByTestId("simulate-again-btn"));

    await waitFor(() => {
      expect(mockFetchGoldfish).toHaveBeenCalledTimes(2);
    });
  });

  it("shows loading state during re-simulation", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("goldfish-panel")).toBeInTheDocument();
    });

    // Make next fetch hang
    mockFetchGoldfish.mockReturnValue(new Promise(() => {}));
    fireEvent.click(screen.getByTestId("simulate-again-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("goldfish-loading")).toBeInTheDocument();
    });
  });

  it("renders error state with retry", async () => {
    mockFetchResult = {
      data: null,
      errors: [{ message: "Something went wrong" }],
    };

    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      // ErrorBanner should be visible
      expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    });
  });

  it("displays simulation info text", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      expect(screen.getByTestId("simulation-info")).toBeInTheDocument();
    });
  });

  it("renders green badge for low screw rate", async () => {
    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      const badge = screen.getByTestId("screw-rate-badge");
      expect(badge.className).toContain("bg-green-900/30");
    });
  });

  it("renders red badge for high screw rate", async () => {
    mockFetchResult = {
      data: {
        ...mockGoldfishResult,
        mana_screw_rate: 0.35,
      },
      errors: [],
    };

    render(<GoldfishPanel deckId={1} />);
    await waitFor(() => {
      const badge = screen.getByTestId("screw-rate-badge");
      expect(badge.className).toContain("bg-red-900/30");
    });
  });

  it("calls fetchGoldfish with the correct deck id", async () => {
    render(<GoldfishPanel deckId={42} />);
    await waitFor(() => {
      expect(mockFetchGoldfish).toHaveBeenCalledWith(42);
    });
  });
});
