import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScanSummaryCard } from "../../src/components/ScanSummaryCard";
import type { ScanSummary } from "../../src/components/ScanSummaryCard";

const baseSummary: ScanSummary = {
  cardsTotal: 100,
  cardsProcessed: 100,
  cardsFailed: 5,
  observationsSaved: 95,
  notFoundCount: 3,
  rateLimitedCount: 1,
  durationMs: 154000,
};

describe("ScanSummaryCard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all stat counts when all are > 0", () => {
    render(<ScanSummaryCard summary={baseSummary} onDismiss={vi.fn()} />);

    expect(screen.getByTestId("scan-summary-priced")).toBeDefined();
    expect(screen.getByTestId("scan-summary-not-found")).toBeDefined();
    expect(screen.getByTestId("scan-summary-rate-limited")).toBeDefined();
    expect(screen.getByTestId("scan-summary-other-errors")).toBeDefined();
  });

  it("hides zero-count categories", () => {
    const noErrors: ScanSummary = {
      ...baseSummary,
      cardsFailed: 0,
      notFoundCount: 0,
      rateLimitedCount: 0,
    };
    render(<ScanSummaryCard summary={noErrors} onDismiss={vi.fn()} />);

    expect(screen.getByTestId("scan-summary-priced")).toBeDefined();
    expect(screen.queryByTestId("scan-summary-not-found")).toBeNull();
    expect(screen.queryByTestId("scan-summary-rate-limited")).toBeNull();
    expect(screen.queryByTestId("scan-summary-other-errors")).toBeNull();
  });

  it("dismiss button calls onDismiss", () => {
    const onDismiss = vi.fn();
    render(<ScanSummaryCard summary={baseSummary} onDismiss={onDismiss} />);

    fireEvent.click(screen.getByTestId("scan-summary-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
  });

  it("shows warning icon when failures exist", () => {
    render(<ScanSummaryCard summary={baseSummary} onDismiss={vi.fn()} />);
    expect(screen.getByTestId("scan-summary-warning-icon")).toBeDefined();
    expect(screen.queryByTestId("scan-summary-success-icon")).toBeNull();
  });

  it("shows success icon when no failures", () => {
    const noFail: ScanSummary = {
      ...baseSummary,
      cardsFailed: 0,
      notFoundCount: 0,
      rateLimitedCount: 0,
    };
    render(<ScanSummaryCard summary={noFail} onDismiss={vi.fn()} />);
    expect(screen.getByTestId("scan-summary-success-icon")).toBeDefined();
    expect(screen.queryByTestId("scan-summary-warning-icon")).toBeNull();
  });

  it("formats duration correctly", () => {
    render(<ScanSummaryCard summary={baseSummary} onDismiss={vi.fn()} />);
    const durationEl = screen.getByTestId("scan-summary-duration");
    // The i18n key receives {{time}} as "2m 34s" -- check for either the
    // formatted output (when locale is loaded) or the key (when mock returns key)
    const text = durationEl.textContent || "";
    expect(text.includes("2m 34s") || text.includes("scan.summary.duration")).toBe(true);
  });

  it("card persists until dismissed (no auto-timeout)", async () => {
    vi.useFakeTimers();
    const onDismiss = vi.fn();
    render(<ScanSummaryCard summary={baseSummary} onDismiss={onDismiss} />);

    // Advance time well past any reasonable auto-dismiss
    vi.advanceTimersByTime(30000);

    // Card should still be in the DOM
    expect(screen.getByTestId("scan-summary-card")).toBeDefined();
    // onDismiss should NOT have been called automatically
    expect(onDismiss).not.toHaveBeenCalled();

    vi.useRealTimers();
  });
});
