// Ban list / legality types

export interface BanListEntry {
  card_id: number;
  name_en: string | null;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  format: string;
  status: string;
  effective_date: string | null;
  image_url: string | null;
  printings: number;
  owned: boolean;
  owned_quantity: number;
}

export interface BanlistStatus {
  last_synced_at: string | null;
  legalities_count: number;
  banned_count: number;
  restricted_count: number;
  history_count: number;
  formats: number;
}

export interface CardLegality {
  format: string;
  status: string;
  effective_date: string | null;
}

export interface LegalityHistoryEntry {
  card_id: number;
  name_en: string | null;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  format: string;
  old_status: string | null;
  new_status: string;
  changed_at: string;
  image_url: string | null;
}

export interface LegalityHistoryResponse {
  items: LegalityHistoryEntry[];
  total: number;
  limit: number;
  offset: number;
}

export interface CardBanHistoryEntry {
  id: number;
  format: string;
  old_status: string | null;
  new_status: string;
  changed_at: string;
  source: string;
}

export interface BanImpactSchema {
  format: string;
  old_status: string | null;
  new_status: string;
  changed_at: string;
  window_days: number;
  price_before: number | null;
  price_after: number | null;
  absolute_change: number | null;
  percent_change: number | null;
  data_available: boolean;
}
