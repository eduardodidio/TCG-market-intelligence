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
