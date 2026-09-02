import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

/** Flatten nested JSON keys into dot-notation strings */
function flattenKeys(obj: Record<string, unknown>, prefix = ""): string[] {
  const keys: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "object" && value !== null && !Array.isArray(value)) {
      keys.push(...flattenKeys(value as Record<string, unknown>, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys;
}

describe("i18n completeness", () => {
  const enKeys = flattenKeys(en);
  const ptBRKeys = flattenKeys(ptBR);

  it("all keys in en.json exist in pt-BR.json", () => {
    const ptBRKeySet = new Set(ptBRKeys);
    const missingInPtBR = enKeys.filter((k) => !ptBRKeySet.has(k));
    expect(missingInPtBR).toEqual([]);
  });

  it("all keys in pt-BR.json exist in en.json", () => {
    const enKeySet = new Set(enKeys);
    const missingInEn = ptBRKeys.filter((k) => !enKeySet.has(k));
    expect(missingInEn).toEqual([]);
  });

  it("all onboarding.* keys are non-empty strings in both locales", () => {
    const onboardingKeys = enKeys.filter((k) => k.startsWith("onboarding."));
    expect(onboardingKeys.length).toBeGreaterThan(0);

    for (const key of onboardingKeys) {
      const parts = key.split(".");
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let enVal: any = en;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let ptVal: any = ptBR;
      for (const part of parts) {
        enVal = enVal?.[part];
        ptVal = ptVal?.[part];
      }
      expect(typeof enVal).toBe("string");
      expect(enVal.length).toBeGreaterThan(0);
      expect(typeof ptVal).toBe("string");
      expect(ptVal.length).toBeGreaterThan(0);
    }
  });
});
