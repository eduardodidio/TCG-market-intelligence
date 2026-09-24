import { describe, it, expect } from "vitest";
import { filterCardList, sortCardList, buildSetOptions } from "../cardListFilter";
import type { CardListAccessors } from "../cardListFilter";

interface MixedCard {
  name: string | null;
  namePt?: string | null;
  set: string | null;
  number?: string | null;
  price?: number | null;
  date?: string | null;
  status?: string | null;
}

const acc: CardListAccessors<MixedCard> = {
  name: (i) => i.name,
  namePt: (i) => i.namePt,
  setCode: (i) => i.set,
  number: (i) => i.number,
  price: (i) => i.price,
  date: (i) => i.date,
  status: (i) => i.status,
};

function mixedCardListFixture(): MixedCard[] {
  return [
    { name: "Lightning Bolt", namePt: "Raio", set: "M11", number: "1", price: 5, date: "2024-01-01", status: "pending" },
    { name: "Relâmpago Especial", namePt: null, set: "m11", number: "10a", price: null, date: "2024-01-03", status: "accepted" },
    { name: "Counterspell", namePt: "Contramágica", set: "STX", number: "10", price: 2, date: null, status: null },
    { name: "Divine Smite", namePt: null, set: "STX", number: "2", price: 8, date: "2024-01-02", status: "completed" },
    { name: null, namePt: null, set: null, number: null, price: null, date: null, status: null },
  ];
}

describe("filterCardList", () => {
  it("filters by search + set (happy path)", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { search: "bolt", set: "M11" }, acc);
    expect(result).toEqual([items[0]]);
  });

  it("matches accented search 'relampago' against 'Relâmpago Especial'", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { search: "relampago" }, acc);
    expect(result).toEqual([items[1]]);
  });

  it("matches search against namePt", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { search: "contramagica" }, acc);
    expect(result).toEqual([items[2]]);
  });

  it("is case-insensitive for set comparison", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { set: "stx" }, acc);
    expect(result).toEqual([items[2], items[3]]);
  });

  it("filters by status when accessor is provided", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { status: "pending" }, acc);
    expect(result).toEqual([items[0]]);
  });

  it("ignores status filter when accessor is missing", () => {
    const items = mixedCardListFixture();
    const accNoStatus: CardListAccessors<MixedCard> = { ...acc, status: undefined };
    const result = filterCardList(items, { status: "pending" }, accNoStatus);
    expect(result).toEqual(items);
  });

  it("ignores a search string that is only whitespace", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { search: "   " }, acc);
    expect(result).toEqual(items);
  });

  it("excludes items with null set when a set filter is applied", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { set: "m11" }, acc);
    expect(result).toEqual([items[0], items[1]]);
  });

  it("excludes items with null name/namePt when searching", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, { search: "anything" }, acc);
    expect(result).toEqual([]);
  });

  it("returns an empty array unchanged for an empty input array", () => {
    const result = filterCardList([], { search: "bolt" }, acc);
    expect(result).toEqual([]);
  });

  it("returns all items when no filters are given", () => {
    const items = mixedCardListFixture();
    const result = filterCardList(items, {}, acc);
    expect(result).toEqual(items);
  });

  it("does not mutate the input array", () => {
    const items = mixedCardListFixture();
    const copy = [...items];
    filterCardList(items, { search: "bolt" }, acc);
    expect(items).toEqual(copy);
  });
});

