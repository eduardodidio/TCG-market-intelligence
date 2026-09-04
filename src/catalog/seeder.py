"""Catalog seeder — batch upsert cards + source_cards from Scryfall bulk data.

Reads parsed CatalogCard objects and inserts them into the database in
batches, creating both ``cards`` rows and ``source_cards`` entries pointing
to LigaMagic search URLs.  Fully idempotent: running twice produces no
duplicates thanks to INSERT OR IGNORE semantics on unique constraints.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from sqlalchemy import create_engine, event, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from src.catalog.scryfall import CatalogCard, parse_bulk_cards
from src.database.models import Base, CardRow, SourceCardRow
from src.providers.liga.provider import _build_card_url

log = structlog.get_logger()


@dataclass
class SeedResult:
    """Counts returned by :func:`seed_catalog`."""

    cards_inserted: int = 0
    cards_updated: int = 0
    cards_skipped: int = 0
    source_cards_created: int = 0
    errors: list[str] = field(default_factory=list)
    elapsed_seconds: float = 0.0


def _setup_sqlite_pragmas(engine) -> None:  # pragma: no cover — same as Repository
    """Enable PRAGMA foreign_keys=ON and WAL mode for SQLite connections."""
    if str(engine.url).startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _set_pragmas(dbapi_conn, _connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.close()


def _process_card_batch(
    session: Session,
    batch: list[CatalogCard],
    result: SeedResult,
) -> None:
    """Insert a batch of cards and their source_cards entries."""
    # --- Step 1: INSERT OR IGNORE cards ---
    for card in batch:
        stmt = (
            sqlite_insert(CardRow)
            .values(
                game="magic",
                name_en=card.name_en,
                name_pt=card.name_pt,
                set_code=card.set_code,
                collector_number=card.collector_number,
                rarity=card.rarity,
                color_identity=card.color_identity,
                mana_cost=card.mana_cost,
                type_line=card.type_line,
                image_uri=card.image_uri,
            )
            .on_conflict_do_nothing(index_elements=["game", "set_code", "collector_number"])
        )
        row_result = session.execute(stmt)
        if row_result.rowcount > 0:
            result.cards_inserted += 1
        else:
            result.cards_skipped += 1

    # Flush so that card IDs are visible for the look-up below
    session.flush()

    # --- Step 2: Look up card IDs and create source_cards entries ---
    # Build a mapping of (set_code, collector_number) -> card_id
    set_cn_pairs = [(c.set_code, c.collector_number) for c in batch]
    # Query all card IDs for this batch in one go
    card_id_map: dict[tuple[str, str], int] = {}
    # Process in sub-batches to avoid overly large IN clauses
    for i in range(0, len(set_cn_pairs), 200):
        sub = set_cn_pairs[i : i + 200]
        conditions = [(CardRow.set_code == sc) & (CardRow.collector_number == cn) for sc, cn in sub]
        if not conditions:
            continue
        # OR all conditions together
        from sqlalchemy import or_

        stmt = select(CardRow.id, CardRow.set_code, CardRow.collector_number).where(
            CardRow.game == "magic",
            or_(*conditions),
        )
        rows = session.execute(stmt).all()
        for row in rows:
            card_id_map[(row.set_code, row.collector_number)] = row.id

    # Insert source_cards
    for card in batch:
        card_id = card_id_map.get((card.set_code, card.collector_number))
        if card_id is None:
            continue

        external_id = f"liga_catalog_{card.set_code}_{card.collector_number}"
        url = _build_card_url(card.name_en)

        stmt = (
            sqlite_insert(SourceCardRow)
            .values(
                source="liga",
                external_id=external_id,
                card_id=card_id,
                url=url,
                name_en=card.name_en,
                name_pt=card.name_pt,
                set_code=card.set_code,
                collector_number=card.collector_number,
            )
            .on_conflict_do_nothing(index_elements=["source", "external_id"])
        )
        row_result = session.execute(stmt)
        if row_result.rowcount > 0:
            result.source_cards_created += 1


def seed_catalog(
    db_url: str,
    bulk_path: Path,
    batch_size: int = 500,
) -> SeedResult:
    """Seed the database with cards from a Scryfall bulk data file.

    Iterates through the parsed cards in batches, inserting cards and
    creating Liga source_cards entries.  Commits per batch so that
    progress is not lost on failure.

    Args:
        db_url: SQLAlchemy database URL (e.g. ``sqlite:///tcg_market.db``).
        bulk_path: Path to the Scryfall bulk data JSON file.
        batch_size: Number of cards to process per batch/commit.

    Returns:
        A :class:`SeedResult` with counts and elapsed time.
    """
    start = time.monotonic()
    result = SeedResult()

    engine = create_engine(db_url, echo=False)
    _setup_sqlite_pragmas(engine)
    Base.metadata.create_all(engine)

    batch: list[CatalogCard] = []
    total_processed = 0

    log.info("catalog_seed.start", bulk_path=str(bulk_path), batch_size=batch_size)

    for card in parse_bulk_cards(bulk_path):
        batch.append(card)

        if len(batch) >= batch_size:
            try:
                with Session(engine) as session:
                    _process_card_batch(session, batch, result)
                    session.commit()
            except Exception as exc:
                error_msg = f"Batch error at offset {total_processed}: {exc}"
                log.error("catalog_seed.batch_error", error=str(exc), offset=total_processed)
                result.errors.append(error_msg)

            total_processed += len(batch)
            batch.clear()

            if total_processed % 1000 == 0:
                log.info(
                    "catalog_seed.progress",
                    processed=total_processed,
                    inserted=result.cards_inserted,
                    skipped=result.cards_skipped,
                    source_cards=result.source_cards_created,
                )

    # Process remaining cards
    if batch:
        try:
            with Session(engine) as session:
                _process_card_batch(session, batch, result)
                session.commit()
        except Exception as exc:
            error_msg = f"Final batch error at offset {total_processed}: {exc}"
            log.error("catalog_seed.batch_error", error=str(exc), offset=total_processed)
            result.errors.append(error_msg)

        total_processed += len(batch)

    result.elapsed_seconds = round(time.monotonic() - start, 2)

    log.info(
        "catalog_seed.complete",
        cards_inserted=result.cards_inserted,
        cards_skipped=result.cards_skipped,
        source_cards_created=result.source_cards_created,
        errors=len(result.errors),
        elapsed_seconds=result.elapsed_seconds,
    )

    engine.dispose()
    return result
