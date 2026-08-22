import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { TickerItem } from "../../src/components/TickerItem";
import type { TickerItemData } from "../../src/types/api";

function mockItem(overrides?: Partial<TickerItemData>): TickerItemData {
  return {
    card_id: 1,
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "lea",
    price_end: 15.0,
    change_pct: 12.5,
    direction: "up",
    currency: "BRL",
    ...overrides,
  };
}

describe("TickerItem", () => {
  it("renders card name", () => {
    render(<TickerItem item={mockItem()} onClick={vi.fn()} />);
    expect(screen.getByText("Lightning Bolt")).toBeTruthy();
  });

  it("renders set code in uppercase", () => {
    render(<TickerItem item={mockItem()} onClick={vi.fn()} />);
    const setEl = screen.getByText("lea");
    expect(setEl).toBeTruthy();
    expect(setEl.className).toContain("uppercase");
  });

  it("renders price", () => {
    render(<TickerItem item={mockItem()} onClick={vi.fn()} />);
    // formatCurrency for BRL should produce R$ formatted price
    const items = screen.getAllByTestId("ticker-item");
    expect(items[0].textContent).toContain("15");
  });

  it("shows positive change with green color for up direction", () => {
    render(<TickerItem item={mockItem({ direction: "up", change_pct: 12.5 })} onClick={vi.fn()} />);
    const changeEl = screen.getByText(/\+12\.5%/);
    expect(changeEl).toBeTruthy();
    expect(changeEl.className).toContain("text-emerald-400");
  });

  it("shows negative change with red color for down direction", () => {
    render(<TickerItem item={mockItem({ direction: "down", change_pct: -8.3 })} onClick={vi.fn()} />);
    const changeEl = screen.getByText(/-8\.3%/);
    expect(changeEl).toBeTruthy();
    expect(changeEl.className).toContain("text-red-400");
  });

  it("shows up arrow for up direction", () => {
    render(<TickerItem item={mockItem({ direction: "up" })} onClick={vi.fn()} />);
    expect(screen.getByText(/\u25B2/)).toBeTruthy();
  });

  it("shows down arrow for down direction", () => {
    render(<TickerItem item={mockItem({ direction: "down" })} onClick={vi.fn()} />);
    expect(screen.getByText(/\u25BC/)).toBeTruthy();
  });

  it("calls onClick with card_id when clicked", () => {
    const onClick = vi.fn();
    render(<TickerItem item={mockItem({ card_id: 42 })} onClick={onClick} />);
    fireEvent.click(screen.getByTestId("ticker-item"));
    expect(onClick).toHaveBeenCalledWith(42);
  });

  it("has aria-label with card info", () => {
    render(<TickerItem item={mockItem()} onClick={vi.fn()} />);
    const btn = screen.getByTestId("ticker-item");
    expect(btn.getAttribute("aria-label")).toContain("Lightning Bolt");
  });

  it("truncates long card names", () => {
    render(<TickerItem item={mockItem()} onClick={vi.fn()} />);
    const nameEl = screen.getByText("Lightning Bolt");
    expect(nameEl.className).toContain("truncate");
    expect(nameEl.className).toContain("max-w-[120px]");
  });

  it("hides set code when null", () => {
    render(<TickerItem item={mockItem({ set_code: null })} onClick={vi.fn()} />);
    expect(screen.queryByText("lea")).toBeNull();
  });

  it("applies tabIndex when provided", () => {
    render(<TickerItem item={mockItem()} onClick={vi.fn()} tabIndex={-1} />);
    const btn = screen.getByTestId("ticker-item");
    expect(btn.getAttribute("tabindex")).toBe("-1");
  });

  it("uses absolute value of change_pct for display", () => {
    render(<TickerItem item={mockItem({ direction: "down", change_pct: -25.7 })} onClick={vi.fn()} />);
    // Should show 25.7%, not -25.7% (sign comes from the prefix)
    expect(screen.getByText(/-25\.7%/)).toBeTruthy();
  });
});
