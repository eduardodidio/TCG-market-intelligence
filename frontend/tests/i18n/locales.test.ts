import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

function collectLeafKeys(obj: Record<string, unknown>, prefix = ""): string[] {
  const keys: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (v && typeof v === "object" && !Array.isArray(v)) {
      keys.push(...collectLeafKeys(v as Record<string, unknown>, path));
    } else {
      keys.push(path);
    }
  }
  return keys;
}

describe("i18n locale parity", () => {
  it("EN and PT-BR have the same number of leaf keys", () => {
    const enKeys = collectLeafKeys(en as Record<string, unknown>).sort();
    const ptKeys = collectLeafKeys(ptBR as Record<string, unknown>).sort();
    expect(enKeys.length).toBe(ptKeys.length);
  });

  it("EN and PT-BR have identical key sets", () => {
    const enKeys = new Set(collectLeafKeys(en as Record<string, unknown>));
    const ptKeys = new Set(collectLeafKeys(ptBR as Record<string, unknown>));

    const missingInPt = [...enKeys].filter((k) => !ptKeys.has(k));
    const missingInEn = [...ptKeys].filter((k) => !enKeys.has(k));

    expect(missingInPt).toEqual([]);
    expect(missingInEn).toEqual([]);
  });
});
