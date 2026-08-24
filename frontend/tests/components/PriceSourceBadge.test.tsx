import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { PriceSourceBadge } from "../../src/components/PriceSourceBadge";

describe("PriceSourceBadge", () => {
  it("renders amber badge with 'Manual Price' text for source='manual'", () => {
    render(<PriceSourceBadge priceSource="manual" />);
    const badge = screen.getByTestId("price-source-badge");
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain("Manual Price");
    expect(badge.className).toContain("text-amber-400");
  });

  it("renders no badge for source='myp'", () => {
    render(<PriceSourceBadge priceSource="myp" />);
    expect(screen.queryByTestId("price-source-badge")).toBeNull();
  });

  it("renders no badge for source='jsonld_snapshot'", () => {
    render(<PriceSourceBadge priceSource="jsonld_snapshot" />);
    expect(screen.queryByTestId("price-source-badge")).toBeNull();
  });

  it("renders no badge when price_source is null", () => {
    render(<PriceSourceBadge priceSource={null} />);
    expect(screen.queryByTestId("price-source-badge")).toBeNull();
  });

  it("renders no badge when price_source is undefined", () => {
    render(<PriceSourceBadge />);
    expect(screen.queryByTestId("price-source-badge")).toBeNull();
  });

  it("has tooltip with manual price explanation", () => {
    render(<PriceSourceBadge priceSource="manual" />);
    const badge = screen.getByTestId("price-source-badge");
    expect(badge.getAttribute("title")).toBe("Price was manually set");
  });

  it("renders pencil icon SVG inside badge", () => {
    render(<PriceSourceBadge priceSource="manual" />);
    const badge = screen.getByTestId("price-source-badge");
    const svg = badge.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg!.getAttribute("aria-hidden")).toBe("true");
  });

  it("renders violet badge with 'LigaMagic' text for source='liga'", () => {
    render(<PriceSourceBadge priceSource="liga" />);
    const badge = screen.getByTestId("price-source-badge");
    expect(badge).toBeDefined();
    expect(badge.textContent).toContain("LigaMagic");
    expect(badge.className).toContain("text-violet-400");
    expect(badge.className).toContain("bg-violet-600/20");
  });

  it("renders globe icon SVG for liga source", () => {
    render(<PriceSourceBadge priceSource="liga" />);
    const badge = screen.getByTestId("price-source-badge");
    const svg = badge.querySelector("svg");
    expect(svg).not.toBeNull();
    expect(svg!.getAttribute("aria-hidden")).toBe("true");
  });

  it("has tooltip with LigaMagic label for liga source", () => {
    render(<PriceSourceBadge priceSource="liga" />);
    const badge = screen.getByTestId("price-source-badge");
    expect(badge.getAttribute("title")).toBe("LigaMagic");
  });

  it("uses i18n t() for badge text (renders translated text)", () => {
    // The test setup initializes i18n with EN translations.
    // This verifies the component uses t("price.manual") which resolves to "Manual Price"
    render(<PriceSourceBadge priceSource="manual" />);
    expect(screen.getByTestId("price-source-badge").textContent).toContain("Manual Price");
  });
});
