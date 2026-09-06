import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceSparkline } from "../../src/components/PriceSparkline";

describe("PriceSparkline", () => {
  it("renders sparkline for valid price data", () => {
    render(<PriceSparkline prices={[10, 12, 15, 14, 16]} />);
    expect(screen.getByTestId("price-sparkline")).toBeDefined();
  });

  it("renders empty placeholder when fewer than 2 prices", () => {
    render(<PriceSparkline prices={[10]} />);
    expect(screen.getByTestId("price-sparkline-empty")).toBeDefined();
  });

  it("renders empty placeholder for empty prices", () => {
    render(<PriceSparkline prices={[]} />);
    expect(screen.getByTestId("price-sparkline-empty")).toBeDefined();
  });

  it("applies custom width and height", () => {
    render(<PriceSparkline prices={[1, 2, 3]} width={100} height={30} />);
    const container = screen.getByTestId("price-sparkline");
    expect(container.style.width).toBe("100px");
    expect(container.style.height).toBe("30px");
  });
});
