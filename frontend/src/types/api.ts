// TypeScript interfaces mirroring the backend Pydantic schemas (F06 REST API)

export interface ApiError {
  code: string;
  message: string;
  field?: string;
}

export interface ApiMeta {
  cursor: string | null;
  total: number | null;
  offset: number | null;
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
  currency?: string;
}

export interface SourceCard {
  source: string;
  external_id: string;
  sku: string | null;
  url: string;
}

export interface CardDetail extends CardSummary {
  source_cards: SourceCard[];
  collection_entry_id: number | null;
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

export interface PriceChangeSummary {
  period: string;
  price_start: number | null;
  price_end: number | null;
  absolute_change: number | null;
  percent_change: number | null;
  data_points: number;
  resolution: string;
}

export interface PriceHistoryResponse {
  observations: PriceObservation[];
  summary: PriceChangeSummary | null;
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
  name_pt?: string;
  set_code: string | null;
  price_start: number;
  price_end: number;
  change_pct: number;
  currency?: string;
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
  currency?: string;
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
  is_foil: boolean;
  latest_price: number | null;
  price_source?: string | null;
  currency?: string;
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
  priced_count: number;
  sets_count: number;
  currency?: string;
  banned_count: number;
  recently_changed_count: number;
}

// Ban engine types (F42)

export interface BannedCollectionCard {
  entry_id: number;
  card_id: number;
  name_en: string | null;
  name_pt: string | null;
  set_code: string;
  collector_number: string;
  quantity: number;
  format: string;
  status: string;
  effective_date: string | null;
  recently_changed: boolean;
  change_date: string | null;
  image_url: string | null;
}

export interface BanSummary {
  banned_count: number;
  restricted_count: number;
  recently_changed_count: number;
  formats_affected: string[];
}

export interface CardLegalityWithChange {
  format: string;
  status: string;
  effective_date: string | null;
  recently_changed: boolean;
  change_date: string | null;
  old_status: string | null;
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
  provider?: string;
  set_codes?: string[];
  format_name?: string;
  rarities?: string[];
  card_ids?: number[];
  limit?: number;
  dry_run?: boolean;
  max_age_days?: number;
}

export interface ScanPreviewResponse {
  card_count: number;
  skipped_count: number;
  credit_cost: number;
}

// Deck types

export interface DeckSummary {
  id: number;
  name: string;
  description: string | null;
  total_cards: number;
  unique_cards: number;
  owned_cards: number;
  ownership_pct: number;
  total_value: number | null;
  value_change_pct: number | null;
  created_at: string;
  updated_at: string;
}

export interface DeckCard {
  id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  quantity: number;
  card_id: number | null;
  in_collection: boolean;
  owned_quantity: number;
  collection_entry_id: number | null;
  image_url: string | null;
  latest_price: number | null;
}

export interface DeckDetail {
  id: number;
  name: string;
  description: string | null;
  cards: DeckCard[];
  total_cards: number;
  unique_cards: number;
  owned_cards: number;
  ownership_pct: number;
  created_at: string;
  updated_at: string;
}

export interface DeckImportResult {
  deck_id: number;
  name: string;
  cards_imported: number;
  cards_linked: number;
}

// Schedule types

export interface ScheduleResponse {
  id: number;
  name: string;
  description: string | null;
  cron_expression: string;
  scan_type: string;
  filters_json: string;
  status: string;
  last_run_id: number | null;
  last_run_at: string | null;
  next_run_at: string | null;
  error_count: number;
  max_retries: number;
  created_at: string;
  updated_at: string;
}

export interface ScheduleListResponse {
  schedules: ScheduleResponse[];
  total: number;
}

export interface ScheduleCreateRequest {
  name: string;
  cron_expression: string;
  scan_type?: string;
  filters_json?: string;
  description?: string;
  max_retries?: number;
}

export interface ScheduleUpdateRequest {
  name?: string;
  cron_expression?: string;
  scan_type?: string;
  filters_json?: string;
  description?: string;
  status?: string;
  max_retries?: number;
}

export interface ScheduleTriggerResponse {
  schedule_id: number;
  scan_id: number;
  status: string;
}

// Metrics types

export interface MovingAverageEntry {
  period: number;
  value: number;
}

export interface PriceExtremes {
  ath_price: number;
  ath_date: string;
  atl_price: number;
  atl_date: string;
}

export interface VolatilityData {
  period_days: number;
  std_dev: number;
  coefficient_of_variation: number;
}

export interface MomentumData {
  period_days: number;
  rate_of_change: number;
  trend_direction: "up" | "down" | "flat";
}

export interface PerformanceScoreData {
  score: number;
  label: "strong" | "moderate" | "weak" | "declining";
  period_days: number;
}

export interface PeriodComparisonData {
  current_avg: number;
  previous_avg: number;
  delta: number;
  delta_pct: number;
  period_days: number;
}

export interface CardMetricsResponse {
  entry_id: number;
  card_id: number;
  period: string;
  currency: string;
  moving_averages: MovingAverageEntry[];
  extremes: PriceExtremes | null;
  volatility: VolatilityData | null;
  momentum: MomentumData | null;
  performance: PerformanceScoreData | null;
  period_comparison: PeriodComparisonData | null;
  data_points: number;
}

// Auth types

export interface UserProfile {
  id: number;
  email: string;
  display_name: string | null;
  avatar_url: string | null;
  auth_provider: string;
  preferred_language: string | null;
  is_active: boolean;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// Trending types (F36)

export interface TrendingCardEntry {
  card_id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  image_url: string | null;
  price_start: number;
  price_end: number;
  change_pct: number;
  change_abs: number;
  consistency: number;
  composite_score: number;
  observation_count: number;
  currency: string;
}

export interface TrendingResponse {
  cards: TrendingCardEntry[];
  period: string;
  direction: "up" | "down";
  computed_at: string;
  cached: boolean;
}

// Deck ranking types (F35)

export interface DeckRankingEntry {
  id: number;
  name: string;
  description: string | null;
  total_cards: number;
  unique_cards: number;
  owned_cards: number;
  ownership_pct: number;
  total_value: number | null;
  priced_cards: number;
  unpriced_cards: number;
  value_change: number | null;
  value_change_pct: number | null;
  sparkline: number[];
  currency: string;
  created_at: string;
  updated_at: string;
}

export interface DeckRankingResponse {
  decks: DeckRankingEntry[];
  total: number;
  sort_by: string;
  period: string;
}

export interface DeckValuePoint {
  date: string;
  value: number;
}

export interface DeckValueDetail {
  deck_id: number;
  total_value: number | null;
  priced_cards: number;
  unpriced_cards: number;
  value_change: number | null;
  value_change_pct: number | null;
  value_series: DeckValuePoint[];
  currency: string;
  period: string;
}

// Market summary types (F40)

export interface MarketSummaryResponse {
  total_cards_tracked: number;
  total_observations: number;
  avg_price: number | null;
  avg_price_change_pct: number | null;
  gainers_count: number;
  losers_count: number;
  unchanged_count: number;
  market_direction: string;
  period: string;
  currency: string;
  computed_at: string;
}

// Volatile types (F40)

export interface VolatileCardEntry {
  card_id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  image_url: string | null;
  price_start: number;
  price_end: number;
  change_pct: number;
  change_abs: number;
  consistency: number;
  composite_score: number;
  observation_count: number;
  currency: string;
}

// Liga status types (F60)

export interface LigaStatusResponse {
  total_cards: number;
  liga_priced: number;
  liga_stale: number;
  liga_missing: number;
  unlinked: number;
  coverage_pct: number;
  last_liga_scan: string | null;
}

// Bulk canonize types (F49)

export interface BulkCanonizeResult {
  total: number;
  canonized: number;
  failed: number;
  skipped: number;
  rate_limited: number;
}

// Ticker types (F39)

export interface TickerItemData {
  card_id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  price_end: number;
  change_pct: number;
  direction: "up" | "down";
  currency: string;
}

export interface WebSearchResult {
  card_name: string;
  set_name: string | null;
  liga_url: string | null;
  normal_price: number | null;
  foil_price: number | null;
  image_url: string | null;
  local_card_id: number | null;
}
