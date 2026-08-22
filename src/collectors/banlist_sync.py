"""Banlist sync orchestrator — fetch legality data from Scryfall and update local DB."""

from __future__ import annotations

import json
from datetime import date, datetime

import httpx
import structlog

from src.database.repository import Repository
from src.domain.models import BanlistSyncSummary, CardLegality, LegalityChange

log = structlog.get_logger()

# Formats we care about from Scryfall
TRACKED_FORMATS = [
    "standard",
    "future",
    "historic",
    "timeless",
    "gladiator",
    "pioneer",
    "explorer",
    "modern",
    "legacy",
    "pauper",
    "vintage",
    "penny",
    "commander",
    "oathbreaker",
    "standardbrawl",
    "brawl",
    "alchemy",
    "paupercommander",
    "duel",
    "oldschool",
    "premodern",
    "predh",
]


def _parse_legalities_from_card(card_json: dict) -> dict[str, str]:
    """Extract legalities dict from a Scryfall card JSON object.

    Returns dict of format->status for tracked formats only.
    """
    legalities = card_json.get("legalities", {})
    return {fmt: legalities[fmt] for fmt in TRACKED_FORMATS if fmt in legalities}


async def run_banlist_sync(
    db_url: str,
    bulk: bool = True,
    limit: int | None = None,
) -> BanlistSyncSummary:
    """Run a banlist sync from Scryfall.

    bulk=True: download the default-cards NDJSON file (recommended for full sync).
    bulk=False: per-card mode using individual Scryfall API calls.
    """
    summary = BanlistSyncSummary(started_at=datetime.now())
    repo = Repository(db_url)

    if bulk:
        summary = await _sync_bulk(repo, summary, limit)
    else:
        summary = await _sync_per_card(repo, summary, limit)

    summary.finished_at = datetime.now()
    return summary


async def _sync_bulk(
    repo: Repository,
    summary: BanlistSyncSummary,
    limit: int | None,
) -> BanlistSyncSummary:
    """Bulk sync using Scryfall NDJSON bulk data download."""
    async with httpx.AsyncClient(timeout=300) as client:
        # 1. Fetch bulk data catalog to get download URL
        log.info("banlist_sync_fetching_catalog")
        catalog_resp = await client.get("https://api.scryfall.com/bulk-data")
        catalog_resp.raise_for_status()
        catalog = catalog_resp.json()

        download_url = None
        for entry in catalog.get("data", []):
            if entry.get("type") == "default_cards":
                download_url = entry.get("download_uri")
                break

        if not download_url:
            log.error("banlist_sync_no_download_url")
            summary.errors += 1
            return summary

        # 2. Build a lookup of local cards by (set_code, collector_number)
        log.info("banlist_sync_building_card_index")
        from sqlalchemy import select
        from sqlalchemy.orm import Session

        from src.database.models import CardRow

        card_index: dict[tuple[str, str], int] = {}
        with Session(repo.engine) as session:
            stmt = select(CardRow.id, CardRow.set_code, CardRow.collector_number).where(
                CardRow.set_code.isnot(None),
                CardRow.collector_number.isnot(None),
            )
            for row in session.execute(stmt).all():
                key = (row.set_code.lower(), row.collector_number.lower())
                card_index[key] = row.id

        if not card_index:
            log.warning("banlist_sync_no_local_cards")
            return summary

        log.info("banlist_sync_local_cards_indexed", count=len(card_index))

        # 3. Load existing legalities for diff detection
        existing_legalities = _load_existing_legalities(repo)

        # 4. Stream NDJSON and process
        log.info("banlist_sync_downloading_ndjson", url=download_url[:80])
        all_legalities: list[CardLegality] = []
        all_changes: list[LegalityChange] = []
        cards_processed = 0

        async with client.stream("GET", download_url) as resp:
            resp.raise_for_status()
            buffer = b""
            async for chunk in resp.aiter_bytes():
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        card = json.loads(line)
                    except json.JSONDecodeError:
                        summary.errors += 1
                        continue

                    set_code = card.get("set", "").lower()
                    collector_number = card.get("collector_number", "").lower()
                    key = (set_code, collector_number)

                    if key not in card_index:
                        continue

                    card_id = card_index[key]
                    legalities = _parse_legalities_from_card(card)

                    for fmt, status in legalities.items():
                        leg = CardLegality(
                            card_id=card_id,
                            format=fmt,
                            status=status,
                        )

                        # Check for changes
                        old_key = (card_id, fmt)
                        old_status = existing_legalities.get(old_key)
                        if old_status != status:
                            leg.effective_date = date.today()
                            all_changes.append(
                                LegalityChange(
                                    card_id=card_id,
                                    format=fmt,
                                    old_status=old_status,
                                    new_status=status,
                                    changed_at=datetime.now(),
                                )
                            )

                        all_legalities.append(leg)

                    cards_processed += 1
                    if limit and cards_processed >= limit:
                        break

                if limit and cards_processed >= limit:
                    break

        # 5. Batch upsert
        if all_legalities:
            summary.legalities_upserted = repo.upsert_legalities(all_legalities)
        if all_changes:
            summary.changes_detected = repo.insert_legality_changes(all_changes)
        summary.cards_processed = cards_processed

        log.info(
            "banlist_sync_complete",
            cards=cards_processed,
            upserted=summary.legalities_upserted,
            changes=summary.changes_detected,
        )

    return summary


