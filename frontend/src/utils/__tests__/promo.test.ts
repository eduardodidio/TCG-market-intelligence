import { describe, it, expect } from "vitest";
import { isPromoCard } from "../promo";

describe("isPromoCard", () => {
  it('returns true for 4-char set code starting with "p" (pone)', () => {
    expect(isPromoCard("pone", null)).toBe(true);
  });

  it('returns true for 4-char set code starting with "p" (pltr)', () => {
    expect(isPromoCard("pltr", null)).toBe(true);
  });

  it('returns true for 4-char set code starting with "p" (pmkm)', () => {
    expect(isPromoCard("pmkm", null)).toBe(true);
  });

  it('returns false for 3-char set code "pip" (real set)', () => {
    expect(isPromoCard("pip", null)).toBe(false);
  });

  it('returns false for 3-char set code "pca" (real set)', () => {
    expect(isPromoCard("pca", null)).toBe(false);
  });

  it("returns false for non-promo set code", () => {
    expect(isPromoCard("fdn", null)).toBe(false);
  });

  it("returns false when both args are null", () => {
    expect(isPromoCard(null, null)).toBe(false);
  });

  it('returns true when extras contains "Promo" (case-insensitive)', () => {
    expect(isPromoCard("fdn", "Foil, Promo")).toBe(true);
  });

  it('returns false when extras does not contain "promo"', () => {
    expect(isPromoCard("fdn", "foil")).toBe(false);
  });

  it('returns true when setCode is null but extras contains "promo"', () => {
    expect(isPromoCard(null, "promo pack")).toBe(true);
  });

  it("returns false for undefined inputs", () => {
    expect(isPromoCard(undefined, undefined)).toBe(false);
  });

  it('returns true for uppercase set code starting with "P" (4+ chars)', () => {
    expect(isPromoCard("PONE", null)).toBe(true);
  });

  it("returns true when both set code and extras match", () => {
    expect(isPromoCard("pone", "Promo")).toBe(true);
  });
});
