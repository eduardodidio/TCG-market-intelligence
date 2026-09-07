import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TrendBadge } from "../../src/components/TrendBadge";

describe("TrendBadge", () => {
  it("renders green up-arrow for positive change", () => {
    render(<TrendBadge changePct={12.4} />);
    const badge = screen.getByTestId("trend-badge");
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain("+12.4%");
    expect(badge.className).toContain("text-green-400");
  });

  it("renders red down-arrow for negative change", () => {
    render(<TrendBadge changePct={-5.3} />);
    const badge = screen.getByTestId("trend-badge");
    expect(badge.textContent).toContain("-5.3%");
    expect(badge.className).toContain("text-red-400");
  });

  it("renders gray dash for zero change", () => {
    render(<TrendBadge changePct={0} />);
    const badge = screen.getByTestId("trend-badge");
    expect(badge.textContent).toContain("0.0%");
    expect(badge.className).toContain("text-slate-400");
  });

  it("renders nothing for null change", () => {
    const { container } = render(<TrendBadge changePct={null} />);
    expect(container.innerHTML).toBe("");
  });

  it("formats percentage to 1 decimal place", () => {
    render(<TrendBadge changePct={12.456} />);
    const badge = screen.getByTestId("trend-badge");
    expect(badge.textContent).toContain("+12.5%");
  });

  it("renders with md size class", () => {
    render(<TrendBadge changePct={5} size="md" />);
    const badge = screen.getByTestId("trend-badge");
    expect(badge.className).toContain("text-sm");
  });

  it("renders with sm size class by default", () => {
    render(<TrendBadge changePct={5} />);
    const badge = screen.getByTestId("trend-badge");
    expect(badge.className).toContain("text-xs");
  });

  it("has aria-label for accessibility", () => {
    render(<TrendBadge changePct={10} />);
    const badge = screen.getByTestId("trend-badge");
    expect(badge.getAttribute("aria-label")).toContain("Trending up");
  });
});
