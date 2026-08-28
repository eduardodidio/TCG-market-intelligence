import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { FoilBadge } from "../../src/components/FoilBadge";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "card.foil": "Foil",
        "card.foilPrice": "Foil price",
      };
      return map[key] ?? key;
    },
  }),
  initReactI18next: { type: "3rdParty", init: () => {} },
}));

describe("FoilBadge", () => {
  it("renders with 'Foil' text", () => {
    render(<FoilBadge />);
    expect(screen.getByText("Foil")).toBeInTheDocument();
  });

  it("has data-testid foil-badge", () => {
    render(<FoilBadge />);
    expect(screen.getByTestId("foil-badge")).toBeInTheDocument();
  });

  it("renders compact variant with text-xs class", () => {
    render(<FoilBadge variant="compact" />);
    const badge = screen.getByTestId("foil-badge");
    expect(badge.className).toContain("text-xs");
    expect(badge.className).toContain("px-2");
  });

  it("renders full variant with text-sm class", () => {
    render(<FoilBadge variant="full" />);
    const badge = screen.getByTestId("foil-badge");
    expect(badge.className).toContain("text-sm");
    expect(badge.className).toContain("px-3");
  });

  it("defaults to compact variant", () => {
    render(<FoilBadge />);
    const badge = screen.getByTestId("foil-badge");
    expect(badge.className).toContain("text-xs");
  });

  it("has amber gradient styling", () => {
    render(<FoilBadge />);
    const badge = screen.getByTestId("foil-badge");
    expect(badge.className).toContain("from-amber-500/20");
    expect(badge.className).toContain("to-yellow-500/20");
    expect(badge.className).toContain("text-amber-400");
  });

  it("contains a star SVG icon", () => {
    render(<FoilBadge />);
    const badge = screen.getByTestId("foil-badge");
    const svg = badge.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });

  it("compact variant has smaller icon (h-3 w-3)", () => {
    render(<FoilBadge variant="compact" />);
    const svg = screen.getByTestId("foil-badge").querySelector("svg");
    expect(svg?.className.baseVal ?? svg?.getAttribute("class")).toContain("h-3");
  });

  it("full variant has larger icon (h-4 w-4)", () => {
    render(<FoilBadge variant="full" />);
    const svg = screen.getByTestId("foil-badge").querySelector("svg");
    expect(svg?.className.baseVal ?? svg?.getAttribute("class")).toContain("h-4");
  });
});
