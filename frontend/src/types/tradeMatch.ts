export interface DuplicateCard {
  card_id: number;
  name_en: string | null;
  name_pt: string | null;
  set_code: string | null;
  collector_number: string | null;
  quantity: number;
  surplus: number;
  quality: string | null;
  image_uri: string | null;
  current_price: number | null;
}

export interface MatchedCard {
  card_id: number;
  name_en: string;
  set_code: string | null;
  image_uri: string | null;
  partner_quantity: number;
  your_max_price: number | null;
}

export interface TradeMatch {
  partner_name: string;
  share_code: string;
  matching_card_count: number;
  matched_cards: MatchedCard[];
}
