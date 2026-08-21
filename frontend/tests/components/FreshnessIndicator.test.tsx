import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { FreshnessIndicator } from "../../src/components/FreshnessIndicator";

describe("FreshnessIndicator", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders relative time for a recent timestamp", () => {
    // Fix "now" to 2026-08-19T12:00:00Z
    const now = new Date("2026-08-19T12:00:00Z").getTime();
    vi.spyOn(Date, "now").mockReturnValue(now);

    // 35 minutes ago
    const thirtyFiveMinAgo = new Date("2026-08-19T11:25:00Z").toISOString();

    render(
      <FreshnessIndicator lastCollectionAt={thirtyFiveMinAgo} status="healthy" />,
    );

    expect(screen.getByTestId("freshness-indicator")).toBeDefined();
    expect(screen.getByText("Last updated: 35 minutes ago")).toBeDefined();
  });

  it("renders 'just now' for very recent timestamps", () => {
    const now = new Date("2026-08-19T12:00:00Z").getTime();
    vi.spyOn(Date, "now").mockReturnValue(now);

    const tenSecondsAgo = new Date("2026-08-19T11:59:50Z").toISOString();

    render(
      <FreshnessIndicator lastCollectionAt={tenSecondsAgo} status="healthy" />,
    );

    expect(screen.getByText("Last updated: just now")).toBeDefined();
  });

  it("renders hours ago correctly", () => {
    const now = new Date("2026-08-19T15:00:00Z").getTime();
    vi.spyOn(Date, "now").mockReturnValue(now);

    const threeHoursAgo = new Date("2026-08-19T12:00:00Z").toISOString();

    render(
      <FreshnessIndicator lastCollectionAt={threeHoursAgo} status="stale" />,
    );

    expect(screen.getByText("Last updated: 3 hours ago")).toBeDefined();
  });

  it("renders days ago correctly", () => {
    const now = new Date("2026-08-19T12:00:00Z").getTime();
    vi.spyOn(Date, "now").mockReturnValue(now);

    const twoDaysAgo = new Date("2026-08-17T12:00:00Z").toISOString();

    render(
      <FreshnessIndicator lastCollectionAt={twoDaysAgo} status="error" />,
    );

    expect(screen.getByText("Last updated: 2 days ago")).toBeDefined();
  });

  it("renders singular form for 1 minute", () => {
    const now = new Date("2026-08-19T12:01:30Z").getTime();
    vi.spyOn(Date, "now").mockReturnValue(now);

    const oneMinAgo = new Date("2026-08-19T12:00:00Z").toISOString();

    render(
      <FreshnessIndicator lastCollectionAt={oneMinAgo} status="healthy" />,
    );

    expect(screen.getByText("Last updated: 1 minute ago")).toBeDefined();
  });

  it("renders 'Data freshness: Unknown' when lastCollectionAt is null", () => {
    render(<FreshnessIndicator lastCollectionAt={null} status="healthy" />);

    expect(screen.getByText("Data freshness: Unknown")).toBeDefined();
  });

  it("shows green dot for healthy status", () => {
    const now = new Date("2026-08-19T12:00:00Z").getTime();
    vi.spyOn(Date, "now").mockReturnValue(now);

    render(
      <FreshnessIndicator
        lastCollectionAt="2026-08-19T11:30:00Z"
        status="healthy"
      />,
    );

    const dot = screen.getByTestId("freshness-dot");
    expect(dot.className).toContain("bg-tcg-gain");
  });

  it("shows yellow dot for stale status", () => {
    render(
      <FreshnessIndicator lastCollectionAt={null} status="stale" />,
    );

    const dot = screen.getByTestId("freshness-dot");
    expect(dot.className).toContain("bg-tcg-warning");
  });

  it("shows red dot for error status", () => {
    render(
      <FreshnessIndicator lastCollectionAt={null} status="error" />,
    );

    const dot = screen.getByTestId("freshness-dot");
    expect(dot.className).toContain("bg-tcg-loss");
  });

  it("shows slate dot for unknown status", () => {
    render(
      <FreshnessIndicator lastCollectionAt={null} status="unknown" />,
    );

    const dot = screen.getByTestId("freshness-dot");
    expect(dot.className).toContain("bg-tcg-muted");
  });
});
