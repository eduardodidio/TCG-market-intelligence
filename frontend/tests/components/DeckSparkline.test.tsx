import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { DeckSparkline } from "../../src/components/DeckSparkline";

describe("DeckSparkline", () => {
  it("renders sparkline container for valid data", () => {
    render(<DeckSparkline data={[10, 20, 30]} />);
    expect(screen.getByTestId("sparkline")).toBeDefined();
  });

  it("renders empty container for empty data", () => {
    render(<DeckSparkline data={[]} />);
    expect(screen.getByTestId("sparkline-empty")).toBeDefined();
  });

  it("handles single-point data without crashing", () => {
    render(<DeckSparkline data={[42]} />);
    expect(screen.getByTestId("sparkline")).toBeDefined();
  });

  it("applies custom width and height", () => {
    render(<DeckSparkline data={[1, 2, 3]} width={200} height={50} />);
    const container = screen.getByTestId("sparkline");
    expect(container.style.width).toBe("200px");
    expect(container.style.height).toBe("50px");
  });
});
