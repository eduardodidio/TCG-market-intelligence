import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

const F96_CREDIT_KEYS = [
  "earnInfo",
  "claimBonusModal",
  "bonusClaimed",
  "costBadge",
  "refreshCostTooltip",
  "approxCost",
];

const F96_SCHEDULE_KEYS = [
  "creditPauseTooltip",
  "creditPauseHint",
];

describe("F96 i18n keys — EN", () => {
  it("all credit keys exist in EN locale", () => {
    for (const key of F96_CREDIT_KEYS) {
      expect(
        (en.credits as Record<string, string>)[key],
        `Missing EN key: credits.${key}`,
      ).toBeDefined();
    }
  });

  it("all schedule keys exist in EN locale", () => {
    for (const key of F96_SCHEDULE_KEYS) {
      expect(
        (en.schedules as Record<string, string>)[key],
        `Missing EN key: schedules.${key}`,
      ).toBeDefined();
    }
  });
});

describe("F96 i18n keys — PT-BR", () => {
  it("all credit keys exist in PT-BR locale", () => {
    for (const key of F96_CREDIT_KEYS) {
      expect(
        (ptBR.credits as Record<string, string>)[key],
        `Missing PT-BR key: credits.${key}`,
      ).toBeDefined();
    }
  });

  it("all schedule keys exist in PT-BR locale", () => {
    for (const key of F96_SCHEDULE_KEYS) {
      expect(
        (ptBR.schedules as Record<string, string>)[key],
        `Missing PT-BR key: schedules.${key}`,
      ).toBeDefined();
    }
  });
});
