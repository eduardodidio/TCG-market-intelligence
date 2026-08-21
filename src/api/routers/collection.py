from __future__ import annotations

import asyncio
import base64
import os
from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import HTTPException

from src.api.deps import get_currency_converter_dep, get_db, require_auth_or_api_key
from src.api.jobs import job_tracker
from src.api.schemas.cards import PriceObservation, SourceCardSchema
from src.api.schemas.collect import JobStatus
from src.api.schemas.collection import (
    CollectionCard,
    CollectionCardDetail,
    CollectionSummary,
    ImportResult,
    SnapshotRequest,
    SyncRequest,
)
from src.api.schemas.envelope import ApiResponse, paginated_response, success_response
from src.database.repository import Repository
from src.services.currency import CurrencyConverter
from src.utils.set_code_map import map_to_scryfall_set_code

router = APIRouter(prefix="/collection", tags=["collection"])


def _encode_cursor(row_id: int) -> str:
    return base64.urlsafe_b64encode(str(row_id).encode()).decode()


def _decode_cursor(cursor: str) -> int | None:
    try:
        return int(base64.urlsafe_b64decode(cursor).decode())
    except (ValueError, Exception):
        return None


def _scryfall_image_url(set_code: str, collector_number: str) -> str:
    mapped = map_to_scryfall_set_code(set_code)
    return (
        f"https://api.scryfall.com/cards/{mapped}/{collector_number}"
        f"?format=image&version=normal"
    )


