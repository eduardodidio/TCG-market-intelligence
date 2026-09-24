import { render, screen } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import i18n from "i18next";
import { describe, it, expect, vi } from "vitest";
import type { ReactNode } from "react";
import { PriceChart, ChartTooltip } from "../PriceChart";
import type { ApiResponse, PriceHistoryMeta, PriceHistoryResponse, PriceObservation } from "../../types/api";

// Recharts does not render real dimensions in jsdom
vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => (
    <div data-testid="responsive-container">{children}</div>
  ),
  LineChart: ({ children }: { children: ReactNode }) => <div data-testid="line-chart">{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  Legend: () => null,
  Brush: () => null,
  ReferenceArea: () => null,
  ReferenceLine: () => null,
}));

function obs(date: string, source: string | null = "liga"): PriceObservation {
  return {
    observed_at: date,
    median_price: 10,
    tcg_price: null,
    last_sold_price: null,
    quantity_available: null,
    currency: "BRL",
    source,
  };
}

const META: PriceHistoryMeta = {
  variant: "foil",
  sources: ["liga", "daily_snapshot"],
  first_observed_at: "2026-09-10",
  last_observed_at: "2026-09-12",
  real_points: 2,
  snapshot_points: 1,
};

const API_META = { cursor: null, total: null, offset: null, request_id: "test" };

function renderWithMeta(response: PriceHistoryResponse | Error) {
  const fetchHistory = vi.fn(
    async (): Promise<ApiResponse<PriceHistoryResponse>> =>
      response instanceof Error
        ? { data: null, meta: API_META, errors: [{ code: "server_error", message: response.message }] }
        : { data: response, meta: API_META, errors: [] },
  );
  render(
    <I18nextProvider i18n={i18n}>
      <PriceChart cardId={1} fetchHistory={fetchHistory} />
    </I18nextProvider>,
  );
  return fetchHistory;
}

describe("PriceChart with history meta", () => {
  it("renders PriceHistoryMeta above the chart when meta is present", async () => {
    renderWithMeta({
      observations: [obs("2026-09-10"), obs("2026-09-11", "daily_snapshot"), obs("2026-09-12")],
      summary: null,
      meta: META,
    });
    expect(await screen.findByTestId("price-history-meta")).toBeInTheDocument();
    expect(screen.getByTestId("price-history-variant")).toHaveTextContent("Foil");
    expect(screen.getByTestId("chart-container")).toBeInTheDocument();
  });

  it("without meta keeps legacy UI (no meta, legacy empty text)", async () => {
    renderWithMeta({ observations: [], summary: null });
    const empty = await screen.findByTestId("empty-history");
    expect(empty).toHaveTextContent(i18n.t("chart.noHistory"));
    expect(screen.queryByTestId("price-history-meta")).not.toBeInTheDocument();
    expect(screen.queryByTestId("empty-history-never")).not.toBeInTheDocument();
    expect(screen.queryByTestId("empty-history-period")).not.toBeInTheDocument();
  });

  it("without meta still shows no-data-for-period when summary has no prices", async () => {
    renderWithMeta({
      observations: [],
      summary: {
        period: "30d", price_start: null, price_end: null, absolute_change: null,
        percent_change: null, data_points: 0, resolution: "daily",
      },
    });
    expect(await screen.findByTestId("no-data-for-period")).toBeInTheDocument();
  });

  it("shows never-collected empty state with variant when first_observed_at is null", async () => {
    renderWithMeta({
      observations: [],
      summary: null,
      meta: { ...META, sources: [], first_observed_at: null, last_observed_at: null, real_points: 0, snapshot_points: 0 },
    });
    const empty = await screen.findByTestId("empty-history");
    const never = screen.getByTestId("empty-history-never");
    expect(empty).toContainElement(never);
    expect(never).toHaveTextContent("(foil)");
    expect(empty).not.toHaveTextContent(i18n.t("chart.noHistory"));
    expect(screen.queryByTestId("empty-history-period")).not.toBeInTheDocument();
  });

  it("shows period empty state with since-date when history exists outside the period", async () => {
    renderWithMeta({ observations: [], summary: null, meta: { ...META, variant: "normal" } });
    const empty = await screen.findByTestId("empty-history");
    const period = screen.getByTestId("empty-history-period");
    expect(empty).toContainElement(period);
    expect(period).toHaveTextContent("10/09");
    expect(screen.queryByTestId("empty-history-never")).not.toBeInTheDocument();
  });

  it("shows ErrorBanner unchanged on fetch error and no meta", async () => {
    renderWithMeta(new Error("boom"));
    expect(await screen.findByText("boom")).toBeInTheDocument();
    expect(screen.queryByTestId("price-history-meta")).not.toBeInTheDocument();
    expect(screen.queryByTestId("empty-history")).not.toBeInTheDocument();
  });
});

describe("ChartTooltip", () => {
  function renderTooltip(point: PriceObservation) {
    render(
      <ChartTooltip
        active
        label="2026-09-11"
        payload={[{ dataKey: "median_price", value: 10, color: "#22d3ee", name: "Median", payload: point } as never]}
      />,
    );
  }

  it("indicates repeated price for daily_snapshot points", () => {
    renderTooltip(obs("2026-09-11", "daily_snapshot"));
    expect(screen.getByTestId("tooltip-snapshot-point")).toHaveTextContent(i18n.t("priceHistory.snapshotPoint"));
  });

  it("does not show snapshot text for real points", () => {
    renderTooltip(obs("2026-09-11", "liga"));
    expect(screen.queryByTestId("tooltip-snapshot-point")).not.toBeInTheDocument();
  });

  it("does not show snapshot text when source is absent (legacy backend)", () => {
    renderTooltip(obs("2026-09-11", null));
    expect(screen.queryByTestId("tooltip-snapshot-point")).not.toBeInTheDocument();
  });
});
