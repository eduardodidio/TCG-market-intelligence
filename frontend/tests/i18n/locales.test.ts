import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

const LIGA_KEYS = [
  "nav.admin",
  "nav.ligaStatus",
  "admin.ligaStatus.title",
  "admin.ligaStatus.totalCards",
  "admin.ligaStatus.ligaPriced",
  "admin.ligaStatus.ligaMissing",
  "admin.ligaStatus.ligaStale",
  "admin.ligaStatus.coverage",
  "admin.ligaStatus.scanAllMissing",
  "admin.ligaStatus.lastScan",
  "admin.ligaStatus.unlinked",
  "admin.ligaStatus.noMissing",
  "card.refreshLiga",
  "card.refreshMyp",
  "card.priceSource.liga",
  "card.priceSource.myp",
  "card.priceSource.manual",
  "scan.provider.liga",
  "scan.provider.myp",
];

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

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

describe("F60-T09 Liga i18n keys", () => {
  it.each(LIGA_KEYS)("EN has key: %s", (key) => {
    const value = getNestedValue(en, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
  });

  it.each(LIGA_KEYS)("PT-BR has key: %s", (key) => {
    const value = getNestedValue(ptBR, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
  });

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
