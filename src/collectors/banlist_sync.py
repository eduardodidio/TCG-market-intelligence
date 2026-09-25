"""Banlist sync orchestrator — fetch legality data from Scryfall and update local DB."""

from __future__ import annotations

import json
import zlib
from datetime import date, datetime
from typing import AsyncIterator

import httpx
import structlog

from src.database.legality_writer import bulk_insert_legality_changes, bulk_upsert_legalities
from src.database.repository import Repository
from src.domain.models import BanlistSyncSummary, CardLegality, LegalityChange
from src.utils.set_code_map import map_to_scryfall_set_code

log = structlog.get_logger()

FLUSH_EVERY = 5000
MATCH_CHECK_THRESHOLD = 1000

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


def _select_download_url(catalog: dict) -> str | None:
    """Pick the default_cards download URL, preferring JSONL over JSON array."""
    for entry in catalog.get("data", []):
        if entry.get("type") == "default_cards":
            return entry.get("jsonl_download_uri") or entry.get("download_uri")
    return None


def _parse_bulk_line(line: bytes) -> dict | None:
    """Parse one line of a bulk data file (JSONL or JSON-array-with-trailing-comma).

    Returns None for blank lines and the `[` / `]` array delimiters. Raises
    json.JSONDecodeError for malformed content so the caller can count it as
    an error (as opposed to a line that was never meant to parse).
    """
    stripped = line.strip()
    if not stripped or stripped in (b"[", b"]"):
        return None
    if stripped.endswith(b","):
        stripped = stripped[:-1]
    if not stripped:
        return None
    return json.loads(stripped)


def _build_index_keys(set_code: str, collector_number: str) -> set[tuple[str, str]]:
    """Build lookup keys covering both raw and Scryfall-mapped set codes,
    and both raw and zero-stripped collector numbers."""
    raw_set = (set_code or "").strip().lower()
    mapped_set = map_to_scryfall_set_code(set_code or "").lower()
    cn = (collector_number or "").strip().lower()
    cn_stripped = cn.lstrip("0") or "0"

    keys: set[tuple[str, str]] = set()
    for s in {raw_set, mapped_set}:
        for c in {cn, cn_stripped}:
            keys.add((s, c))
    return keys


def _classify(
    card_id: int,
    fmt: str,
    status: str,
    existing: str | None,
    owned: bool,
    first_sync: bool,
    scope: str,
) -> tuple[bool, LegalityChange | None, date | None]:
    """Decide whether/how to persist one (card, format, status) triple.

    Returns (write, change, effective_date). `write` says whether a
    CardLegality row should be sent to the writer. `change` is a
    LegalityChange to append to history, or None.
    """
    should_store = (
        scope == "full"
        or status in ("banned", "restricted")
        or owned
        or existing is not None
    )
    if not should_store:
        return False, None, None

    if existing == status:
        return False, None, None

    if existing is not None:
        change = LegalityChange(
            card_id=card_id,
            format=fmt,
            old_status=existing,
            new_status=status,
            source="scryfall_sync",
        )
        return True, change, date.today()

    if status in ("banned", "restricted"):
        if first_sync:
            change = LegalityChange(
                card_id=card_id,
                format=fmt,
                old_status=None,
                new_status=status,
                source="scryfall_baseline",
            )
            return True, change, None
        change = LegalityChange(
            card_id=card_id,
            format=fmt,
            old_status=None,
            new_status=status,
            source="scryfall_sync",
        )
        return True, change, date.today()

    return True, None, None


async def _iter_bulk_lines(resp: httpx.Response, gzipped: bool) -> AsyncIterator[bytes]:
    """Stream complete lines out of a (possibly gzipped) HTTP response body.

    Gzip detection also falls back to sniffing the magic bytes of the first
    chunk, in case the URL doesn't carry a `.gz` suffix.
    """
    decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS) if gzipped else None
    buffer = b""
    first = True

    async for raw_chunk in resp.aiter_bytes():
        if first:
            first = False
            if decompressor is None and raw_chunk[:2] == b"\x1f\x8b":
                decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)

        chunk = decompressor.decompress(raw_chunk) if decompressor else raw_chunk
        if not chunk:
            continue

        buffer += chunk
        lines = buffer.split(b"\n")
        buffer = lines.pop()
        for line in lines:
            yield line

    if decompressor:
        buffer += decompressor.flush()
    if buffer:
        yield buffer


