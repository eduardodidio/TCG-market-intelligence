import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChimarraoIcon } from "../../src/components/ChimarraoIcon";

describe("ChimarraoIcon", () => {
  it("renders with pulse animation", () => {
    render(<ChimarraoIcon onClick={vi.fn()} />);
    const btn = screen.getByTestId("chimarrao-icon");
    expect(btn).toBeDefined();
    expect(btn.className).toContain("animate-pulse");
  });

  it("calls onClick when clicked", () => {
    const handleClick = vi.fn();
    render(<ChimarraoIcon onClick={handleClick} />);
    fireEvent.click(screen.getByTestId("chimarrao-icon"));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it("has correct fixed positioning classes", () => {
    render(<ChimarraoIcon onClick={vi.fn()} />);
    const btn = screen.getByTestId("chimarrao-icon");
    expect(btn.className).toContain("fixed");
    expect(btn.className).toContain("bottom-6");
    expect(btn.className).toContain("right-6");
    expect(btn.className).toContain("z-50");
  });

  it("has hover scale and transition classes", () => {
    render(<ChimarraoIcon onClick={vi.fn()} />);
    const btn = screen.getByTestId("chimarrao-icon");
    expect(btn.className).toContain("hover:scale-110");
    expect(btn.className).toContain("transition-transform");
  });

  it("has green glow shadow", () => {
    render(<ChimarraoIcon onClick={vi.fn()} />);
    const btn = screen.getByTestId("chimarrao-icon");
    expect(btn.className).toContain("shadow-lg");
    expect(btn.className).toContain("shadow-green-500/30");
  });
});
