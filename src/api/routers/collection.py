from __future__ import annotations

import asyncio
import base64
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, UploadFile
from fastapi.exceptions import HTTPException

from src.analytics.aggregation import (
    PERIOD_MAP,
    aggregate_series,
    compute_price_change_summary,
)
from src.analytics.indicators import compute_card_analytics
from src.api.deps import (
    get_credit_service,
    get_currency_converter_dep,
    get_current_user,
    get_db,
    require_auth_or_api_key,
)
from src.api.jobs import job_tracker
from src.api.schemas.ban_engine import BannedCollectionCard, CardLegalityWithChange
from src.api.schemas.cards import PriceObservation, SourceCardSchema
from src.api.schemas.collect import JobStatus
from src.api.schemas.collection import (
    BulkCanonizeResult,
    CollectionCard,
    CollectionCardDetail,
    CollectionHistoryResponse,
    CollectionSummary,
    ImportResult,
    LigaStatusResponse,
    ManualPriceRequest,
    SnapshotRequest,
    SyncRequest,
)
from src.api.schemas.envelope import ApiResponse, ErrorDetail, paginated_response, success_response
from src.api.schemas.metrics import (
    CardMetricsResponse,
    MomentumSchema,
    MovingAverageSchema,
    PerformanceScoreSchema,
    PeriodComparisonSchema,
    PriceExtremesSchema,
    VolatilitySchema,
)
from src.config import get_db_url
from src.credits.constants import CARD_REFRESH_COST
from src.credits.service import CreditService
from src.database.repository import Repository
from src.domain.models import CardAnalytics, HistoricalPrice, User
from src.services import ban_analyzer
from src.services.currency import CurrencyConverter
from src.utils.set_code_map import map_to_scryfall_set_code

log = structlog.get_logger()

router = APIRouter(prefix="/collection", tags=["collection"])


def _encode_cursor(row_id: int) -> str:
    return base64.urlsafe_b64encode(str(row_id).encode()).decode()


def _decode_cursor(cursor: str) -> int | None:
    try:
        return int(base64.urlsafe_b64decode(cursor).decode())
    except Exception:
        return None