@router.get("", response_model=ApiResponse[list[CollectionCard]])
def list_collection(
    name: str | None = None,
    set: str | None = Query(None, alias="set"),
    cursor: str | None = None,
    sort_by: str = Query(default="name", pattern="^(name|set|number|added)$"),
    sort_dir: str = Query(default="asc", pattern="^(asc|desc)$"),
    offset: int | None = Query(default=None, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    after_id = _decode_cursor(cursor) if cursor else None
    rows = repo.list_collection(
        user_id=user_id,
        name_search=name,
        set_code=set,
        sort_by=sort_by,
        sort_dir=sort_dir,
        offset=offset if offset is not None else 0,
        after_id=after_id,
        limit=limit,
    )

    has_next = len(rows) > limit
    if has_next:
        rows = rows[:limit]

    # Batch-fetch latest prices for linked cards
    linked_card_ids = [r.card_id for r in rows if r.card_id is not None]
    latest_prices = repo.get_latest_prices_batch(linked_card_ids) if linked_card_ids else {}

    data = []
    for r in rows:
        obs = latest_prices.get(r.card_id) if r.card_id else None
        raw_price = obs.median_price if obs else None
        price = converter.convert(raw_price, date.today(), currency) if raw_price else None
        data.append(
            CollectionCard(
                id=r.id,
                card_id=r.card_id,
                set_code=r.set_code,
                collector_number=r.collector_number,
                name_en=r.name_en,
                name_pt=r.name_pt,
                set_name_en=r.set_name_en,
                quantity=r.quantity,
                quality=r.quality,
                language=r.language,
                rarity=r.rarity,
                color=r.color,
                extras=r.extras,
                latest_price=price,
                currency=currency,
                image_url=_scryfall_image_url(r.set_code, r.collector_number),
            )
        )

    next_cursor = _encode_cursor(rows[-1].id) if has_next and rows else None
    total = repo.count_collection(user_id, name_search=name, set_code=set)

    # Compute next_offset for offset-based pagination
    next_offset = None
    if offset is not None and has_next:
        next_offset = offset + limit

    return paginated_response(
        data=data,
        cursor=next_cursor,
        total=total,
        offset=next_offset,
    )


@router.get("/summary", response_model=ApiResponse[CollectionSummary])
def collection_summary(
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    summary = repo.get_collection_summary(user_id)
    total_value = repo.get_collection_total_value(user_id)
    converted_value = (
        converter.convert(total_value, date.today(), currency) if total_value else None
    )
    data = CollectionSummary(
        total_unique=summary["total_unique"],
        total_cards=summary["total_cards"],
        total_value=converted_value,
        linked_count=summary["linked_count"],
        sets_count=summary["sets_count"],
        currency=currency,
    )
    return success_response(data=data)


@router.get("/sets")
def collection_sets(
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    sets = repo.get_collection_sets(user_id)
    data = [{"set_code": s[0], "set_name": s[1], "count": s[2]} for s in sets]
    return success_response(data=data)


@router.get("/{entry_id}", response_model=ApiResponse[CollectionCardDetail])
def get_collection_entry(
    entry_id: int,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
):
    """Get a single collection entry with full detail."""
    entry = repo.get_collection_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    image_url = _scryfall_image_url(entry.set_code, entry.collector_number)
    latest_price = None
    price_history: list[PriceObservation] = []
    source_cards_data: list[SourceCardSchema] = []

    # If linked to a canonical card, fetch price and source data
    if entry.card_id is not None:
        prices = repo.get_latest_prices_batch([entry.card_id])
        obs = prices.get(entry.card_id)
        if obs and obs.median_price:
            latest_price = converter.convert(obs.median_price, date.today(), currency)

        source_cards = repo.get_source_cards_for_card(entry.card_id)
        source_cards_data = [SourceCardSchema.model_validate(sc) for sc in source_cards]

        # Fetch price history from all sources
        for sc in source_cards:
            series = repo.get_price_series(
                source=[sc.source, "jsonld_snapshot"],
                external_id=sc.external_id,
            )
            price_history.extend(
                PriceObservation(
                    observed_at=p.observed_at,
                    median_price=converter.convert(p.median_price, p.observed_at, currency),
                    tcg_price=converter.convert(p.tcg_price, p.observed_at, currency),
                    last_sold_price=converter.convert(p.last_sold_price, p.observed_at, currency),
                    quantity_available=p.quantity_available,
                    currency=currency,
                )
                for p in series
            )
        price_history.sort(key=lambda p: p.observed_at)

    # Build external links
    name = entry.name_en or entry.name_pt or ""
    scryfall_url = None
    ligamagic_url = None
    if name:
        scryfall_q = name
        if entry.set_code:
            scryfall_q += f"+set:{entry.set_code}"
        scryfall_url = f"https://scryfall.com/search?q={scryfall_q}"
        ligamagic_url = f"https://www.ligamagic.com.br/?view=cards/card&card={name}"

    data = CollectionCardDetail(
        id=entry.id,
        card_id=entry.card_id,
        set_code=entry.set_code,
        collector_number=entry.collector_number,
        name_en=entry.name_en,
        name_pt=entry.name_pt,
        set_name_en=entry.set_name_en,
        quantity=entry.quantity,
        quality=entry.quality,
        language=entry.language,
        rarity=entry.rarity,
        color=entry.color,
        extras=entry.extras,
        latest_price=latest_price,
        currency=currency,
        image_url=image_url,
        price_history=price_history,
        source_cards=source_cards_data,
        scryfall_url=scryfall_url,
        ligamagic_url=ligamagic_url,
    )

    return success_response(data=data)


@router.post("/import", response_model=ApiResponse[ImportResult])
def import_collection(
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Import collection from the default CSV file."""
    from pathlib import Path

    from src.collection.importer import import_collection_csv

    csv_path = Path("docs/colecaoImport/export_1b19325b553f22c3260d042d65c1d7dcb07f2743.csv")
    if not csv_path.exists():
        raise HTTPException(status_code=404, detail="Collection CSV not found")

    result = import_collection_csv(
        engine=repo.engine,
        csv_path=csv_path,
        user_id=user_id,
    )
    return success_response(data=ImportResult(**result))


@router.post("/sync", response_model=ApiResponse[JobStatus])
async def trigger_sync(
    request: SyncRequest,
    repo: Repository = Depends(get_db),
    _user_id: str = Depends(require_auth_or_api_key),
) -> ApiResponse[JobStatus]:
    """Trigger a collection sync as a background job."""
    job_id = job_tracker.start(
        "collection_sync",
        {
            "limit": request.limit,
            "history_days": request.history_days,
            "force": request.force,
        },
    )

    asyncio.create_task(
        _run_sync_job(
            job_id,
            limit=request.limit,
            history_days=request.history_days,
            force=request.force,
        )
    )

    data = JobStatus(
        job_id=job_id,
        status="started",
        message="Collection sync started",
    )
    return success_response(data=data)


async def _run_sync_job(
    job_id: str,
    limit: int | None,
    history_days: int,
    force: bool,
) -> None:
    try:
        from src.collectors.sync_collection import run_sync_collection

        db_url = os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")
        summary = await run_sync_collection(
            db_url=db_url,
            limit=limit,
            history_days=history_days,
            skip_matched=not force,
        )
        job_tracker.complete(
            job_id,
            f"Synced {summary.matched} cards, " f"{summary.observations_saved} observations saved",
        )
    except Exception as e:
        job_tracker.fail(job_id, str(e))


@router.post("/snapshot-prices", response_model=ApiResponse[JobStatus])
async def trigger_snapshot_prices(
    request: SnapshotRequest,
    repo: Repository = Depends(get_db),
    _user_id: str = Depends(require_auth_or_api_key),
) -> ApiResponse[JobStatus]:
    """Trigger a daily price snapshot as a background job."""
    job_id = job_tracker.start(
        "snapshot_prices",
        {"limit": request.limit, "dry_run": request.dry_run},
    )

    asyncio.create_task(_run_snapshot_job(job_id, limit=request.limit, dry_run=request.dry_run))

    data = JobStatus(
        job_id=job_id,
        status="started",
        message="Price snapshot started",
    )
    return success_response(data=data)


async def _run_snapshot_job(
    job_id: str,
    limit: int | None,
    dry_run: bool = False,
) -> None:
    try:
        from src.collectors.snapshot_prices import run_snapshot_prices

        db_url = os.environ.get("TCG_DATABASE_URL", "sqlite:///tcg_market.db")
        summary = await run_snapshot_prices(
            db_url=db_url,
            limit=limit,
            dry_run=dry_run,
        )
        job_tracker.complete(
            job_id,
            f"Snapshot complete: {summary.stored} stored, "
            f"{summary.skipped_existing} skipped (existing), "
            f"{summary.skipped_zero_price} skipped (zero price)",
        )
    except Exception as e:
        job_tracker.fail(job_id, str(e))
