import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import DashboardV2 from "../../src/pages/DashboardV2";
import {
  mockCollectionSummary,
  mockApiError,
} from "../fixtures/api-responses";

// Mock CardImage to avoid image loading complexity in tests
vi.mock("../../src/components/CardImage", () => ({
  CardImage: ({ alt, className }: { alt: string; className?: string; src: string | null }) => (
    <div data-testid="card-image-mock" className={className}>
      {alt}
    </div>
  ),
}));

function renderDashboard() {
  return render(
    <MemoryRouter>
      <DashboardV2 />
    </MemoryRouter>,
  );
}

function makeMoverData(overrides?: {
  gainers?: Array<{
    card_id: number;
    card_name: string;
    set_code: string | null;
    image_uri: string | null;
    price_start: number;
    price_end: number;
    change_abs: number;
    change_pct: number;
  }>;
  losers?: Array<{
    card_id: number;
    card_name: string;
    set_code: string | null;
    image_uri: string | null;
    price_start: number;
    price_end: number;
    change_abs: number;
    change_pct: number;
  }>;
}) {
  return {
    data: {
      gainers: overrides?.gainers ?? [
        {
          card_id: 1,
          card_name: "Lightning Bolt",
          set_code: "DMR",
          image_uri: "https://example.com/bolt.jpg",
          price_start: 10,
          price_end: 15,
          change_abs: 5,
          change_pct: 50.0,
        },
        {
          card_id: 2,
          card_name: "Counterspell",
          set_code: "MH2",
          image_uri: null,
          price_start: 20,
          price_end: 28,
          change_abs: 8,
          change_pct: 40.0,
        },
      ],
      losers: overrides?.losers ?? [
        {
          card_id: 3,
          card_name: "Dark Ritual",
          set_code: "A25",
          image_uri: "https://example.com/ritual.jpg",
          price_start: 15,
          price_end: 10,
          change_abs: -5,
          change_pct: -33.3,
        },
      ],
      period_days: 7,
    },
    meta: { cursor: null, total: null, offset: null, request_id: "req-test" },
    errors: [],
  };
}

function makePortfolioData() {
  return {
    data: {
      total_invested: 500,
      total_current_value: 750,
      total_pnl: 250,
      total_pnl_pct: 50.0,
      invested_card_count: 10,
    },
    meta: { cursor: null, total: null, offset: null, request_id: "req-test" },
    errors: [],
  };
}

function makeSetCompletionData() {
  return {
    data: [
      { set_code: "DMR", set_name: "Dominaria Remastered", owned: 50, total: 261 },
      { set_code: "MH2", set_name: "Modern Horizons 2", owned: 100, total: 303 },
      { set_code: "2X2", set_name: "Double Masters 2022", owned: 10, total: 332 },
    ],
    meta: { cursor: null, total: null, offset: null, request_id: "req-test" },
    errors: [],
  };
}