async def run_banlist_sync(
    db_url: str,
    bulk: bool = True,
    limit: int | None = None,
    scope: str = "compact",
) -> BanlistSyncSummary:
    """Run a banlist sync from Scryfall.

    bulk=True: download the default-cards bulk file (recommended for full sync).
    bulk=False: per-card mode using individual Scryfall API calls.
    scope="compact" (default): only store banned/restricted rows, rows for
    owned cards, and rows that already exist locally (so transitions still
    get picked up). scope="full": store every tracked format for every
    matched card.
    """
    if scope not in ("compact", "full"):
        raise ValueError(f"invalid scope: {scope!r} (expected 'compact' or 'full')")

    summary = BanlistSyncSummary(started_at=datetime.now())
    repo = Repository(db_url)

    if bulk:
        summary = await _sync_bulk(repo, summary, limit, scope)
    else:
        summary = await _sync_per_card(repo, summary, limit, scope)

    summary.finished_at = datetime.now()
    return summary


def _make_client(**kwargs) -> httpx.AsyncClient:
    headers = {
        "User-Agent": "TEDHC-Market/1.0",
        "Accept": "application/json",
    }
    kwargs.setdefault("headers", headers)
    kwargs.setdefault("follow_redirects", True)
    return httpx.AsyncClient(**kwargs)


def _build_card_index(repo: Repository) -> dict[tuple[str, str], list[int]]:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from src.database.models import CardRow

    index: dict[tuple[str, str], list[int]] = {}
    with Session(repo.engine) as session:
        stmt = select(CardRow.id, CardRow.set_code, CardRow.collector_number).where(
            CardRow.set_code.isnot(None),
            CardRow.collector_number.isnot(None),
        )
        for row in session.execute(stmt).all():
            for key in _build_index_keys(row.set_code, row.collector_number):
                index.setdefault(key, []).append(row.id)
    return index


def _load_owned_card_ids(repo: Repository) -> set[int]:
    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from src.database.models import UserCollectionRow

    with Session(repo.engine) as session:
        stmt = select(UserCollectionRow.card_id).where(
            UserCollectionRow.card_id.isnot(None)
        ).distinct()
        return set(session.execute(stmt).scalars().all())


