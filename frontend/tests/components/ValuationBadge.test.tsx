import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { ValuationBadge } from "../../src/components/ValuationBadge";

// Mock the useValuation hook
const mockUseValuation = vi.fn();
vi.mock("../../src/hooks/useValuation", () => ({
  useValuation: (...args: unknown[]) => mockUseValuation(...args),
}));

describe("ValuationBadge", () => {
  beforeEach(() => {
    mockUseValuation.mockReset();
  });

  it("renders loading state as '--'", () => {
    mockUseValuation.mockReturnValue({ data: null, loading: true, error: null });
    render(<ValuationBadge />);
    expect(screen.getByTestId("valuation-loading")).toBeDefined();
    expect(screen.getByTestId("valuation-loading").textContent).toBe("--");
  });

  it("renders '--' when no data", () => {
    mockUseValuation.mockReturnValue({ data: null, loading: false, error: null });
    render(<ValuationBadge />);
    expect(screen.getByTestId("valuation-no-history")).toBeDefined();
  });

  it("renders '--' when change_pct is null", () => {
    mockUseValuation.mockReturnValue({
      data: { current_value: 1000, previous_value: null, change_pct: null, change_abs: null, currency: "BRL", snapshots: [] },
      loading: false,
      error: null,
    });
    render(<ValuationBadge />);
    expect(screen.getByTestId("valuation-no-history")).toBeDefined();
  });

  it("renders green for positive change", () => {
    mockUseValuation.mockReturnValue({
      data: {
        current_value: 1300,
        previous_value: 1000,
        change_pct: 30.0,
        change_abs: 300.0,
        currency: "BRL",
        snapshots: [],
      },
      loading: false,
      error: null,
    });
    render(<ValuationBadge />);
    const badge = screen.getByTestId("valuation-badge");
    expect(badge.className).toContain("text-emerald-400");
    expect(badge.textContent).toContain("+30.00%");
  });

  it("renders red for negative change", () => {
    mockUseValuation.mockReturnValue({
      data: {
        current_value: 900,
        previous_value: 1000,
        change_pct: -10.0,
        change_abs: -100.0,
        currency: "BRL",
        snapshots: [],
      },
      loading: false,
      error: null,
    });
    render(<ValuationBadge />);
    const badge = screen.getByTestId("valuation-badge");
    expect(badge.className).toContain("text-red-400");
    expect(badge.textContent).toContain("-10.00%");
  });

  it("renders up arrow for positive change", () => {
    mockUseValuation.mockReturnValue({
      data: { current_value: 1100, previous_value: 1000, change_pct: 10.0, change_abs: 100.0, currency: "BRL", snapshots: [] },
      loading: false,
      error: null,
    });
    render(<ValuationBadge />);
    const badge = screen.getByTestId("valuation-badge");
    expect(badge.textContent).toContain("\u2191");
  });

  it("renders down arrow for negative change", () => {
    mockUseValuation.mockReturnValue({
      data: { current_value: 900, previous_value: 1000, change_pct: -10.0, change_abs: -100.0, currency: "BRL", snapshots: [] },
      loading: false,
      error: null,
    });
    render(<ValuationBadge />);
    const badge = screen.getByTestId("valuation-badge");
    expect(badge.textContent).toContain("\u2193");
  });

  it("passes days and currency to useValuation", () => {
    mockUseValuation.mockReturnValue({ data: null, loading: true, error: null });
    render(<ValuationBadge days={30} currency="USD" />);
    expect(mockUseValuation).toHaveBeenCalledWith(30, "USD");
  });

  it("renders zero change as green", () => {
    mockUseValuation.mockReturnValue({
      data: { current_value: 1000, previous_value: 1000, change_pct: 0.0, change_abs: 0.0, currency: "BRL", snapshots: [] },
      loading: false,
      error: null,
    });
    render(<ValuationBadge />);
    const badge = screen.getByTestId("valuation-badge");
    expect(badge.className).toContain("text-emerald-400");
    expect(badge.textContent).toContain("+0.00%");
  });

  it("has tooltip with absolute change", () => {
    mockUseValuation.mockReturnValue({
      data: { current_value: 1100, previous_value: 1000, change_pct: 10.0, change_abs: 100.0, currency: "BRL", snapshots: [] },
      loading: false,
      error: null,
    });
    render(<ValuationBadge />);
    const badge = screen.getByTestId("valuation-badge");
    expect(badge.title).toBeTruthy();
    expect(badge.title.length).toBeGreaterThan(0);
  });
});
