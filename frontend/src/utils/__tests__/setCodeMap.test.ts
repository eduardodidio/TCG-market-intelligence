import { describe, expect, it } from "vitest";
import { mapToScryfallSetCode } from "../setCodeMap";

describe("mapToScryfallSetCode", () => {
  describe("known variant mappings", () => {
    const cases: [string, string][] = [
      // Borderless
      ["bldmr", "dmr"],
      ["blfdn", "fdn"],
      ["bl2x2", "2x2"],
      ["bltr", "ltr"],
      ["blltr", "ltr"],
      // Extended Art
      ["exdmu", "dmu"],
      ["eafic", "fic"],
      ["eahoc", "hoc"],
      // Showcase
      ["srltr", "ltr"],
      ["skmh2", "mh2"],
      // Full-art / Etched
      ["feclb", "clb"],
      ["fesnc", "snc"],
      // Special/Misc
      ["smbro", "bro"],
      // Commander Borderless
      ["cbznr", "znr"],
      // Commander variant
      ["cthb", "thb"],
      // Bundle/Box
      ["bbfdn", "fdn"],
      // Draft/Hobby
      ["dhhob", "hob"],
      // Draft variant
      ["dftdm", "tdm"],
      // Gift variant
      ["gftdm", "tdm"],
      // Promo/Prerelease
      ["pltr", "ltr"],
      // Vault/Visual
      ["vvow", "vow"],
      // Special Commander
      ["schob", "hob"],
      ["schoc", "hoc"],
      // Art Series
      ["ashob", "hob"],
    ];

    it.each(cases)("%s -> %s", (input, expected) => {
      expect(mapToScryfallSetCode(input)).toBe(expected);
    });
  });

  describe("Secret Lair codes", () => {
    it.each(["sld158", "sld1", "sld99999", "SLD42"])("%s -> sld", (code) => {
      expect(mapToScryfallSetCode(code)).toBe("sld");
    });
  });

  describe("standard codes pass through unchanged", () => {
    it.each(["dmr", "dmu", "ltr", "clb", "snc", "2x2"])("%s unchanged", (code) => {
      expect(mapToScryfallSetCode(code)).toBe(code);
    });
  });

  describe("unknown codes return unchanged", () => {
    it.each(["xyz", "unknown123", "a", ""])("%s returns lowercased", (code) => {
      expect(mapToScryfallSetCode(code)).toBe(code.toLowerCase());
    });
  });

  describe("case-insensitive", () => {
    const cases: [string, string][] = [
      ["BLDMR", "dmr"],
      ["BLdmr", "dmr"],
      ["Bldmr", "dmr"],
      ["EXDMU", "dmu"],
      ["SLD158", "sld"],
      ["DMR", "dmr"],
    ];

    it.each(cases)("%s -> %s", (input, expected) => {
      expect(mapToScryfallSetCode(input)).toBe(expected);
    });
  });

  describe("prefix-stripping heuristic for unknown codes", () => {
    const cases: [string, string][] = [
      ["blxyz", "xyz"],
      ["exabc", "abc"],
      ["eaqrs", "qrs"],
      ["skfoo", "foo"],
      ["febar", "bar"],
    ];

    it.each(cases)("%s -> %s", (input, expected) => {
      expect(mapToScryfallSetCode(input)).toBe(expected);
    });
  });
});
