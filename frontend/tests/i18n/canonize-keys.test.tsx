import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

const CANONIZE_KEYS = [
  "collection.canonizeAll",
  "collection.canonizeAllDescription",
  "collection.unlinkedCount",
  "collection.canonizeResult",
  "collection.canonizeFailed",
  "collection.canonizing",
  "collection.canonizeScheduled",
];

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

describe("F49 i18n canonize keys", () => {
  it.each(CANONIZE_KEYS)("EN has key: %s", (key) => {
    const value = getNestedValue(en, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
  });

  it.each(CANONIZE_KEYS)("PT-BR has key: %s", (key) => {
    const value = getNestedValue(ptBR, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
  });
});
