"""Bulk canonize service: link all unlinked collection entries to MYP sources.

Iterates over entries with no card_id (unlinked) or card_id but no
SourceCardRow (orphans), reusing the single-card canonize logic.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date

import structlog
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.collection.converter import row_to_collection_entry
from src.collection.matcher import match_collection_card
from src.database.models import SourceCardRow, UserCollectionRow
from src.database.repository import Repository
from src.domain.models import HistoricalPrice, SourceCard
from src.providers.myp.exceptions import NotFoundError, RateLimitError, ServerError

log = structlog.get_logger()


@dataclass
class BulkCanonizeResult:
    """Summary of a bulk canonize run."""

    total: int = 0
    canonized: int = 0
    failed: int = 0
    skipped: int = 0
    rate_limited: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)


def _get_unlinked_entries(
    engine: Engine,
    user_id: str,
    limit: int | None = None,
) -> list[UserCollectionRow]:
    """Return collection entries that need canonization.

    Includes:
    - Entries with card_id IS NULL (never linked)
    - Entries with card_id but no matching SourceCardRow (orphans)
    """
    with Session(engine) as session:
        # 1. Entries with no card_id
        stmt_unlinked = (
            select(UserCollectionRow)
            .where(
                UserCollectionRow.user_id == user_id,
                UserCollectionRow.card_id.is_(None),
            )
            .order_by(UserCollectionRow.id.asc())
        )
        unlinked = list(session.execute(stmt_unlinked).scalars().all())

        # 2. Orphan entries: card_id set but no source_cards row
        stmt_with_card = (
            select(UserCollectionRow)
            .where(
                UserCollectionRow.user_id == user_id,
                UserCollectionRow.card_id.is_not(None),
            )
            .order_by(UserCollectionRow.id.asc())
        )
        with_card = list(session.execute(stmt_with_card).scalars().all())

        orphans = []
        for entry in with_card:
            source_cards = list(
                session.execute(select(SourceCardRow).where(SourceCardRow.card_id == entry.card_id))
                .scalars()
                .all()
            )
            has_myp = any(sc.source == "myp" for sc in source_cards)
            if not has_myp:
                orphans.append(entry)

        entries = unlinked + orphans

        if limit is not None:
            entries = entries[:limit]

        return entries


async def _canonize_single(
    repo: Repository,
    entry: UserCollectionRow,
    provider: object,
) -> str:
    """Canonize a single entry. Returns 'canonized'.

    Reuses the same logic as the POST /{entry_id}/canonize endpoint.
    """
    already_has_card = entry.card_id is not None

    if not already_has_card:
        card_id = repo.create_canonical_card(
            game="magic",
            name_en=entry.name_en or "Unknown",
            name_pt=entry.name_pt,
            set_code=entry.set_code,
            collector_number=entry.collector_number,
        )
        repo.link_collection_entry(entry.id, card_id)
    else:
        card_id = entry.card_id

    # Search MYP and try to create SourceCard + fetch price
    ce = row_to_collection_entry(entry)
    search_results: list = []
    if ce.name_en:
        search_results = await provider.search_card(ce.name_en)

    # PT fallback
    if not search_results and ce.name_pt:
        search_results = await provider.search_card(ce.name_pt)
        if search_results:
            log.info(
                "bulk_canonize_pt_fallback",
                entry_id=entry.id,
                name_pt=ce.name_pt,
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

        detailed = await provider.get_card_details(source_card)
        if detailed:
            repo.upsert_card(detailed)
            repo.upsert_source_card(detailed, card_id=card_id)

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

    return "canonized"


async def bulk_canonize(
    engine: Engine,
    user_id: str,
    provider: object,
    concurrency: int = 3,
    limit: int | None = None,
    repo: Repository | None = None,
) -> BulkCanonizeResult:
    """Bulk canonize all unlinked/orphan collection entries for a user.

    Parameters
    ----------
    engine : Engine
        SQLAlchemy engine.
    user_id : str
        The user whose collection to process.
    provider : object
        MYP provider instance (must have search_card, get_card_details,
        fetch_current_price, close methods).
    concurrency : int
        Max parallel MYP requests.
    limit : int | None
        Cap on entries to process (None = all).
    repo : Repository | None
        Optional repository instance. If None, creates one from engine.

    Returns
    -------
    BulkCanonizeResult
        Summary with counts.
    """
    entries = _get_unlinked_entries(engine, user_id, limit)
    result = BulkCanonizeResult(total=len(entries))

    if not entries:
        log.info("bulk_canonize_empty", user_id=user_id)
        return result

    if repo is None:
        # Bypass __init__ to avoid create_all/_ensure_columns (matches decks/importer.py pattern)
        repo = Repository.__new__(Repository)
        repo.engine = engine

    semaphore = asyncio.Semaphore(concurrency)

    async def _process(entry: UserCollectionRow) -> None:
        async with semaphore:
            try:
                status = await _canonize_single(repo, entry, provider)
                if status == "canonized":
                    result.canonized += 1
                log.info(
                    "bulk_canonize_entry",
                    entry_id=entry.id,
                    status=status,
                    progress=f"{result.canonized + result.failed + result.rate_limited}"
                    f"/{result.total}",
                )
            except RateLimitError as exc:
                result.rate_limited += 1
                result.errors.append({"entry_id": str(entry.id), "error": str(exc)})
                log.warning(
                    "bulk_canonize_rate_limited",
                    entry_id=entry.id,
                    error=str(exc),
                )
            except (NotFoundError, ServerError, Exception) as exc:
                result.failed += 1
                result.errors.append({"entry_id": str(entry.id), "error": str(exc)})
                log.warning(
                    "bulk_canonize_failed",
                    entry_id=entry.id,
                    error=str(exc),
                )

    tasks = [asyncio.create_task(_process(entry)) for entry in entries]
    await asyncio.gather(*tasks)

    log.info(
        "bulk_canonize_complete",
        user_id=user_id,
        total=result.total,
        canonized=result.canonized,
        failed=result.failed,
        skipped=result.skipped,
        rate_limited=result.rate_limited,
    )

    return result
