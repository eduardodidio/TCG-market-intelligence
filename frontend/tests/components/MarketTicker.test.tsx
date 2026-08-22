import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { MarketTicker } from "../../src/components/MarketTicker";
import type { TickerItemData } from "../../src/types/api";

// Mock useTickerData hook
const mockUseTickerData = vi.fn<[], { items: TickerItemData[]; loading: boolean }>();

vi.mock("../../src/hooks/useTickerData", () => ({
  useTickerData: () => mockUseTickerData(),
}));

function mockItems(count = 3): TickerItemData[] {
  return Array.from({ length: count }, (_, i) => ({
    card_id: i + 1,
    name_en: `Card ${i + 1}`,
    name_pt: `Carta ${i + 1}`,
    set_code: "lea",
    price_end: 10 + i,
    change_pct: i % 2 === 0 ? 5.0 : -3.0,
    direction: (i % 2 === 0 ? "up" : "down") as "up" | "down",
    currency: "BRL",
  }));
}

function renderTicker() {
  return render(
    <MemoryRouter>
      <MarketTicker />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("MarketTicker", () => {
  it("returns null when loading", () => {
    mockUseTickerData.mockReturnValue({ items: [], loading: true });
    const { container } = renderTicker();
    expect(container.innerHTML).toBe("");
  });

  it("returns null when items array is empty", () => {
    mockUseTickerData.mockReturnValue({ items: [], loading: false });
    const { container } = renderTicker();
    expect(container.innerHTML).toBe("");
  });

  it("renders items doubled for seamless scrolling", () => {
    const items = mockItems(3);
    mockUseTickerData.mockReturnValue({ items, loading: false });
    renderTicker();
    // 3 items doubled = 6 ticker-item elements
    const tickerItems = screen.getAllByTestId("ticker-item");
    expect(tickerItems).toHaveLength(6);
  });

  it("has role=marquee", () => {
    mockUseTickerData.mockReturnValue({ items: mockItems(2), loading: false });
    renderTicker();
    const ticker = screen.getByTestId("market-ticker");
    expect(ticker.getAttribute("role")).toBe("marquee");
  });

  it("has aria-live=off to prevent screen reader announcements", () => {
    mockUseTickerData.mockReturnValue({ items: mockItems(2), loading: false });
    renderTicker();
    const ticker = screen.getByTestId("market-ticker");
    expect(ticker.getAttribute("aria-live")).toBe("off");
  });

  it("has data-testid market-ticker", () => {
    mockUseTickerData.mockReturnValue({ items: mockItems(2), loading: false });
    renderTicker();
    expect(screen.getByTestId("market-ticker")).toBeTruthy();
  });

  it("applies hidden md:block classes for responsive visibility", () => {
    mockUseTickerData.mockReturnValue({ items: mockItems(2), loading: false });
    renderTicker();
    const ticker = screen.getByTestId("market-ticker");
    expect(ticker.className).toContain("hidden");
    expect(ticker.className).toContain("md:block");
  });

  it("sets --ticker-duration CSS custom property", () => {
    const items = mockItems(5);
    mockUseTickerData.mockReturnValue({ items, loading: false });
    renderTicker();
    const ticker = screen.getByTestId("market-ticker");
    const scrollDiv = ticker.firstElementChild as HTMLElement;
    // duration = max(20, (5 * 80) / 60) = max(20, 6.67) = 20
    expect(scrollDiv.style.getPropertyValue("--ticker-duration")).toBe("20s");
  });

  it("calculates longer duration for many items", () => {
    const items = mockItems(20);
    mockUseTickerData.mockReturnValue({ items, loading: false });
    renderTicker();
    const ticker = screen.getByTestId("market-ticker");
    const scrollDiv = ticker.firstElementChild as HTMLElement;
    // duration = max(20, (20 * 80) / 60) = max(20, 26.67) ~= 26.67
    const dur = parseFloat(scrollDiv.style.getPropertyValue("--ticker-duration"));
    expect(dur).toBeGreaterThan(20);
  });

  it("duplicate items have tabIndex=-1", () => {
    const items = mockItems(2);
    mockUseTickerData.mockReturnValue({ items, loading: false });
    renderTicker();
    const tickerItems = screen.getAllByTestId("ticker-item");
    // First 2 should NOT have tabIndex=-1
    expect(tickerItems[0].getAttribute("tabindex")).toBeNull();
    expect(tickerItems[1].getAttribute("tabindex")).toBeNull();
    // Last 2 (duplicates) should have tabIndex=-1
    expect(tickerItems[2].getAttribute("tabindex")).toBe("-1");
    expect(tickerItems[3].getAttribute("tabindex")).toBe("-1");
  });

  it("has aria-label on the container", () => {
    mockUseTickerData.mockReturnValue({ items: mockItems(2), loading: false });
    renderTicker();
    const ticker = screen.getByTestId("market-ticker");
    expect(ticker.getAttribute("aria-label")).toBeTruthy();
  });
});
