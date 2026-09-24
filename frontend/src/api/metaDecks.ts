import type { ApiResponse } from "../types/api";
import type {
  MetaDeckDetail,
  MetaDeckListResponse,
  MetaFormat,
  MetaFormatsResponse,
} from "../types/metaDecks";
import { apiGet } from "./client";

type RequestOptions = { signal?: AbortSignal };

export function fetchMetaFormats(
  options?: RequestOptions,
): Promise<ApiResponse<MetaFormatsResponse>> {
  return apiGet<MetaFormatsResponse>("/api/v1/meta-decks/formats", undefined, options);
}

export function fetchMetaDecks(params: {
  format: MetaFormat;
  limit?: number;
  offset?: number;
  snapshot_date?: string;
}, options?: RequestOptions): Promise<ApiResponse<MetaDeckListResponse>> {
  const query: Record<string, string> = { format: params.format };
  if (params.limit !== undefined) query.limit = String(params.limit);
  if (params.offset !== undefined) query.offset = String(params.offset);
  if (params.snapshot_date) query.snapshot_date = params.snapshot_date;

  return apiGet<MetaDeckListResponse>("/api/v1/meta-decks", query, options);
}

export function fetchMetaDeck(
  id: number,
  options?: RequestOptions,
): Promise<ApiResponse<MetaDeckDetail>> {
  return apiGet<MetaDeckDetail>(`/api/v1/meta-decks/${id}`, undefined, options);
}
