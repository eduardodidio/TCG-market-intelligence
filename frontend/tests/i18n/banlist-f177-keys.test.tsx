import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

const BANLIST_F177_KEYS = [
  "banlist.ownedOnly",
  "banlist.ownedOnlyLoginHint",
  "banlist.owned",
  "banlist.ownedQty",
  "banlist.printings",
  "banlist.emptyNotSynced",
  "banlist.emptyOwned",
  "banlist.lastSynced",
  "banlist.loadMore",
  "banlist.detail.title",
  "banlist.detail.legalities",
  "banlist.detail.history",
  "banlist.detail.noHistory",
  "banlist.detail.baseline",
  "banlist.detail.close",
  "banlist.detail.openCard",
];

const INTERPOLATED_KEYS: Record<string, string[]> = {
  "banlist.ownedQty": ["{{count}}"],
  "banlist.printings": ["{{count}}"],
  "banlist.lastSynced": ["{{date}}"],
};

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

describe("F177 banlist i18n keys", () => {
  it.each(BANLIST_F177_KEYS)("EN has non-empty key: %s", (key) => {
    const value = getNestedValue(en, key);
    expect(value, `missing EN key: ${key}`).toBeDefined();
    expect(typeof value).toBe("string");
    expect((value as string).length, `EN key ${key} is empty`).toBeGreaterThan(0);
  });

  it.each(BANLIST_F177_KEYS)("PT-BR has non-empty key: %s", (key) => {
    const value = getNestedValue(ptBR, key);
    expect(value, `missing PT-BR key: ${key}`).toBeDefined();
    expect(typeof value).toBe("string");
    expect((value as string).length, `PT-BR key ${key} is empty`).toBeGreaterThan(0);
  });

  it("PT-BR ownedOnly reads 'Somente minha coleção'", () => {
    expect((ptBR as { banlist: { ownedOnly: string } }).banlist.ownedOnly).toBe(
      "Somente minha coleção"
    );
  });

  it.each(Object.entries(INTERPOLATED_KEYS))(
    "%s keeps interpolation placeholders in both locales",
    (key, placeholders) => {
      const enValue = getNestedValue(en, key) as string;
      const ptValue = getNestedValue(ptBR, key) as string;
      for (const placeholder of placeholders) {
        expect(enValue).toContain(placeholder);
        expect(ptValue).toContain(placeholder);
      }
    }
  );

  it("banlist.detail is a nested object, not flattened", () => {
    const enDetail = (en as { banlist: { detail?: unknown } }).banlist.detail;
    const ptDetail = (ptBR as { banlist: { detail?: unknown } }).banlist.detail;
    expect(typeof enDetail).toBe("object");
    expect(typeof ptDetail).toBe("object");
    expect((en as { banlist: Record<string, unknown> }).banlist["detail.title"]).toBeUndefined();
  });
});
