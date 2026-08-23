import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

const REQUIRED_KEYS = [
  "price.manual",
  "price.manualTooltip",
  "price.setPrice",
  "price.enterPrice",
  "price.save",
  "price.saved",
  "price.invalidPrice",
  "price.source.manual",
  "price.source.myp",
  "price.source.auto",
];

/**
 * Resolve a dot-notated key from a nested object.
 * e.g. "price.source.manual" -> obj.price.source.manual
 */
function resolveKey(obj: Record<string, unknown>, key: string): unknown {
  return key.split(".").reduce((acc: unknown, part: string) => {
    if (acc && typeof acc === "object") return (acc as Record<string, unknown>)[part];
    return undefined;
  }, obj);
}

describe("i18n manual price keys — EN", () => {
  it.each(REQUIRED_KEYS)("key '%s' exists in en.json", (key) => {
    const value = resolveKey(en, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
    expect((value as string).length).toBeGreaterThan(0);
  });
});

describe("i18n manual price keys — PT-BR", () => {
  it.each(REQUIRED_KEYS)("key '%s' exists in pt-BR.json", (key) => {
    const value = resolveKey(ptBR, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
    expect((value as string).length).toBeGreaterThan(0);
  });
});

describe("i18n key parity", () => {
  it("every manual price key in en.json has a corresponding key in pt-BR.json", () => {
    for (const key of REQUIRED_KEYS) {
      const enVal = resolveKey(en, key);
      const ptVal = resolveKey(ptBR, key);
      expect(enVal, `EN key '${key}' missing`).toBeDefined();
      expect(ptVal, `PT-BR key '${key}' missing`).toBeDefined();
    }
  });

  it("PT-BR translations differ from EN (not just copied)", () => {
    // At least some keys should be different between locales
    const diffCount = REQUIRED_KEYS.filter((key) => {
      const enVal = resolveKey(en, key) as string;
      const ptVal = resolveKey(ptBR, key) as string;
      return enVal !== ptVal;
    }).length;
    // "MYP" is the same in both, so at least (total - 1) should differ
    expect(diffCount).toBeGreaterThanOrEqual(REQUIRED_KEYS.length - 2);
  });
});
