import type {
  ApiResponse,
  CardDetail,
  CardSummary,
  CollectionHealth,
  CollectionSummary,
  MarketStats,
  MoverEntry,
  MoversResponse,
  PriceChangeSummary,
  PriceHistoryResponse,
  PriceObservation,
  SetSummary,
} from "../../src/types/api";

function envelope<T>(
  data: T,
  meta?: Partial<ApiResponse<T>["meta"]>,
): ApiResponse<T> {
  return {
    data,
    meta: {
      cursor: meta?.cursor ?? null,
      total: meta?.total ?? null,
      offset: meta?.offset ?? null,
      request_id: meta?.request_id ?? "req-test-001",
    },
    errors: [],
  };
}

export function mockMarketStats(): ApiResponse<MarketStats> {
  return envelope<MarketStats>({
    total_cards: 150,
    total_observations: 4500,
    avg_price: 12.5,
    date_range_start: "2026-01-01",
    date_range_end: "2026-08-18",
  });
}

function makeMoverEntry(i: number, positive: boolean): MoverEntry {
  const pct = positive ? 10 + i * 5 : -(10 + i * 5);
  return {
    card_id: 100 + i,
    name_en: `Card ${positive ? "Gainer" : "Loser"} ${i + 1}`,
    name_pt: `Carta ${positive ? "Ganhadora" : "Perdedora"} ${i + 1}`,
    set_code: "DMR",
    price_start: 10,
    price_end: positive ? 10 + i + 1 : Math.max(1, 10 - i - 1),
    change_pct: pct,
  };
}

export function mockMoversResponse(): ApiResponse<MoversResponse> {
  return envelope<MoversResponse>({
    gainers: Array.from({ length: 5 }, (_, i) => makeMoverEntry(i, true)),
    losers: Array.from({ length: 5 }, (_, i) => makeMoverEntry(i, false)),
  });
}

export function mockCardSummaries(n = 3): ApiResponse<CardSummary[]> {
  const cards: CardSummary[] = Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    game: "magic",
    name_en: `Test Card ${i + 1}`,
    name_pt: `Carta Teste ${i + 1}`,
    set_code: "DMR",
    collector_number: String(i + 1).padStart(3, "0"),
    latest_price: 5.0 + i,
  }));

  return envelope<CardSummary[]>(cards, {
    cursor: n >= 24 ? "bmV4dA==" : null,
    total: n,
  });
}

export function mockCardDetail(
  overrides?: Partial<CardDetail>,
): ApiResponse<CardDetail> {
  return envelope<CardDetail>({
    id: 1,
    game: "magic",
    name_en: "Lightning Bolt",
    name_pt: "Raio",
    set_code: "DMR",
    collector_number: "123",
    latest_price: 8.5,
    source_cards: [
      {
        source: "myp",
        external_id: "12345",
        sku: "magic_dmr_123",
        url: "https://mypcards.com/magic/12345/lightning-bolt",
      },
    ],
    collection_entry_id: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-08-18T12:00:00Z",
    ...overrides,
  });
}

export function makePriceObservations(n = 30): PriceObservation[] {
  return Array.from(
    { length: n },
    (_, i) => {
      const date = new Date(2026, 0, 1 + i);
      return {
        observed_at: date.toISOString().slice(0, 10),
        median_price: 8.0 + Math.sin(i / 5) * 2,
        tcg_price: 7.5 + Math.sin(i / 5) * 1.5,
        last_sold_price: 8.5,
        quantity_available: 10 + i,
        currency: "BRL",
      };
    },
  );
}

export function mockPriceHistory(
  n = 30,
  summaryOverrides?: Partial<PriceChangeSummary>,
): ApiResponse<PriceHistoryResponse> {
  const observations = makePriceObservations(n);
  const first = observations[0];
  const last = observations[observations.length - 1];

  const summary: PriceChangeSummary | null = n > 0
    ? {
        period: "30d",
        price_start: first?.median_price ?? null,
        price_end: last?.median_price ?? null,
        absolute_change:
          first?.median_price != null && last?.median_price != null
            ? last.median_price - first.median_price
            : null,
        percent_change:
          first?.median_price != null && last?.median_price != null && first.median_price !== 0
            ? ((last.median_price - first.median_price) / first.median_price) * 100
            : null,
        data_points: n,
        resolution: "daily",
        ...summaryOverrides,
      }
    : null;

  return envelope<PriceHistoryResponse>({
    observations,
    summary,
  });
}

/**
 * @deprecated Use mockPriceHistory which returns the new PriceHistoryResponse shape.
 */
export function mockPriceHistoryLegacy(n = 30): ApiResponse<PriceObservation[]> {
  return envelope<PriceObservation[]>(makePriceObservations(n));
}

export function mockSetSummaries(): ApiResponse<SetSummary[]> {
  return envelope<SetSummary[]>([
    { set_code: "DMR", game: "magic", card_count: 261 },
    { set_code: "MH2", game: "magic", card_count: 303 },
    { set_code: "2X2", game: "magic", card_count: 332 },
  ]);
}

export function mockCollectionHealth(): ApiResponse<CollectionHealth> {
  return envelope<CollectionHealth>({
    last_collection_at: "2026-08-19T10:30:00Z",
    next_expected_at: "2026-08-20T10:30:00Z",
    total_cards: 150,
    stale_cards_count: 5,
    recent_errors_count: 0,
    status: "healthy",
  });
}

export function mockCollectionSummary(
  overrides?: Partial<CollectionSummary>,
): ApiResponse<CollectionSummary> {
  return envelope<CollectionSummary>({
    total_unique: 120,
    total_cards: 340,
    total_value: 2850.0,
    linked_count: 96,
    priced_count: 80,
    sets_count: 5,
    ...overrides,
  });
}

export function mockEmptyMarketStats(): ApiResponse<MarketStats> {
  return envelope<MarketStats>({
    total_cards: 0,
    total_observations: 0,
    avg_price: null,
    date_range_start: null,
    date_range_end: null,
  });
}

export function mockEmptyMoversResponse(): ApiResponse<MoversResponse> {
  return envelope<MoversResponse>({
    gainers: [],
    losers: [],
  });
}

export function mockApiError(
  code: string,
  message: string,
): ApiResponse<null> {
  return {
    data: null,
    meta: { cursor: null, total: null, offset: null, request_id: "req-err-001" },
    errors: [{ code, message }],
  };
}

export function mockNetworkError(): TypeError {
  return new TypeError("Failed to fetch");
}
