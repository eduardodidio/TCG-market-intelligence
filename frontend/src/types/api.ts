// TypeScript interfaces mirroring the backend Pydantic schemas (F06 REST API)

export interface ApiError {
  code: string;
  message: string;
  field?: string;
}

export interface ApiMeta {
  cursor: string | null;
  total: number | null;
  request_id: string;
}

export interface ApiResponse<T> {
  data: T | null;
  meta: ApiMeta;
  errors: ApiError[];
}

// Card types

export interface CardSummary {
  id: number;
  game: string;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  latest_price: number | null;
}

export interface SourceCard {
  source: string;
  external_id: string;
  sku: string | null;
  url: string;
}

export interface CardDetail extends CardSummary {
  source_cards: SourceCard[];
  created_at: string;
  updated_at: string;
}

export interface PriceObservation {
  observed_at: string;
  median_price: number | null;
  tcg_price: number | null;
  last_sold_price: number | null;
  quantity_available: number | null;
  currency: string;
}

// Set types

export interface SetSummary {
  set_code: string;
  game: string;
  card_count: number;
}

// Market types

export interface MoverEntry {
  card_id: number;
  name_en: string;
  set_code: string | null;
  price_start: number;
  price_end: number;
  change_pct: number;
}

export interface MoversResponse {
  gainers: MoverEntry[];
  losers: MoverEntry[];
}

export interface MarketStats {
  total_cards: number;
  total_observations: number;
  avg_price: number | null;
  date_range_start: string | null;
  date_range_end: string | null;
}

// User collection types

export interface CollectionCard {
  id: number;
  card_id: number | null;
  set_code: string;
  collector_number: string;
  name_en: string | null;
  name_pt: string | null;
  set_name_en: string | null;
  quantity: number;
  quality: string | null;
  language: string | null;
  rarity: string | null;
  color: string | null;
  extras: string | null;
  latest_price: number | null;
  image_url: string | null;
}

export interface CollectionCardDetail extends CollectionCard {
  price_history: PriceObservation[];
  source_cards: SourceCard[];
  scryfall_url: string | null;
  ligamagic_url: string | null;
}

export interface CollectionSummary {
  total_unique: number;
  total_cards: number;
  total_value: number | null;
  linked_count: number;
  sets_count: number;
}

// Collection health types

export interface CollectionHealth {
  last_collection_at: string | null;
  next_expected_at: string | null;
  total_cards: number;
  stale_cards_count: number;
  recent_errors_count: number;
  status: "healthy" | "stale" | "error";
}

// Scan types

export interface ScanRun {
  id: number;
  scan_type: string;
  filters_json: string;
  status: string;
  cards_total: number;
  cards_processed: number;
  cards_failed: number;
  observations_saved: number;
  error_summary: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
}

export interface ScanListResponse {
  scans: ScanRun[];
  total: number;
}

export interface ScanTriggerResponse {
  scan_id: number;
  status: string;
}

export interface ScanRequest {
  scan_type: string;
  set_codes?: string[];
  format_name?: string;
  rarities?: string[];
  card_ids?: number[];
  limit?: number;
  dry_run?: boolean;
}
