import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

const BAN_HISTORY_KEYS = [
  "banHistory.title",
  "banHistory.timeline",
  "banHistory.subtitle",
  "banHistory.noEvents",
  "banHistory.noEventsCard",
  "banHistory.loadMore",
  "banHistory.showing",
  "banHistory.allFormats",
  "banHistory.dateFrom",
  "banHistory.dateTo",
  "banHistory.transition.banned",
  "banHistory.transition.unbanned",
  "banHistory.transition.restricted",
  "banHistory.transition.initial",
  "banHistory.impact.title",
  "banHistory.impact.unavailable",
  "banHistory.impact.before",
  "banHistory.impact.after",
  "banHistory.impact.change",
  "nav.banHistory",
];

function getNestedValue(obj: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object" && key in (acc as Record<string, unknown>)) {
      return (acc as Record<string, unknown>)[key];
    }
    return undefined;
  }, obj);
}

describe("F43 i18n keys", () => {
  it.each(BAN_HISTORY_KEYS)("EN has key: %s", (key) => {
    const value = getNestedValue(en, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
  });

  it.each(BAN_HISTORY_KEYS)("PT-BR has key: %s", (key) => {
    const value = getNestedValue(ptBR, key);
    expect(value).toBeDefined();
    expect(typeof value).toBe("string");
  });
});