def _scryfall_image_url(set_code: str, collector_number: str) -> str:
    mapped = map_to_scryfall_set_code(set_code)
    return f"https://api.scryfall.com/cards/{mapped}/{collector_number}?format=image&version=normal"


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
        price_source = obs.source if obs else None
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
                price_source=price_source,
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
    # Ban counts (degrade gracefully if F41 tables missing)
    banned_count = 0
    recently_changed_count = 0
    try:
        ban_summary = ban_analyzer.get_ban_summary(repo, user_id)
        banned_count = ban_summary.banned_count + ban_summary.restricted_count
        recently_changed_count = ban_summary.recently_changed_count
    except Exception:
        log.debug("ban_summary_unavailable", user_id=user_id)

    data = CollectionSummary(
        total_unique=summary["total_unique"],
        total_cards=summary["total_cards"],
        total_value=converted_value,
        linked_count=summary["linked_count"],
        priced_count=summary["priced_count"],
        sets_count=summary["sets_count"],
        currency=currency,
        banned_count=banned_count,
        recently_changed_count=recently_changed_count,
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


@router.get("/banned", response_model=ApiResponse[list[BannedCollectionCard]])
def list_banned_cards(
    format: str | None = Query(None),
    days: int = Query(default=30, ge=1, le=365),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """List banned/restricted cards in the user's collection."""
    data = ban_analyzer.get_banned_collection_cards(repo, user_id, format, days)
    return success_response(data=data)


@router.post("/canonize-all", response_model=ApiResponse[BulkCanonizeResult])
async def canonize_all(
    limit: int | None = Query(default=None, ge=1),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Bulk canonize all unlinked/orphan collection entries."""
    from src.collectors.bulk_canonize import bulk_canonize
    from src.providers.myp.provider import MypCardsProvider

    provider = MypCardsProvider()
    try:
        result = await bulk_canonize(
            engine=repo.engine,
            user_id=user_id,
            provider=provider,
            concurrency=3,
            limit=limit,
        )
    finally:
        await provider.close()

    data = BulkCanonizeResult(
        total=result.total,
        canonized=result.canonized,
        failed=result.failed,
        skipped=result.skipped,
        rate_limited=result.rate_limited,
    )
    return success_response(data=data)


@router.get("/liga-status", response_model=ApiResponse[LigaStatusResponse])
def get_liga_status(
    stale_days: int = Query(default=7, ge=1),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get Liga price coverage stats for the user's collection."""
    stats = repo.get_liga_coverage_stats(user_id, stale_days=stale_days)
    data = LigaStatusResponse(**stats)
    return success_response(data=data)


@router.get("/liga-missing", response_model=ApiResponse[list[CollectionCard]])
def list_liga_missing(
    stale_days: int = Query(default=7, ge=1),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """List collection cards missing or with stale Liga prices."""
    cards, total = repo.get_liga_missing_cards(
        user_id, stale_days=stale_days, limit=limit, offset=offset
    )
    data = [
        CollectionCard(
            id=c["id"],
            card_id=c["card_id"],
            set_code=c["set_code"],
            collector_number=c["collector_number"],
            name_en=c["name_en"],
            name_pt=c["name_pt"],
            set_name_en=c["set_name_en"],
            quantity=c["quantity"],
            quality=c["quality"],
            language=c["language"],
            rarity=c["rarity"],
            color=c["color"],
            extras=c["extras"],
            image_url=_scryfall_image_url(c["set_code"], c["collector_number"]),
        )
        for c in cards
    ]
    return paginated_response(
        data=data,
        cursor=None,
        total=total,
        offset=offset + limit if offset + limit < total else None,
    )


METRICS_PERIOD_MAP = {"24h": 1, "7d": 7, "30d": 30, "90d": 90, "180d": 180, "1y": 365}


@router.get(
    "/{entry_id}/metrics",
    response_model=ApiResponse[CardMetricsResponse],
)
def get_card_metrics(
    entry_id: int,
    period: str = Query(default="30d", pattern="^(24h|7d|30d|90d|180d|1y)$"),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get analytics metrics for a collection entry's card."""
    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    if entry.card_id is None:
        raise HTTPException(status_code=422, detail="Card not linked to a price source")

    source_cards = repo.get_source_cards_for_card(entry.card_id)
    if not source_cards:
        # No source cards: return empty metrics
        return success_response(
            data=CardMetricsResponse(
                entry_id=entry_id,
                card_id=entry.card_id,
                period=period,
                currency=currency,
                data_points=0,
            )
        )

    days = METRICS_PERIOD_MAP[period]

    # Fetch all price observations and convert to domain objects
    all_prices: list[HistoricalPrice] = []
    for sc in source_cards:
        db_prices = repo.get_price_series(
            source=[sc.source, "jsonld_snapshot"],
            external_id=sc.external_id,
            days=days * 2 + 30,  # Extra data for period comparison + MAs
        )
        for p in db_prices:
            all_prices.append(
                HistoricalPrice(
                    source=p.source,
                    external_id=p.external_id,
                    observed_at=p.observed_at,
                    median_price=p.median_price,
                    tcg_price=p.tcg_price,
                    last_sold_price=p.last_sold_price,
                    quantity_available=p.quantity_available,
                )
            )

    all_prices.sort(key=lambda p: p.observed_at)

    # Use the first source card for analytics context
    sc = source_cards[0]
    analytics = compute_card_analytics(
        all_prices,
        source=sc.source,
        external_id=sc.external_id,
        period_days=days,
    )

    # Convert analytics to response with currency conversion
    response = _build_metrics_response(
        entry_id=entry_id,
        card_id=entry.card_id,
        period=period,
        currency=currency,
        analytics=analytics,
        converter=converter,
        data_points=len(all_prices),
    )

    return success_response(data=response)


def _convert_price(
    value: Decimal | None,
    converter: CurrencyConverter,
    currency: str,
) -> float | None:
    """Convert a Decimal price through the currency converter."""
    if value is None:
        return None
    converted = converter.convert(value, date.today(), currency)
    return float(converted) if converted is not None else None


def _build_metrics_response(
    entry_id: int,
    card_id: int,
    period: str,
    currency: str,
    analytics: CardAnalytics,
    converter: CurrencyConverter,
    data_points: int,
) -> CardMetricsResponse:
    """Convert a CardAnalytics domain object to a Pydantic response with currency."""
    # Moving averages
    ma_schemas = []
    for ma in analytics.moving_averages:
        converted = _convert_price(ma.value, converter, currency)
        if converted is not None:
            ma_schemas.append(MovingAverageSchema(period=ma.period, value=converted))

    # Extremes
    extremes_schema = None
    if analytics.extremes:
        e = analytics.extremes
        ath = _convert_price(e.ath_price, converter, currency)
        atl = _convert_price(e.atl_price, converter, currency)
        if ath is not None and atl is not None:
            extremes_schema = PriceExtremesSchema(
                ath_price=ath,
                ath_date=e.ath_date,
                atl_price=atl,
                atl_date=e.atl_date,
            )

    # Volatility
    volatility_schema = None
    if analytics.volatility:
        v = analytics.volatility
        sd = _convert_price(v.std_dev, converter, currency)
        if sd is not None:
            volatility_schema = VolatilitySchema(
                period_days=v.period_days,
                std_dev=sd,
                coefficient_of_variation=float(v.coefficient_of_variation),
            )

    # Momentum
    momentum_schema = None
    if analytics.momentum:
        m = analytics.momentum
        momentum_schema = MomentumSchema(
            period_days=m.period_days,
            rate_of_change=float(m.rate_of_change),
            trend_direction=m.trend_direction,
        )

    # Performance
    performance_schema = None
    if analytics.performance:
        p = analytics.performance
        performance_schema = PerformanceScoreSchema(
            score=p.score,
            label=p.label,
            period_days=p.period_days,
        )

    # Period comparison
    comparison_schema = None
    if analytics.period_comparison:
        pc = analytics.period_comparison
        cur = _convert_price(pc.current_avg, converter, currency)
        prev = _convert_price(pc.previous_avg, converter, currency)
        d = _convert_price(pc.delta, converter, currency)
        if cur is not None and prev is not None and d is not None:
            comparison_schema = PeriodComparisonSchema(
                current_avg=cur,
                previous_avg=prev,
                delta=d,
                delta_pct=float(pc.delta_pct),
                period_days=pc.period_days,
            )

    return CardMetricsResponse(
        entry_id=entry_id,
        card_id=card_id,
        period=period,
        currency=currency,
        moving_averages=ma_schemas,
        extremes=extremes_schema,
        volatility=volatility_schema,
        momentum=momentum_schema,
        performance=performance_schema,
        period_comparison=comparison_schema,
        data_points=data_points,
    )


@router.get(
    "/{entry_id}/history",
    response_model=ApiResponse[CollectionHistoryResponse],
)
def get_collection_history(
    entry_id: int,
    period: str = Query(default="30d"),
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get price history for a collection entry."""
    if period not in PERIOD_MAP:
        raise HTTPException(
            status_code=422,
            detail="Invalid period. Must be one of: " + ", ".join(PERIOD_MAP.keys()),
        )

    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    if entry.card_id is None:
        return success_response(data=CollectionHistoryResponse(observations=[], summary=None))

    source_cards = repo.get_source_cards_for_card(entry.card_id)
    if not source_cards:
        return success_response(data=CollectionHistoryResponse(observations=[], summary=None))

    days = PERIOD_MAP[period]
    all_observations = []
    for sc in source_cards:
        prices = repo.get_price_series(
            source=[sc.source, "jsonld_snapshot"],
            external_id=sc.external_id,
            days=days,
        )
        all_observations.extend(prices)

    all_observations.sort(key=lambda p: p.observed_at)

    observations = [
        PriceObservation(
            observed_at=p.observed_at,
            median_price=converter.convert(p.median_price, p.observed_at, currency),
            tcg_price=converter.convert(p.tcg_price, p.observed_at, currency),
            last_sold_price=converter.convert(p.last_sold_price, p.observed_at, currency),
            quantity_available=p.quantity_available,
            currency=currency,
        )
        for p in all_observations
    ]

    observations, resolution = aggregate_series(observations, period)
    summary = compute_price_change_summary(observations, period, resolution)

    return success_response(
        data=CollectionHistoryResponse(observations=observations, summary=summary)
    )


@router.get(
    "/{entry_id}/legality",
    response_model=ApiResponse[list[CardLegalityWithChange]],
)
def get_entry_legality(
    entry_id: int,
    days: int = Query(default=30, ge=1, le=365),
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get format legality for a collection entry, with recent change info."""
    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    if entry.card_id is None:
        return success_response(data=[])

    data = ban_analyzer.get_card_legalities_with_changes(repo, entry.card_id, days)
    return success_response(data=data)


@router.patch("/{entry_id}/price", response_model=ApiResponse[CollectionCardDetail])
def set_manual_price(
    entry_id: int,
    request: ManualPriceRequest,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Set a manual price for a collection entry."""
    entry = repo.get_collection_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Collection entry not found")
    if entry.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this entry")

    # Convert price to BRL for storage
    price_brl = Decimal(str(request.price))
    if request.currency == "USD":
        rate = converter.get_display_rate(date.today())
        if rate is None:
            raise HTTPException(
                status_code=422, detail="Exchange rate unavailable for USD conversion"
            )
        price_brl = (price_brl * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    # PILA is 1:1 with BRL, no conversion needed

    # Auto-create minimal CardRow if entry has no card_id
    if entry.card_id is None:
        card_id = repo.create_canonical_card(
            game="magic",
            name_en=entry.name_en or "Unknown",
            name_pt=entry.name_pt,
            set_code=entry.set_code,
            collector_number=entry.collector_number,
        )
        repo.link_collection_entry(entry_id, card_id)
        log.info("manual_price_auto_created_card", entry_id=entry_id, card_id=card_id)

    # Reload entry to get card_id (may have been auto-created above)
    entry = repo.get_collection_entry(entry_id)
    if entry is None or entry.card_id is None:
        raise HTTPException(status_code=422, detail="Failed to link collection entry to card")
    repo.upsert_manual_price(entry.card_id, price_brl, date.today())
    log.info(
        "manual_price_set",
        entry_id=entry_id,
        price_brl=str(price_brl),
        original_currency=request.currency,
        original_price=request.price,
    )

    return _build_collection_detail(entry_id, currency, repo, converter, user_id)


@router.get("/{entry_id}", response_model=ApiResponse[CollectionCardDetail])
def get_collection_entry(
    entry_id: int,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Get a single collection entry with full detail."""
    return _build_collection_detail(entry_id, currency, repo, converter, user_id)


@router.post("/{entry_id}/canonize", response_model=ApiResponse[CollectionCardDetail])
async def canonize_card(
    entry_id: int,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Canonize an unlinked collection entry: create CardRow, search MYP,
    link SourceCard, and fetch current price — all in one shot.

    If the entry already has a card_id but no MYP source cards (orphan state),
    re-runs the MYP search+match flow without creating a new CardRow.
    """
    from src.collection.converter import row_to_collection_entry
    from src.collection.matcher import match_collection_card
    from src.domain.models import HistoricalPrice, SourceCard
    from src.providers.myp.provider import MypCardsProvider

    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    # Allow re-canonize when card_id exists but has no MYP source cards
    already_canonical = entry.card_id is not None
    if already_canonical:
        source_cards = repo.get_source_cards_for_card(entry.card_id)
        has_myp_source = any(sc.source == "myp" for sc in source_cards)
        if has_myp_source:
            raise HTTPException(status_code=422, detail="Card is already canonical")
        card_id = entry.card_id
    else:
        # Step 1: Create canonical CardRow from collection data
        card_id = repo.create_canonical_card(
            game="magic",
            name_en=entry.name_en or "Unknown",
            name_pt=entry.name_pt,
            set_code=entry.set_code,
            collector_number=entry.collector_number,
        )

        # Step 2: Link collection entry to canonical card
        repo.link_collection_entry(entry_id, card_id)

    # Step 3: Search MYP and try to create SourceCard + fetch price
    provider = MypCardsProvider()
    myp_warning: str | None = None
    try:
        ce = row_to_collection_entry(entry)
        search_results: list = []
        if ce.name_en:
            search_results = await provider.search_card(ce.name_en)

        # F47-style PT fallback: retry with name_pt when EN yields no results
        if not search_results and ce.name_pt:
            search_results = await provider.search_card(ce.name_pt)
            if search_results:
                log.info(
                    "canonize_pt_fallback_used",
                    entry_id=entry_id,
                    name_en=ce.name_en,
                    name_pt=ce.name_pt,
                    results=len(search_results),
                )

        match = match_collection_card(ce, search_results)

        if match.status == "matched" and match.myp_result:
            myp = match.myp_result
            source_card = SourceCard(
                source="myp",
                external_id=myp.external_id,
                url=myp.url,
                sku=myp.sku,
            )

            # Fetch full details and upsert source card
            detailed = await provider.get_card_details(source_card)
            if detailed:
                # Update canonical card with richer data from MYP
                repo.upsert_card(detailed)
                repo.upsert_source_card(detailed, card_id=card_id)

                # Fetch current price
                slug = source_card.url.rsplit("/", 1)[-1]
                jsonld = await provider.fetch_current_price(
                    myp.external_id,
                    slug,
                )
                if jsonld and jsonld.price and jsonld.price > 0:
                    obs = HistoricalPrice(
                        source="jsonld_snapshot",
                        external_id=myp.external_id,
                        observed_at=date.today(),
                        median_price=jsonld.price,
                    )
                    repo.insert_price_observations([obs])
                    log.info(
                        "canonize_price_fetched",
                        entry_id=entry_id,
                        external_id=myp.external_id,
                        price=str(jsonld.price),
                    )
    except Exception as exc:
        log.warning(
            "canonize_myp_fetch_failed",
            entry_id=entry_id,
            card_id=card_id,
            error=str(exc),
        )
        myp_warning = f"Card linked but MYP fetch failed: {exc}"
    finally:
        await provider.close()

    log.info("card_canonized", entry_id=entry_id, card_id=card_id)
    response = _build_collection_detail(entry_id, currency, repo, converter, user_id)
    if myp_warning:
        response.errors.append(ErrorDetail(code="myp_fetch_warning", message=myp_warning))
    return response


@router.post("/{entry_id}/refresh", response_model=ApiResponse[CollectionCardDetail])
async def refresh_card_price(
    entry_id: int,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
    user: User = Depends(get_current_user),
    credit_svc: CreditService = Depends(get_credit_service),
):
    """Refresh a single card's price from MYP in real-time."""
    from src.domain.models import HistoricalPrice
    from src.providers.myp.provider import MypCardsProvider

    # Credit guard — admin bypass
    if not user.is_admin:
        if not credit_svc.check_sufficient(user.id, CARD_REFRESH_COST):
            balance = credit_svc.get_balance(user.id)
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "INSUFFICIENT_CREDITS",
                    "balance": balance.balance,
                    "cost": CARD_REFRESH_COST,
                    "message": "Not enough treasure tokens.",
                },
            )

    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    if entry.card_id is None:
        raise HTTPException(status_code=422, detail="Card not linked to a price source")

    source_cards = repo.get_source_cards_for_card(entry.card_id)
    myp_sources = [sc for sc in source_cards if sc.source == "myp"]
    if not myp_sources:
        # Auto-canonize: search MYP and create source card before refresh
        from src.collection.converter import row_to_collection_entry
        from src.collection.matcher import match_collection_card
        from src.domain.models import SourceCard

        provider = MypCardsProvider()
        try:
            ce = row_to_collection_entry(entry)
            search_results: list = []
            if ce.name_en:
                search_results = await provider.search_card(ce.name_en)
            if not search_results and ce.name_pt:
                search_results = await provider.search_card(ce.name_pt)

            match = match_collection_card(ce, search_results)

            if match.status != "matched" or not match.myp_result:
                raise HTTPException(
                    status_code=422,
                    detail="No MYP source card linked and auto-match failed",
                )

            myp = match.myp_result
            source_card = SourceCard(
                source="myp",
                external_id=myp.external_id,
                url=myp.url,
                sku=myp.sku,
            )

            detailed = await provider.get_card_details(source_card)
            if detailed:
                repo.upsert_card(detailed)
                repo.upsert_source_card(detailed, card_id=entry.card_id)

            # Re-fetch source cards after canonize
            source_cards = repo.get_source_cards_for_card(entry.card_id)
            myp_sources = [sc for sc in source_cards if sc.source == "myp"]
            if not myp_sources:
                raise HTTPException(
                    status_code=422,
                    detail="No MYP source card linked and auto-canonize failed",
                )

            log.info(
                "refresh_auto_canonized",
                entry_id=entry_id,
                card_id=entry.card_id,
                external_id=myp.external_id,
            )
        except HTTPException:
            raise
        except Exception as exc:
            log.warning(
                "refresh_auto_canonize_failed",
                entry_id=entry_id,
                error=str(exc),
            )
            raise HTTPException(
                status_code=422,
                detail=f"No MYP source card linked and auto-canonize failed: {exc}",
            )
        finally:
            await provider.close()

    sc = myp_sources[0]
    slug = sc.url.rsplit("/", 1)[-1]
    external_id = sc.external_id

    provider = MypCardsProvider()
    try:
        jsonld = await provider.fetch_current_price(external_id, slug)
    finally:
        await provider.close()

    if jsonld and jsonld.price and jsonld.price > 0:
        obs = HistoricalPrice(
            source="jsonld_snapshot",
            external_id=external_id,
            observed_at=date.today(),
            median_price=jsonld.price,
        )
        repo.insert_price_observations([obs])
        log.info(
            "card_price_refreshed",
            entry_id=entry_id,
            external_id=external_id,
            price=str(jsonld.price),
        )

    # Deduct credit unconditionally (non-admin only) — aligned with Liga refresh behavior
    if not user.is_admin:
        credit_svc.deduct(user.id, CARD_REFRESH_COST, "card_refresh", reference_id=str(entry_id))

    # Return updated card detail (reuse same logic as get_collection_entry)
    return _build_collection_detail(entry_id, currency, repo, converter, user_id)


@router.post("/{entry_id}/refresh-liga", response_model=ApiResponse[CollectionCardDetail])
async def refresh_card_price_liga(
    entry_id: int,
    request: Request,
    currency: str = Query(default="BRL", pattern="^(BRL|USD|PILA)$"),
    repo: Repository = Depends(get_db),
    converter: CurrencyConverter = Depends(get_currency_converter_dep),
    user_id: str = Depends(require_auth_or_api_key),
    user: User = Depends(get_current_user),
    credit_svc: CreditService = Depends(get_credit_service),
):
    """Refresh a single card's price from LigaMagic in real-time."""
    import traceback as _tb

    from src.domain.models import HistoricalPrice
    from src.providers.liga.exceptions import (
        LigaError,
        LigaNotFoundError,
        LigaRateLimitError,
    )
    from src.providers.liga.provider import LigaMagicProvider

    # Credit guard — admin bypass
    if not user.is_admin:
        if not credit_svc.check_sufficient(user.id, CARD_REFRESH_COST):
            balance = credit_svc.get_balance(user.id)
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "INSUFFICIENT_CREDITS",
                    "balance": balance.balance,
                    "cost": CARD_REFRESH_COST,
                    "message": "Not enough treasure tokens.",
                },
            )

    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    card_name = entry.name_en or entry.name_pt
    if not card_name:
        raise HTTPException(
            status_code=422,
            detail="Card has no name (name_en or name_pt required for LigaMagic search)",
        )

    # Reuse singleton provider from registry (avoids Playwright resource conflicts)
    registry = getattr(request.app.state, "provider_registry", None)
    provider = None
    if registry is not None:
        provider = next(
            (p for p in registry.providers if isinstance(p, LigaMagicProvider)),
            None,
        )
    if provider is None:
        raise HTTPException(status_code=503, detail="Liga provider not available")

    try:
        prices = await provider.search_card(card_name)
    except LigaNotFoundError:
        response = _build_collection_detail(entry_id, currency, repo, converter, user_id)
        response.errors.append(
            ErrorDetail(code="liga_warning", message="Card not found on LigaMagic")
        )
        return response
    except LigaRateLimitError:
        response = _build_collection_detail(entry_id, currency, repo, converter, user_id)
        response.errors.append(
            ErrorDetail(
                code="liga_warning",
                message="LigaMagic rate limited, try again later",
            )
        )
        return response
    except LigaError as exc:
        log.warning(
            "liga_refresh_error",
            entry_id=entry_id,
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        response = _build_collection_detail(entry_id, currency, repo, converter, user_id)
        response.errors.append(ErrorDetail(code="liga_warning", message=f"LigaMagic error: {exc}"))
        return response
    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}" if str(exc) else f"{type(exc).__name__} (no details)"
        log.warning(
            "liga_refresh_unexpected_error",
            entry_id=entry_id,
            error=str(exc),
            exc_type=type(exc).__name__,
            traceback=_tb.format_exc(),
        )
        response = _build_collection_detail(entry_id, currency, repo, converter, user_id)
        response.errors.append(ErrorDetail(code="liga_warning", message=f"LigaMagic error: {msg}"))
        return response

    # Extract price: prefer normal.mid, fallback normal.low, then normal.high
    normal = prices.get("normal", {})
    price = normal.get("mid") or normal.get("low") or normal.get("high")

    if price is None:
        response = _build_collection_detail(entry_id, currency, repo, converter, user_id)
        response.errors.append(
            ErrorDetail(
                code="liga_warning",
                message="No price found on LigaMagic for this card",
            )
        )
        return response

    # Auto-create canonical card if entry has no card_id
    if entry.card_id is None:
        card_id = repo.create_canonical_card(
            game="magic",
            name_en=entry.name_en or "Unknown",
            name_pt=entry.name_pt,
            set_code=entry.set_code,
            collector_number=entry.collector_number,
        )
        repo.link_collection_entry(entry_id, card_id)
        log.info("liga_refresh_auto_created_card", entry_id=entry_id, card_id=card_id)
        # Reload entry to get card_id
        entry = repo.get_collection_entry(entry_id)

    obs = HistoricalPrice(
        source="liga",
        external_id=f"liga_{entry.card_id}",
        observed_at=date.today(),
        median_price=price,
    )
    repo.insert_price_observations([obs])
    log.info(
        "card_price_refreshed_liga",
        entry_id=entry_id,
        card_name=card_name,
        price=str(price),
    )

    # Deduct credit after successful refresh (non-admin only)
    if not user.is_admin:
        credit_svc.deduct(user.id, CARD_REFRESH_COST, "card_refresh", reference_id=str(entry_id))

    return _build_collection_detail(entry_id, currency, repo, converter, user_id)


def _build_collection_detail(
    entry_id: int,
    currency: str,
    repo: Repository,
    converter: CurrencyConverter,
    user_id: str,
) -> ApiResponse[CollectionCardDetail]:
    """Build a CollectionCardDetail response for an entry. Shared by GET and refresh."""
    entry = repo.get_collection_entry(entry_id)
    if not entry or entry.user_id != user_id:
        raise HTTPException(status_code=404, detail="Collection entry not found")

    image_url = _scryfall_image_url(entry.set_code, entry.collector_number)
    latest_price = None
    price_source = None
    source_cards_data: list[SourceCardSchema] = []

    if entry.card_id is not None:
        prices = repo.get_latest_prices_batch([entry.card_id])
        obs = prices.get(entry.card_id)
        if obs and obs.median_price:
            latest_price = converter.convert(obs.median_price, date.today(), currency)
        if obs:
            price_source = obs.source

        source_cards = repo.get_source_cards_for_card(entry.card_id)
        source_cards_data = [SourceCardSchema.model_validate(sc) for sc in source_cards]

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
        price_source=price_source,
        currency=currency,
        image_url=image_url,
        price_history=[],
        source_cards=source_cards_data,
        scryfall_url=scryfall_url,
        ligamagic_url=ligamagic_url,
    )

    return success_response(data=data)


@router.post("/import", response_model=ApiResponse[ImportResult])
def import_collection(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    repo: Repository = Depends(get_db),
    user_id: str = Depends(require_auth_or_api_key),
):
    """Import collection from an uploaded CSV file."""
    import tempfile
    from pathlib import Path

    from src.collection.importer import import_collection_csv

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are accepted")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
        tmp.write(file.file.read())
        tmp_path = Path(tmp.name)

    try:
        result = import_collection_csv(
            engine=repo.engine,
            csv_path=tmp_path,
            user_id=user_id,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    new_entry_ids = result.get("new_entry_ids", [])
    canonize_scheduled = False
    if new_entry_ids:
        background_tasks.add_task(
            _run_import_canonize,
            engine=repo.engine,
            user_id=user_id,
        )
        canonize_scheduled = True
        log.info(
            "import_canonize_scheduled",
            user_id=user_id,
            new_entries=len(new_entry_ids),
        )

    import_result = ImportResult(
        imported=result["imported"],
        skipped=result["skipped"],
        linked=result["linked"],
        total_csv_rows=result["total_csv_rows"],
        new_entry_ids=new_entry_ids,
        canonize_scheduled=canonize_scheduled,
    )
    return success_response(data=import_result)


async def _run_import_canonize(engine, user_id: str) -> None:
    """Background task: canonize newly imported collection entries."""
    from src.collectors.bulk_canonize import bulk_canonize
    from src.providers.myp.provider import MypCardsProvider

    provider = MypCardsProvider()
    try:
        result = await bulk_canonize(
            engine=engine,
            user_id=user_id,
            provider=provider,
            concurrency=3,
        )
        log.info(
            "import_canonize_complete",
            user_id=user_id,
            total=result.total,
            canonized=result.canonized,
            failed=result.failed,
            rate_limited=result.rate_limited,
        )
    except Exception as exc:
        log.warning(
            "import_canonize_failed",
            user_id=user_id,
            error=str(exc),
        )
    finally:
        await provider.close()


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

        db_url = get_db_url()
        summary = await run_sync_collection(
            db_url=db_url,
            limit=limit,
            history_days=history_days,
            skip_matched=not force,
        )
        job_tracker.complete(
            job_id,
            f"Synced {summary.matched} cards, {summary.observations_saved} observations saved",
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

        db_url = get_db_url()
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
