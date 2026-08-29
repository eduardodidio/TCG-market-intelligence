import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

/**
 * F89 Batch Collection Management — i18n key verification.
 * Ensures all keys added by T03 (inlineEdit), T04 (batchAdd), and T05 (bulk)
 * exist in both EN and PT-BR locale files.
 */

const INLINE_EDIT_KEYS = [
  "inlineEdit.edit",
  "inlineEdit.save",
  "inlineEdit.saveError",
  "inlineEdit.invalidValue",
  "inlineEdit.empty",
  "inlineEdit.quantity",
  "inlineEdit.increase",
  "inlineEdit.decrease",
  "inlineEdit.deleteEntry",
  "inlineEdit.deleteConfirm",
  "inlineEdit.deleteConfirmNamed",
  "inlineEdit.deleteSuccess",
  "inlineEdit.deleteError",
  "inlineEdit.qualityLabel",
  "inlineEdit.languageLabel",
  "inlineEdit.extrasLabel",
  "inlineEdit.quantityLabel",
];

const BATCH_ADD_KEYS = [
  "batchAdd.title",
  "batchAdd.addCards",
  "batchAdd.pasteLabel",
  "batchAdd.placeholder",
  "batchAdd.preview",
  "batchAdd.lines",
  "batchAdd.overLimitWarning",
  "batchAdd.formatHelpToggle",
  "batchAdd.formatHelpTitle",
  "batchAdd.formatRule1",
  "batchAdd.formatRule2",
  "batchAdd.formatRule3",
  "batchAdd.formatRule4",
  "batchAdd.valid",
  "batchAdd.errors",
  "batchAdd.colQty",
  "batchAdd.colName",
  "batchAdd.colSet",
  "batchAdd.colCondition",
  "batchAdd.colLanguage",
  "batchAdd.colExtras",
  "batchAdd.removeRow",
  "batchAdd.addNCards",
  "batchAdd.addNCards_one",
  "batchAdd.resultAdded",
  "batchAdd.resultAdded_one",
  "batchAdd.resultErrors",
  "batchAdd.resultErrors_one",
  "batchAdd.close",
];

const BULK_KEYS = [
  "bulk.select",
  "bulk.selectAll",
  "bulk.deselectAll",
  "bulk.selectedCount",
  "bulk.selectedCount_one",
  "bulk.setCondition",
  "bulk.setLanguage",
  "bulk.setExtras",
  "bulk.extrasPlaceholder",
  "bulk.apply",
  "bulk.deleteTitle",
  "bulk.deleteMessage",
  "bulk.updateSuccess",
  "bulk.deleteSuccess",
];

const ALL_KEYS = [...INLINE_EDIT_KEYS, ...BATCH_ADD_KEYS, ...BULK_KEYS];

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

describe("F89 Batch CRUD i18n keys", () => {
  describe("inlineEdit keys", () => {
    it.each(INLINE_EDIT_KEYS)("EN has key: %s", (key) => {
      const value = getNestedValue(en, key);
      expect(value).toBeDefined();
      expect(typeof value).toBe("string");
    });

    it.each(INLINE_EDIT_KEYS)("PT-BR has key: %s", (key) => {
      const value = getNestedValue(ptBR, key);
      expect(value).toBeDefined();
      expect(typeof value).toBe("string");
    });
  });

  describe("batchAdd keys", () => {
    it.each(BATCH_ADD_KEYS)("EN has key: %s", (key) => {
      const value = getNestedValue(en, key);
      expect(value).toBeDefined();
      expect(typeof value).toBe("string");
    });

    it.each(BATCH_ADD_KEYS)("PT-BR has key: %s", (key) => {
      const value = getNestedValue(ptBR, key);
      expect(value).toBeDefined();
      expect(typeof value).toBe("string");
    });
  });

  describe("bulk keys", () => {
    it.each(BULK_KEYS)("EN has key: %s", (key) => {
      const value = getNestedValue(en, key);
      expect(value).toBeDefined();
      expect(typeof value).toBe("string");
    });

    it.each(BULK_KEYS)("PT-BR has key: %s", (key) => {
      const value = getNestedValue(ptBR, key);
      expect(value).toBeDefined();
      expect(typeof value).toBe("string");
    });
  });

  it("EN and PT-BR locale files have identical key sets", () => {
    const enKeys = new Set(collectLeafKeys(en as Record<string, unknown>));
    const ptKeys = new Set(collectLeafKeys(ptBR as Record<string, unknown>));

    const missingInPt = [...enKeys].filter((k) => !ptKeys.has(k));
    const missingInEn = [...ptKeys].filter((k) => !enKeys.has(k));

    expect(missingInPt).toEqual([]);
    expect(missingInEn).toEqual([]);
  });

  it("no F89 key has an empty string value in EN", () => {
    for (const key of ALL_KEYS) {
      const value = getNestedValue(en, key);
      expect(value, `EN key "${key}" should not be empty`).not.toBe("");
    }
  });

  it("no F89 key has an empty string value in PT-BR", () => {
    for (const key of ALL_KEYS) {
      const value = getNestedValue(ptBR, key);
      expect(value, `PT-BR key "${key}" should not be empty`).not.toBe("");
    }
  });
});
