import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { PnlBadge } from "../../src/components/PnlBadge";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock("../../src/utils/format", () => ({
  formatCurrency: (value: number | null, _currency: string) => {
    if (value == null) return "--";
    return `R$ ${value.toFixed(2)}`;
  },
}));

describe("PnlBadge", () => {
  it("renders positive P&L in green", () => {
    render(
      <PnlBadge acquisitionPrice={5.0} currentPrice={8.5} currency="BRL" />,
    );
    const badge = screen.getByTestId("pnl-badge");
    expect(badge.textContent).toContain("+R$ 3.50");
    expect(badge.textContent).toContain("(+70.0%)");
    expect(badge.className).toContain("text-emerald-400");
  });

  it("renders negative P&L in red", () => {
    render(
      <PnlBadge acquisitionPrice={10.0} currentPrice={7.0} currency="BRL" />,
    );
    const badge = screen.getByTestId("pnl-badge");
    expect(badge.textContent).toContain("R$ -3.00");
    expect(badge.textContent).toContain("(-30.0%)");
    expect(badge.className).toContain("text-red-400");
  });

  it("renders zero P&L in green", () => {
    render(
      <PnlBadge acquisitionPrice={5.0} currentPrice={5.0} currency="BRL" />,
    );
    const badge = screen.getByTestId("pnl-badge");
    expect(badge.textContent).toContain("+R$ 0.00");
    expect(badge.className).toContain("text-emerald-400");
  });
});
