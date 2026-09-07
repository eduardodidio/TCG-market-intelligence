export interface WishlistItem {
  id: number;
  card_id: number;
  name_en: string;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  notes: string | null;
  max_price: number | null;
  is_acquired: boolean;
  acquired_at: string | null;
  created_at: string;
  image_uri: string | null;
  current_price: number | null;
}

export interface WishlistCheckResponse {
  wishlisted: number[];
}
