import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CostBadge } from "../../src/components/CostBadge";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (key === "credits.costBadge") return `(${opts?.cost} token)`;
      return key;
    },
  }),
}));

describe("CostBadge", () => {
  it("renders cost text", () => {
    render(<CostBadge cost={1} balance={10} />);
    const badge = screen.getByTestId("cost-badge");
    expect(badge.textContent).toBe("(1 token)");
  });

  it("uses slate color when balance is sufficient", () => {
    render(<CostBadge cost={1} balance={10} />);
    const badge = screen.getByTestId("cost-badge");
    expect(badge.className).toContain("text-slate-400");
    expect(badge.className).not.toContain("text-red-400");
  });

  it("uses red color when balance is insufficient", () => {
    render(<CostBadge cost={5} balance={2} />);
    const badge = screen.getByTestId("cost-badge");
    expect(badge.className).toContain("text-red-400");
    expect(badge.className).not.toContain("text-slate-400");
  });

  it("uses slate color when balance is null", () => {
    render(<CostBadge cost={1} balance={null} />);
    const badge = screen.getByTestId("cost-badge");
    expect(badge.className).toContain("text-slate-400");
  });

  it("uses red when balance equals zero and cost > 0", () => {
    render(<CostBadge cost={1} balance={0} />);
    const badge = screen.getByTestId("cost-badge");
    expect(badge.className).toContain("text-red-400");
  });

  it("renders correct cost number", () => {
    render(<CostBadge cost={42} balance={100} />);
    const badge = screen.getByTestId("cost-badge");
    expect(badge.textContent).toBe("(42 token)");
  });
});
