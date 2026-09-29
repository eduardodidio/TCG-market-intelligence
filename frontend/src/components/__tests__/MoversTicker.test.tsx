import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MoversTicker } from "../MoversTicker";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual =
    await vi.importActual<typeof import("react-router-dom")>(
      "react-router-dom",
    );
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const translations: Record<string, string> = {
        "movers.tickerAriaLabel":
          "Collection movers ticker showing price changes",
      };
      return translations[key] || key;
    },
    i18n: { language: "en" },
  }),
}));

const mockFetchCollectionMovers = vi.fn();
vi.mock("../../api/collection", () => ({
  fetchCollectionMovers: (...args: unknown[]) =>
    mockFetchCollectionMovers(...args),
}));

const sampleGainers = [
  {
    card_id: 1,
    card_name: "Black Lotus",
    set_code: "lea",
    image_uri: null,
    price_start: 100,
    price_end: 120,
    change_abs: 20,
    change_pct: 20.0,
  },
  {
    card_id: 2,
    card_name: "Mox Ruby",
    set_code: "lea",
    image_uri: null,
    price_start: 50,
    price_end: 60,
    change_abs: 10,
    change_pct: 20.0,
  },
];

const sampleLosers = [
  {
    card_id: 3,
    card_name: "Shivan Dragon",
    set_code: "lea",
    image_uri: null,
    price_start: 30,
    price_end: 24,
    change_abs: -6,
    change_pct: -20.0,
  },
  {
    card_id: 4,
    card_name: "Serra Angel",
    set_code: "lea",
    image_uri: null,
    price_start: 20,
    price_end: 16,
    change_abs: -4,
    change_pct: -20.0,
  },
];

describe("MoversTicker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders ticker with interleaved gainers and losers", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: sampleGainers,
        losers: sampleLosers,
        period_days: 7,
      },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(screen.getByTestId("movers-ticker")).toBeInTheDocument(),
    );

    // All card names should appear (doubled for seamless loop)
    const items = screen.getAllByTestId("movers-ticker-item");
    // 4 items interleaved, doubled = 8
    expect(items).toHaveLength(8);

    // Check interleave order: gainer1, loser1, gainer2, loser2, ...
    expect(items[0]).toHaveTextContent("Black Lotus");
    expect(items[1]).toHaveTextContent("Shivan Dragon");
    expect(items[2]).toHaveTextContent("Mox Ruby");
    expect(items[3]).toHaveTextContent("Serra Angel");
  });

  it("shows green for gainers and red for losers", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [sampleGainers[0]],
        losers: [sampleLosers[0]],
        period_days: 7,
      },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(screen.getByTestId("movers-ticker")).toBeInTheDocument(),
    );

    const items = screen.getAllByTestId("movers-ticker-item");
    // First item is gainer — should have green text
    const gainerPct = items[0].querySelector(".text-emerald-400");
    expect(gainerPct).toBeInTheDocument();
    expect(gainerPct).toHaveTextContent("+20.0%");

    // Second item is loser — should have red text
    const loserPct = items[1].querySelector(".text-red-400");
    expect(loserPct).toBeInTheDocument();
    expect(loserPct).toHaveTextContent("-20.0%");
  });

  it("returns null when data is empty", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: { gainers: [], losers: [], period_days: 7 },
      errors: [],
    });

    const { container } = render(<MoversTicker />);

    await waitFor(() =>
      expect(mockFetchCollectionMovers).toHaveBeenCalledTimes(1),
    );

    // Wait for loading to finish and confirm null render
    await waitFor(() =>
      expect(screen.queryByTestId("movers-ticker")).not.toBeInTheDocument(),
    );
    expect(container.innerHTML).toBe("");
  });

  it("returns null while loading", () => {
    // Never resolve the promise — stays in loading state
    mockFetchCollectionMovers.mockReturnValue(new Promise(() => {}));

    const { container } = render(<MoversTicker />);

    expect(screen.queryByTestId("movers-ticker")).not.toBeInTheDocument();
    expect(container.innerHTML).toBe("");
  });

  it("navigates to card detail on click", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [sampleGainers[0]],
        losers: [],
        period_days: 7,
      },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(screen.getByTestId("movers-ticker")).toBeInTheDocument(),
    );

    const items = screen.getAllByTestId("movers-ticker-item");
    fireEvent.click(items[0]);

    expect(mockNavigate).toHaveBeenCalledWith("/cards/1");
  });

  it("has correct CSS classes for hover pause", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [sampleGainers[0]],
        losers: [sampleLosers[0]],
        period_days: 7,
      },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(screen.getByTestId("movers-ticker")).toBeInTheDocument(),
    );

    // The inner div with animate-ticker class handles hover pause via CSS
    const ticker = screen.getByTestId("movers-ticker");
    const innerDiv = ticker.firstElementChild as HTMLElement;
    expect(innerDiv.className).toContain("animate-ticker");
  });

  it("has motion-reduce classes for accessibility", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [sampleGainers[0]],
        losers: [sampleLosers[0]],
        period_days: 7,
      },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(screen.getByTestId("movers-ticker")).toBeInTheDocument(),
    );

    const ticker = screen.getByTestId("movers-ticker");
    const innerDiv = ticker.firstElementChild as HTMLElement;
    expect(innerDiv.className).toContain("motion-reduce:animate-none");
    expect(innerDiv.className).toContain("motion-reduce:overflow-x-auto");
  });

  it("has role=marquee and aria-label", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [sampleGainers[0]],
        losers: [sampleLosers[0]],
        period_days: 7,
      },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(screen.getByTestId("movers-ticker")).toBeInTheDocument(),
    );

    const ticker = screen.getByTestId("movers-ticker");
    expect(ticker).toHaveAttribute("role", "marquee");
    expect(ticker).toHaveAttribute(
      "aria-label",
      "Collection movers ticker showing price changes",
    );
  });

  it("sets tabIndex=-1 on duplicated items to prevent double keyboard focus", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: {
        gainers: [sampleGainers[0]],
        losers: [sampleLosers[0]],
        period_days: 7,
      },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(screen.getByTestId("movers-ticker")).toBeInTheDocument(),
    );

    const items = screen.getAllByTestId("movers-ticker-item");
    // 2 original items + 2 duplicated = 4 total
    expect(items).toHaveLength(4);

    // First half (original items) should NOT have tabIndex=-1
    expect(items[0]).not.toHaveAttribute("tabindex", "-1");
    expect(items[1]).not.toHaveAttribute("tabindex", "-1");

    // Second half (duplicated items) SHOULD have tabIndex=-1
    expect(items[2]).toHaveAttribute("tabindex", "-1");
    expect(items[3]).toHaveAttribute("tabindex", "-1");
  });

  it("calls fetchCollectionMovers with correct params", async () => {
    mockFetchCollectionMovers.mockResolvedValue({
      data: { gainers: [], losers: [], period_days: 7 },
      errors: [],
    });

    render(<MoversTicker />);

    await waitFor(() =>
      expect(mockFetchCollectionMovers).toHaveBeenCalledWith(7, 10, true),
    );
  });
});
