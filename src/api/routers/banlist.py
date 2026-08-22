"""Banlist router — format legality queries, ban history, and sync trigger."""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import date

from fastapi import APIRouter, Depends, HTTPException

from src.api.deps import get_db, require_auth_or_api_key
from src.api.schemas.banlist import (
    BanImpactSchema,
    BanListEntry,
    CardBanHistoryEntry,
    CardLegalitySchema,
    LegalityHistoryEntry,
    LegalityHistoryResponse,
    SyncTriggerRequest,
)
from src.api.schemas.collect import JobStatus
from src.api.schemas.envelope import ApiResponse, success_response
from src.database.repository import Repository
from src.utils.set_code_map import map_to_scryfall_set_code

router = APIRouter(prefix="/banlist", tags=["banlist"])


def _scryfall_image_url(set_code: str | None, collector_number: str | None) -> str | None:
    if not set_code or not collector_number:
        return None
    mapped = map_to_scryfall_set_code(set_code)
    return (
        f"https://api.scryfall.com/cards/{mapped}/{collector_number}"
        f"?format=image&version=normal"
    )


@router.get("", response_model=ApiResponse[list[BanListEntry]])
def list_banlist(
    format: str,
    status: str | None = None,
    search: str | None = None,
    limit: int = 200,
    offset: int = 0,
    db: Repository = Depends(get_db),
):
    """List banned/restricted cards for a format."""
    # Default to showing banned+restricted if no status filter
    if status is None:
        # Get both banned and restricted
        banned = db.get_legalities_by_format(
            format=format, status="banned", search=search, limit=limit, offset=offset
        )
        restricted = db.get_legalities_by_format(
            format=format, status="restricted", search=search, limit=limit, offset=offset
        )
        rows = banned + restricted
        # Sort by name
        rows.sort(key=lambda r: (r.get("name_en") or "").lower())
        rows = rows[:limit]
    else:
        rows = db.get_legalities_by_format(
            format=format, status=status, search=search, limit=limit, offset=offset
        )

    entries = [
        BanListEntry(
            card_id=r["card_id"],
            name_en=r.get("name_en"),
            name_pt=r.get("name_pt"),
            set_code=r.get("set_code"),
            collector_number=r.get("collector_number"),
            format=r["format"],
            status=r["status"],
            effective_date=r.get("effective_date"),
            image_url=_scryfall_image_url(r.get("set_code"), r.get("collector_number")),
        )
        for r in rows
    ]

    return success_response(entries, total=len(entries), offset=offset)


@router.get("/formats", response_model=ApiResponse[list[str]])
def list_formats(db: Repository = Depends(get_db)):
    """List known MTG formats."""
    formats = db.get_known_formats()
    return success_response(formats)


@router.get("/card/{card_id}", response_model=ApiResponse[list[CardLegalitySchema]])
def get_card_legalities(card_id: int, db: Repository = Depends(get_db)):
    """Get all format legalities for a specific card."""
    legalities = db.get_legalities_for_card(card_id)
    schemas = [
        CardLegalitySchema(
            format=leg["format"],
            status=leg["status"],
            effective_date=leg.get("effective_date"),
        )
        for leg in legalities
    ]
    return success_response(schemas)


@router.get(
    "/card/{card_id}/history",
    response_model=ApiResponse[list[CardBanHistoryEntry]],
)
def get_card_ban_history(card_id: int, db: Repository = Depends(get_db)):
    """Get full ban history timeline for a specific card."""
    card = db.get_card_by_id(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    history = db.get_card_ban_history(card_id)
    entries = [
        CardBanHistoryEntry(
            id=h["id"],
            format=h["format"],
            old_status=h.get("old_status"),
            new_status=h["new_status"],
            changed_at=h["changed_at"],
            source=h["source"],
        )
        for h in history
    ]
    return success_response(entries)


@router.get("/history", response_model=ApiResponse[LegalityHistoryResponse])
def get_legality_history(
    format: str | None = None,
    card_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Repository = Depends(get_db),
):
    """Get paginated legality change history with optional filters."""
    items, total = db.get_legality_history_paginated(
        card_id=card_id,
        format=format,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    entries = [
        LegalityHistoryEntry(
            card_id=h["card_id"],
            name_en=h.get("name_en"),
            name_pt=h.get("name_pt"),
            set_code=h.get("set_code"),
            collector_number=h.get("collector_number"),
            format=h["format"],
            old_status=h.get("old_status"),
            new_status=h["new_status"],
            changed_at=h["changed_at"],
            image_url=_scryfall_image_url(h.get("set_code"), h.get("collector_number")),
        )
        for h in items
    ]
    response = LegalityHistoryResponse(
        items=entries,
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_response(response)


@router.get(
    "/impact/{card_id}",
    response_model=ApiResponse[list[BanImpactSchema]],
)
def get_ban_impact(
    card_id: int,
    window_days: int = 7,
    db: Repository = Depends(get_db),
):
    """Get price impact analysis for ban events (stub — returns data_available=False)."""
    card = db.get_card_by_id(card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    events = db.get_ban_events_for_impact(card_id)
    impacts = [
        BanImpactSchema(
            format=ev["format"],
            old_status=ev.get("old_status"),
            new_status=ev["new_status"],
            changed_at=ev["changed_at"],
            window_days=window_days,
            price_before=None,
            price_after=None,
            absolute_change=None,
            percent_change=None,
            data_available=False,
        )
        for ev in events
    ]
    return success_response(impacts)


@router.post("/sync", response_model=ApiResponse[JobStatus])
async def trigger_sync(
    request: SyncTriggerRequest,
    _user_id: str = Depends(require_auth_or_api_key),
):
    """Trigger a Scryfall legality sync (auth required)."""
    from src.api.jobs import job_tracker

    job_id = job_tracker.start("banlist_sync")

    def _run() -> None:
        from src.collectors.banlist_sync import run_banlist_sync

        db_url = os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")
        try:
            summary = asyncio.run(
                run_banlist_sync(
                    db_url=db_url,
                    bulk=request.bulk,
                    limit=request.limit,
                )
            )
            job_tracker.complete(
                job_id,
                summary=(
                    f"cards={summary.cards_processed} "
                    f"upserted={summary.legalities_upserted} "
                    f"changes={summary.changes_detected}"
                ),
            )
        except Exception as exc:
            job_tracker.fail(job_id, str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return success_response(
        JobStatus(job_id=job_id, status="running", message="Banlist sync started")
    )
