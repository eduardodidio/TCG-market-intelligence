// F173 — Metagame top decks. Mirrors `src/api/routers/meta_decks.py` schemas
// (snake_case; money and percentages serialized as numbers, null when unknown).

export const META_FORMATS = [
  "commander",
  "standard",
  "pioneer",
  "modern",
  "legacy",
  "pauper",
  "vintage",
] as const;

export type MetaFormat = (typeof META_FORMATS)[number];

export interface MetaFormatInfo {
  format: MetaFormat;
  latest_snapshot_date: string | null;
  deck_count: number;
}

export interface MetaFormatsResponse {
  formats: MetaFormatInfo[];
}

export interface MetaDeckSummary {
  id: number;
  rank: number;
  archetype: string;
  commander_name: string | null;
  colors: string | null;
  meta_share_pct: number | null;
  deck_count: number | null;
  source: string;
  source_url: string;
  event_date: string | null;
  snapshot_date: string;
  total_value_brl: number | null;
  priced_pct: number | null;
  /** null when the request is anonymous. */
  owned_pct: number | null;
  missing_value_brl: number | null;
  total_copies: number;
}

export interface MetaDeckListResponse {
  format: MetaFormat;
  snapshot_date: string | null;
  source: string | null;
  total: number;
  decks: MetaDeckSummary[];
}

export interface MetaDeckCard {
  name: string;
  quantity: number;
  board: string;
  card_id: number | null;
  price_brl: number | null;
  owned_qty: number | null;
  image_url?: string | null;
}

export interface MetaDeckDetail extends MetaDeckSummary {
  cards: MetaDeckCard[];
}
