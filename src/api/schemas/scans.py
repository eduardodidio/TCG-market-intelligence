from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ScanRequest(BaseModel):
    scan_type: str = "collection"
    provider: str = "liga"  # "liga" | "myp", default liga
    set_codes: list[str] | None = None
    format_name: str | None = None
    rarities: list[str] | None = None
    card_ids: list[int] | None = None
    limit: int | None = None
    dry_run: bool = False
    max_age_days: int | None = None


class ScanRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_type: str
    filters_json: str
    status: str
    cards_total: int
    cards_processed: int
    cards_failed: int
    observations_saved: int
    provider: str | None = None
    error_summary: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    created_at: str
    # Computed summary fields (derived from error_summary JSON)
    not_found_count: int = 0
    rate_limited_count: int = 0
    priced_count: int = 0


class ScanListResponse(BaseModel):
    scans: list[ScanRunResponse]
    total: int


class ScanPreviewResponse(BaseModel):
    card_count: int
    skipped_count: int
    credit_cost: int


class ScanTriggerResponse(BaseModel):
    scan_id: int
    status: str
