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
}

export interface CardLegality {
  format: string;
  status: string;
  effective_date: string | null;
}

export interface LegalityHistoryEntry {
  card_id: number;
  name_en: string | null;
  format: string;
  old_status: string | null;
  new_status: string;
  changed_at: string;
}
