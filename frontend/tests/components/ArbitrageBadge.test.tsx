import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ArbitrageBadge } from "../../src/components/ArbitrageBadge";

describe("ArbitrageBadge", () => {
  it("shows Best: Liga when Liga price is lower", () => {
    render(<ArbitrageBadge ligaPrice={10} tcgPrice={15} />);
    const badge = screen.getByTestId("arbitrage-badge");
    expect(badge.textContent).toContain("Liga");
    expect(badge.className).toContain("text-green-400");
  });

  it("shows Best: TCG when TCG price is lower", () => {
    render(<ArbitrageBadge ligaPrice={20} tcgPrice={12} />);
    const badge = screen.getByTestId("arbitrage-badge");
    expect(badge.textContent).toContain("TCG");
  });

  it("calculates correct gap percentage", () => {
    render(<ArbitrageBadge ligaPrice={10} tcgPrice={20} />);
    const badge = screen.getByTestId("arbitrage-badge");
    // gap = (20-10)/20 * 100 = 50%
    expect(badge.textContent).toContain("50.0%");
  });

  it("renders nothing when both prices are null", () => {
    const { container } = render(<ArbitrageBadge ligaPrice={null} tcgPrice={null} />);
    expect(container.innerHTML).toBe("");
  });

  it("shows Liga only when only Liga price exists", () => {
    render(<ArbitrageBadge ligaPrice={10} tcgPrice={null} />);
    const badge = screen.getByTestId("arbitrage-badge");
    expect(badge.textContent).toContain("Liga only");
  });

  it("shows TCG only when only TCG price exists", () => {
    render(<ArbitrageBadge ligaPrice={null} tcgPrice={15} />);
    const badge = screen.getByTestId("arbitrage-badge");
    expect(badge.textContent).toContain("TCG only");
  });

  it("has tooltip with both prices when both exist", () => {
    render(<ArbitrageBadge ligaPrice={10} tcgPrice={15} />);
    const badge = screen.getByTestId("arbitrage-badge");
    expect(badge.getAttribute("title")).toContain("Liga");
    expect(badge.getAttribute("title")).toContain("TCG");
  });
});
