import { describe, expect, it } from "vitest";
import { scryfallImageUrl, scryfallImageByName, scryfallSetIconUrl } from "../scryfall";

describe("scryfallImageUrl", () => {
  it("maps borderless set code bldmr to dmr", () => {
    const url = scryfallImageUrl("bldmr", "437");
    expect(url).toContain("/cards/dmr/437?");
    expect(url).toContain("format=image");
  });

  it("maps extended art set code exdmu to dmu", () => {
    const url = scryfallImageUrl("exdmu", "410");
    expect(url).toContain("/cards/dmu/410?");
  });

  it("maps Secret Lair sld158 to sld", () => {
    const url = scryfallImageUrl("sld158", "1245");
    expect(url).toContain("/cards/sld/1245?");
  });

  it("passes through standard set codes unchanged", () => {
    const url = scryfallImageUrl("dmr", "100");
    expect(url).toBe(
      "https://api.scryfall.com/cards/dmr/100?format=image&version=normal",
    );
  });

  it("handles uppercase input", () => {
    const url = scryfallImageUrl("BLDMR", "437");
    expect(url).toContain("/cards/dmr/437?");
  });

  it("respects version parameter", () => {
    const url = scryfallImageUrl("dmr", "100", "small");
    expect(url).toContain("version=small");
  });

  it("uses normal version by default", () => {
    const url = scryfallImageUrl("dmr", "100");
    expect(url).toContain("version=normal");
  });
});

describe("scryfallImageByName", () => {
  it("builds name-based URL with encoded name", () => {
    const url = scryfallImageByName("Lightning Bolt");
    expect(url).toContain("exact=Lightning%20Bolt");
    expect(url).toContain("format=image");
  });

  it("uses normal version by default", () => {
    const url = scryfallImageByName("Sol Ring");
    expect(url).toContain("version=normal");
  });

  it("respects version parameter", () => {
    const url = scryfallImageByName("Sol Ring", "large");
    expect(url).toContain("version=large");
  });

  it("encodes special characters in card name", () => {
    const url = scryfallImageByName("Jace, the Mind Sculptor");
    expect(url).toContain("exact=Jace%2C%20the%20Mind%20Sculptor");
  });

  it("encodes ampersand in card name", () => {
    const url = scryfallImageByName("Sword of Fire & Ice");
    expect(url).toContain("exact=Sword%20of%20Fire%20%26%20Ice");
  });
});

describe("scryfallSetIconUrl", () => {
  it("builds SVG URL for a standard set code", () => {
    expect(scryfallSetIconUrl("DMR")).toBe(
      "https://svgs.scryfall.io/sets/dmr.svg",
    );
  });

  it("maps variant set code bldmr to dmr", () => {
    expect(scryfallSetIconUrl("bldmr")).toBe(
      "https://svgs.scryfall.io/sets/dmr.svg",
    );
  });

  it("handles uppercase variant set code", () => {
    expect(scryfallSetIconUrl("BLDMR")).toBe(
      "https://svgs.scryfall.io/sets/dmr.svg",
    );
  });
});