async def _sync_bulk(
    repo: Repository,
    summary: BanlistSyncSummary,
    limit: int | None,
    scope: str,
) -> BanlistSyncSummary:
    """Bulk sync using Scryfall's default_cards bulk data download."""
    async with _make_client(timeout=300) as client:
        log.info("banlist_sync_fetching_catalog")
        catalog_resp = await client.get("https://api.scryfall.com/bulk-data")
        catalog_resp.raise_for_status()
        catalog = catalog_resp.json()

        download_url = _select_download_url(catalog)
        if not download_url:
            log.error("banlist_sync_no_download_url")
            summary.errors += 1
            return summary

        log.info("banlist_sync_building_card_index")
        card_index = _build_card_index(repo)
        if not card_index:
            log.warning("banlist_sync_no_local_cards")
            return summary
        log.info("banlist_sync_local_cards_indexed", count=len(card_index))

        owned_card_ids = _load_owned_card_ids(repo)
        existing_legalities = _load_existing_legalities(repo)
        first_sync = len(existing_legalities) == 0

        gzipped = download_url.endswith(".gz")

        pending_legalities: list[CardLegality] = []
        pending_changes: list[LegalityChange] = []
        matched_card_ids: set[int] = set()
        parsed_lines = 0
        skipped_unchanged = 0

        def _flush() -> None:
            nonlocal pending_legalities, pending_changes
            if pending_legalities:
                summary.legalities_upserted += bulk_upsert_legalities(
                    repo.engine, pending_legalities
                )
                pending_legalities = []
            if pending_changes:
                summary.changes_detected += bulk_insert_legality_changes(
                    repo.engine, pending_changes
                )
                pending_changes = []

        log.info("banlist_sync_downloading", url=download_url[:80])
        async with client.stream("GET", download_url) as resp:
            resp.raise_for_status()
            async for raw_line in _iter_bulk_lines(resp, gzipped):
                try:
                    card = _parse_bulk_line(raw_line)
                except json.JSONDecodeError:
                    summary.errors += 1
                    continue
                if card is None:
                    continue

                parsed_lines += 1

                key = (
                    str(card.get("set", "")).lower(),
                    str(card.get("collector_number", "")).lower(),
                )
                card_ids = card_index.get(key)
                if not card_ids:
                    continue

                legalities = _parse_legalities_from_card(card)
                for card_id in card_ids:
                    owned = card_id in owned_card_ids
                    matched_before_this_card = card_id in matched_card_ids
                    if limit and not matched_before_this_card and len(matched_card_ids) >= limit:
                        continue

                    for fmt, status in legalities.items():
                        existing = existing_legalities.get((card_id, fmt))
                        write, change, effective_date = _classify(
                            card_id, fmt, status, existing, owned, first_sync, scope
                        )
                        if not write:
                            skipped_unchanged += 1
                            continue
                        pending_legalities.append(
                            CardLegality(
                                card_id=card_id,
                                format=fmt,
                                status=status,
                                effective_date=effective_date,
                            )
                        )
                        if change:
                            pending_changes.append(change)
                        existing_legalities[(card_id, fmt)] = status

                    matched_card_ids.add(card_id)

                    if len(pending_legalities) >= FLUSH_EVERY:
                        _flush()

                if limit and len(matched_card_ids) >= limit:
                    break

        _flush()
        summary.cards_processed = len(matched_card_ids)

        log.info(
            "banlist_sync_diagnostics",
            lines_parsed=parsed_lines,
            cards_matched=len(matched_card_ids),
            rows_written=summary.legalities_upserted,
            changes=summary.changes_detected,
            skipped_unchanged=skipped_unchanged,
        )

        if parsed_lines == 0:
            raise RuntimeError("banlist_sync parsed 0 lines from bulk file")
        if len(matched_card_ids) == 0 and parsed_lines > MATCH_CHECK_THRESHOLD:
            raise RuntimeError(
                "banlist_sync matched 0 cards — check set-code mapping / bulk format"
            )

    return summary


async def _sync_per_card(
    repo: Repository,
    summary: BanlistSyncSummary,
    limit: int | None,
    scope: str,
) -> BanlistSyncSummary:
    """Per-card sync using individual Scryfall API calls."""
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.orm import Session

    from src.database.models import CardRow

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

    owned_card_ids = _load_owned_card_ids(repo)
    existing_legalities = _load_existing_legalities(repo)
    first_sync = len(existing_legalities) == 0

    pending_legalities: list[CardLegality] = []
    pending_changes: list[LegalityChange] = []

    async with _make_client(timeout=30) as client:
        for card_id, set_code, collector_number in card_list:
            try:
                mapped_set = map_to_scryfall_set_code(set_code)
                url = f"https://api.scryfall.com/cards/{mapped_set}/{collector_number}"
                resp = await client.get(url)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()
                card_json = resp.json()

                owned = card_id in owned_card_ids
                legalities = _parse_legalities_from_card(card_json)
                for fmt, status in legalities.items():
                    existing = existing_legalities.get((card_id, fmt))
                    write, change, effective_date = _classify(
                        card_id, fmt, status, existing, owned, first_sync, scope
                    )
                    if not write:
                        continue
                    pending_legalities.append(
                        CardLegality(
                            card_id=card_id,
                            format=fmt,
                            status=status,
                            effective_date=effective_date,
                        )
                    )
                    if change:
                        pending_changes.append(change)
                    existing_legalities[(card_id, fmt)] = status

                summary.cards_processed += 1

            except Exception as exc:
                log.warning("banlist_sync_card_error", card_id=card_id, error=str(exc))
                summary.errors += 1

            await asyncio.sleep(0.1)

    if pending_legalities:
        summary.legalities_upserted = bulk_upsert_legalities(repo.engine, pending_legalities)
    if pending_changes:
        summary.changes_detected = bulk_insert_legality_changes(repo.engine, pending_changes)

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
