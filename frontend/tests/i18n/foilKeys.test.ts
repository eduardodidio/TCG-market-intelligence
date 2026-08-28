import { describe, it, expect } from "vitest";
import en from "../../src/i18n/locales/en.json";
import ptBR from "../../src/i18n/locales/pt-BR.json";

describe("Foil i18n keys", () => {
  it("EN locale has card.foil key", () => {
    expect(en.card.foil).toBe("Foil");
  });

  it("EN locale has card.foilPrice key", () => {
    expect(en.card.foilPrice).toBe("Foil price");
  });

  it("PT-BR locale has card.foil key", () => {
    expect(ptBR.card.foil).toBe("Foil");
  });

  it("PT-BR locale has card.foilPrice key", () => {
    expect(ptBR.card.foilPrice).toBe("Preco Foil");
  });
});