describe("DashboardV2", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  function mockAllSuccess() {
    const summaryResponse = mockCollectionSummary();
    const moversResponse = makeMoverData();
    const portfolioResponse = makePortfolioData();
    const setCompletionResponse = makeSetCompletionData();

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(summaryResponse),
          });
        }
        if (urlStr.includes("/collection/movers")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(moversResponse),
          });
        }
        if (urlStr.includes("/collection/portfolio-summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(portfolioResponse),
          });
        }
        if (urlStr.includes("/collection/set-completion")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(setCompletionResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: {}, errors: [] }),
        });
      },
    );
  }

  function mockSummaryError() {
    const errorResponse = mockApiError("SERVER_ERROR", "Internal server error");
    const moversResponse = makeMoverData({ gainers: [], losers: [] });

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: "Internal Server Error",
            json: () => Promise.resolve(errorResponse),
          });
        }
        if (urlStr.includes("/collection/movers")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(moversResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: {}, errors: [] }),
        });
      },
    );
  }

  it("renders portfolio hero with total value", async () => {
    mockAllSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("portfolio-hero")).toBeDefined();
    });

    const valueEl = screen.getByTestId("portfolio-value");
    expect(valueEl.textContent).toContain("2");
    expect(valueEl.textContent).toContain("850");
  });

  it("renders portfolio PnL percentage", async () => {
    mockAllSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("portfolio-pnl")).toBeDefined();
    });

    const pnlEl = screen.getByTestId("portfolio-pnl");
    expect(pnlEl.textContent).toContain("+50.0%");
    expect(pnlEl.className).toContain("text-emerald-400");
  });

  it("renders stat cards with correct values", async () => {
    mockAllSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("stats-row")).toBeDefined();
    });

    // total_unique = 120
    expect(screen.getByTestId("stat-total-cards").textContent).toContain("120");
    // sets_count = 5
    expect(screen.getByTestId("stat-sets").textContent).toContain("5");
    // priced_count = 80
    expect(screen.getByTestId("stat-priced").textContent).toContain("80");
    // coverage = round(80/120 * 100) = 67%
    expect(screen.getByTestId("stat-coverage").textContent).toContain("67%");
  });

  it("renders gainers section with green percentages", async () => {
    mockAllSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("gainers-card")).toBeDefined();
    });

    expect(screen.getByText("Top Gainers")).toBeDefined();

    // Card names appear twice (CardImage alt + text label), use getAllByText
    expect(screen.getAllByText("Lightning Bolt").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("Counterspell").length).toBeGreaterThanOrEqual(1);

    const gainerPcts = screen.getAllByTestId("mover-pct-gainer");
    expect(gainerPcts.length).toBe(2);
    expect(gainerPcts[0].textContent).toContain("+50.0%");
    expect(gainerPcts[0].className).toContain("text-emerald-400");
  });

  it("renders losers section with red percentages", async () => {
    mockAllSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("losers-card")).toBeDefined();
    });

    expect(screen.getByText("Top Losers")).toBeDefined();
    expect(screen.getAllByText("Dark Ritual").length).toBeGreaterThanOrEqual(1);

    const loserPcts = screen.getAllByTestId("mover-pct-loser");
    expect(loserPcts.length).toBe(1);
    expect(loserPcts[0].textContent).toContain("-33.3%");
    expect(loserPcts[0].className).toContain("text-red-400");
  });

  it("shows 'No movers yet' when movers are empty", async () => {
    const summaryResponse = mockCollectionSummary();
    const emptyMovers = makeMoverData({ gainers: [], losers: [] });

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(summaryResponse),
          });
        }
        if (urlStr.includes("/collection/movers")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(emptyMovers),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: {}, errors: [] }),
        });
      },
    );

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("no-gainers")).toBeDefined();
    });

    expect(screen.getByTestId("no-losers")).toBeDefined();
  });

  it("shows error state with retry button on API failure", async () => {
    mockSummaryError();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-error")).toBeDefined();
    });

    expect(screen.getByText("Could not load collection data")).toBeDefined();
    expect(screen.getByTestId("retry-button")).toBeDefined();
  });

  it("retries fetch when retry button is clicked", async () => {
    mockSummaryError();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("dashboard-error")).toBeDefined();
    });

    // Now mock success for retry
    mockAllSuccess();
    fireEvent.click(screen.getByTestId("retry-button"));

    await waitFor(() => {
      expect(screen.getByTestId("portfolio-hero")).toBeDefined();
    });

    expect(screen.queryByTestId("dashboard-error")).toBeNull();
  });

  it("shows skeleton loading while data is being fetched", () => {
    (fetch as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));

    renderDashboard();

    expect(screen.getByTestId("skeleton-hero")).toBeDefined();
    const skeletons = screen.getAllByTestId("skeleton-stat");
    expect(skeletons.length).toBe(4);
  });

  it("renders set completion preview with progress bars", async () => {
    mockAllSuccess();
    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("set-completion-preview")).toBeDefined();
    });

    expect(screen.getByText("Set Completion")).toBeDefined();
    expect(screen.getByText("Dominaria Remastered")).toBeDefined();
    expect(screen.getByText("Modern Horizons 2")).toBeDefined();
    expect(screen.getByText("Double Masters 2022")).toBeDefined();

    const progressBars = screen.getAllByTestId("set-progress");
    expect(progressBars.length).toBe(3);
  });

  it("renders em dash when total_value is null", async () => {
    const nullValueSummary = mockCollectionSummary({ total_value: null });

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(nullValueSummary),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: {}, errors: [] }),
        });
      },
    );

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("portfolio-value")).toBeDefined();
    });

    expect(screen.getByTestId("portfolio-value").textContent).toContain("\u2014");
  });

  it("does not render set completion when data is empty", async () => {
    const summaryResponse = mockCollectionSummary();
    const emptySetCompletion = {
      data: [],
      meta: { cursor: null, total: null, offset: null, request_id: "req-test" },
      errors: [],
    };

    (fetch as ReturnType<typeof vi.fn>).mockImplementation(
      (url: string | URL) => {
        const urlStr = url.toString();
        if (urlStr.includes("/collection/summary")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(summaryResponse),
          });
        }
        if (urlStr.includes("/collection/set-completion")) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(emptySetCompletion),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ data: null, meta: {}, errors: [] }),
        });
      },
    );

    renderDashboard();

    await waitFor(() => {
      expect(screen.getByTestId("portfolio-hero")).toBeDefined();
    });

    expect(screen.queryByTestId("set-completion-preview")).toBeNull();
  });
});
