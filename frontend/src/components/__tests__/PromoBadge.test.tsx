import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PromoBadge } from "../PromoBadge";

describe("PromoBadge", () => {
  it('renders with data-testid="promo-badge"', () => {
    render(<PromoBadge />);
    expect(screen.getByTestId("promo-badge")).toBeInTheDocument();
  });

  it('contains "PROMO" text', () => {
    render(<PromoBadge />);
    expect(screen.getByText("PROMO")).toBeInTheDocument();
  });

  it("has pointer-events: none style", () => {
    render(<PromoBadge />);
    const badge = screen.getByTestId("promo-badge");
    expect(badge).toHaveClass("pointer-events-none");
  });

  it("accepts and applies optional className", () => {
    render(<PromoBadge className="my-custom-class" />);
    const badge = screen.getByTestId("promo-badge");
    expect(badge).toHaveClass("my-custom-class");
  });

  it("has absolute positioning classes for bottom-center placement", () => {
    render(<PromoBadge />);
    const badge = screen.getByTestId("promo-badge");
    expect(badge).toHaveClass("absolute");
    expect(badge).toHaveClass("bottom-2");
    expect(badge).toHaveClass("left-1/2");
    expect(badge).toHaveClass("-translate-x-1/2");
  });

  it("has silver gradient background style", () => {
    render(<PromoBadge />);
    const badge = screen.getByTestId("promo-badge");
    expect(badge.style.background).toContain("linear-gradient");
  });
});
