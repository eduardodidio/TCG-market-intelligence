import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

describe("pwa i18n keys", () => {
  const enKeys = Object.keys((en as Record<string, Record<string, string>>).pwa);
  const ptKeys = Object.keys((ptBR as Record<string, Record<string, string>>).pwa);

  it("en and pt-BR have the same pwa keys", () => {
    expect(enKeys.sort()).toEqual(ptKeys.sort());
  });

  it("all pwa keys have non-empty values in en", () => {
    for (const key of enKeys) {
      const val = (en as Record<string, Record<string, string>>).pwa[key];
      expect(val, `pwa.${key} should be non-empty`).toBeTruthy();
    }
  });

  it("all pwa keys have non-empty values in pt-BR", () => {
    for (const key of ptKeys) {
      const val = (ptBR as Record<string, Record<string, string>>).pwa[key];
      expect(val, `pwa.${key} should be non-empty`).toBeTruthy();
    }
  });

  it("contains all expected keys", () => {
    const expected = [
      "updateAvailable",
      "update",
      "dismiss",
      "offlineMessage",
      "installMessage",
      "install",
    ];
    for (const key of expected) {
      expect(enKeys, `missing key: ${key}`).toContain(key);
    }
  });
});