async def _sync_per_card(
    repo: Repository,
    summary: BanlistSyncSummary,
    limit: int | None,
) -> BanlistSyncSummary:
    """Per-card sync using individual Scryfall API calls."""
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from src.database.models import CardRow

    # Load local cards
    with Session(repo.engine) as session:
        stmt = select(CardRow).where(
            CardRow.set_code.isnot(None),
            CardRow.collector_number.isnot(None),
        )
        if limit:
            stmt = stmt.limit(limit)
        cards = session.execute(stmt).scalars().all()
        card_list = [(c.id, c.set_code, c.collector_number) for c in cards]

    if not card_list:
        return summary

    existing_legalities = _load_existing_legalities(repo)
    all_legalities: list[CardLegality] = []
    all_changes: list[LegalityChange] = []

    async with httpx.AsyncClient(timeout=30) as client:
        for card_id, set_code, collector_number in card_list:
            try:
                url = f"https://api.scryfall.com/cards/{set_code}/{collector_number}"
                resp = await client.get(url)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                card_json = resp.json()

                legalities = _parse_legalities_from_card(card_json)
                for fmt, status in legalities.items():
                    leg = CardLegality(
                        card_id=card_id,
                        format=fmt,
                        status=status,
                    )
                    old_key = (card_id, fmt)
                    old_status = existing_legalities.get(old_key)
                    if old_status != status:
                        leg.effective_date = date.today()
                        all_changes.append(
                            LegalityChange(
                                card_id=card_id,
                                format=fmt,
                                old_status=old_status,
                                new_status=status,
                                changed_at=datetime.now(),
                            )
                        )
                    all_legalities.append(leg)

                summary.cards_processed += 1

            except Exception as exc:
                log.warning("banlist_sync_card_error", card_id=card_id, error=str(exc))
                summary.errors += 1

            # Rate limit: 100ms between requests (10 req/s)
            await asyncio.sleep(0.1)

    if all_legalities:
        summary.legalities_upserted = repo.upsert_legalities(all_legalities)
    if all_changes:
        summary.changes_detected = repo.insert_legality_changes(all_changes)

    return summary


def _load_existing_legalities(repo: Repository) -> dict[tuple[int, str], str]:
    """Load all existing legalities as a dict of (card_id, format) -> status."""
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from src.database.models import CardLegalityRow

    result: dict[tuple[int, str], str] = {}
    with Session(repo.engine) as session:
        stmt = select(
            CardLegalityRow.card_id,
            CardLegalityRow.format,
            CardLegalityRow.status,
        )
        for row in session.execute(stmt).all():
            result[(row.card_id, row.format)] = row.status
    return result
