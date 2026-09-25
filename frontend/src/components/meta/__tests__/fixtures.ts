import type { ApiResponse } from "../../../types/api";
import type { MetaDeckCard, MetaDeckSummary } from "../../../types/metaDecks";

export function ok<T>(data: T): ApiResponse<T> {
  return { data, meta: { cursor: null, total: null, offset: null, request_id: "t" }, errors: [] };
}

export function fail<T>(message = "boom"): ApiResponse<T> {
  return {
    data: null,
    meta: { cursor: null, total: null, offset: null, request_id: "t" },
    errors: [{ code: "ERR", message }],
  };
}

export function makeDeck(overrides: Partial<MetaDeckSummary> = {}): MetaDeckSummary {
  return {
    id: 1,
    rank: 1,
    archetype: "Boros Energy",
    commander_name: null,
    colors: "RW",
    meta_share_pct: 12.5,
    deck_count: null,
    source: "MTGGoldfish",
    source_url: "https://example.com/deck/1",
    event_date: null,
    snapshot_date: "2026-09-24",
    total_value_brl: 1234.5,
    priced_pct: 100,
    owned_pct: 40,
    missing_value_brl: 700,
    total_copies: 75,
    ...overrides,
  };
}

export function makeCard(overrides: Partial<MetaDeckCard> = {}): MetaDeckCard {
  return {
    name: "Lightning Bolt",
    quantity: 4,
    board: "main",
    card_id: 10,
    price_brl: 5,
    owned_qty: 4,
    ...overrides,
  };
}