describe("sortCardList", () => {
  it("sorts by price desc after filtering (happy path)", () => {
    const items = mixedCardListFixture();
    const filtered = filterCardList(items, {}, acc);
    const result = sortCardList(filtered, "price", "desc", acc);
    expect(result.map((i) => i.name)).toEqual([
      "Divine Smite",
      "Lightning Bolt",
      "Counterspell",
      "Relâmpago Especial",
      null,
    ]);
  });

  it("sorts by price asc with nulls last", () => {
    const items = mixedCardListFixture();
    const result = sortCardList(items, "price", "asc", acc);
    expect(result.map((i) => i.name)).toEqual([
      "Counterspell",
      "Lightning Bolt",
      "Divine Smite",
      "Relâmpago Especial",
      null,
    ]);
  });

  it("sorts by name asc with nulls last", () => {
    const items = mixedCardListFixture();
    const result = sortCardList(items, "name", "asc", acc);
    expect(result.map((i) => i.name)).toEqual([
      "Counterspell",
      "Divine Smite",
      "Lightning Bolt",
      "Relâmpago Especial",
      null,
    ]);
  });

  it("sorts by name desc with nulls last (nulls last in both directions)", () => {
    const items = mixedCardListFixture();
    const result = sortCardList(items, "name", "desc", acc);
    expect(result.map((i) => i.name)).toEqual([
      "Relâmpago Especial",
      "Lightning Bolt",
      "Divine Smite",
      "Counterspell",
      null,
    ]);
  });

  it("sorts by set asc with nulls last", () => {
    const items = mixedCardListFixture();
    const result = sortCardList(items, "set", "asc", acc);
    expect(result.map((i) => i.set)).toEqual(["m11", "M11", "STX", "STX", null]);
  });

  it("sorts by date asc with nulls last", () => {
    const items = mixedCardListFixture();
    const result = sortCardList(items, "date", "asc", acc);
    expect(result.map((i) => i.date)).toEqual([
      "2024-01-01",
      "2024-01-02",
      "2024-01-03",
      null,
      null,
    ]);
  });

  it("sorts by status asc with nulls last", () => {
    const items = mixedCardListFixture();
    const result = sortCardList(items, "status", "asc", acc);
    expect(result.map((i) => i.status)).toEqual([
      "accepted",
      "completed",
      "pending",
      null,
      null,
    ]);
  });

  it("uses natural sort for collector numbers: '2' < '10' < '10a'", () => {
    const naturalItems: MixedCard[] = [
      { name: "a", set: "X", number: "10a" },
      { name: "b", set: "X", number: "2" },
      { name: "c", set: "X", number: "10" },
    ];
    const result = sortCardList(naturalItems, "number", "asc", acc);
    expect(result.map((i) => i.number)).toEqual(["2", "10", "10a"]);
  });

  it("uses natural sort across '1','2','10','10a','★'", () => {
    const naturalItems: MixedCard[] = [
      { name: "a", set: "X", number: "10a" },
      { name: "b", set: "X", number: "★" },
      { name: "c", set: "X", number: "10" },
      { name: "d", set: "X", number: "1" },
      { name: "e", set: "X", number: "2" },
    ];
    const result = sortCardList(naturalItems, "number", "asc", acc);
    expect(result.map((i) => i.number)).toEqual(["★", "1", "2", "10", "10a"]);
  });

  it("returns a copy in original order for an unknown sortBy", () => {
    const items = mixedCardListFixture();
    const result = sortCardList(items, "unknown-field", "asc", acc);
    expect(result).toEqual(items);
    expect(result).not.toBe(items);
  });

  it("falls back to copy-in-order when accessor for sortBy is missing", () => {
    const items = mixedCardListFixture();
    const accNoPrice: CardListAccessors<MixedCard> = { ...acc, price: undefined };
    const result = sortCardList(items, "price", "asc", accNoPrice);
    expect(result).toEqual(items);
  });

  it("keeps input order for all-equal keys (stability)", () => {
    const equalItems: MixedCard[] = [
      { name: "same", set: "X", price: 1 },
      { name: "same", set: "X", price: 1 },
      { name: "same", set: "X", price: 1 },
    ];
    const result = sortCardList(equalItems, "name", "asc", acc);
    expect(result).toEqual(equalItems);
    expect(result[0]).toBe(equalItems[0]);
    expect(result[1]).toBe(equalItems[1]);
    expect(result[2]).toBe(equalItems[2]);
  });

  it("does not mutate the input array and keeps its identity unchanged", () => {
    const items = mixedCardListFixture();
    const copy = [...items];
    const result = sortCardList(items, "name", "asc", acc);
    expect(items).toEqual(copy);
    expect(result).not.toBe(items);
  });

  it("handles a single-item array", () => {
    const single: MixedCard[] = [{ name: "Solo", set: "X" }];
    const result = sortCardList(single, "name", "asc", acc);
    expect(result).toEqual(single);
  });

  it("handles an empty array", () => {
    const result = sortCardList([], "name", "asc", acc);
    expect(result).toEqual([]);
  });
});

describe("buildSetOptions", () => {
  it("de-duplicates, lowercases values, uppercases labels, and sorts", () => {
    const items = mixedCardListFixture();
    const result = buildSetOptions(items, acc);
    expect(result).toEqual([
      { value: "m11", label: "M11" },
      { value: "stx", label: "STX" },
    ]);
  });

  it("ignores items with a null set", () => {
    const items: MixedCard[] = [{ name: "a", set: null }, { name: "b", set: "abc" }];
    const result = buildSetOptions(items, acc);
    expect(result).toEqual([{ value: "abc", label: "ABC" }]);
  });

  it("returns an empty array for an empty input array", () => {
    const result = buildSetOptions([], acc);
    expect(result).toEqual([]);
  });
});
