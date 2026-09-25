"""Batched writer for card legalities and legality-change history.

Replaces per-row upserts (one INSERT round trip per row) with chunked
multi-row statements so a full banlist sync against Neon finishes without
timing out.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from datetime import datetime

import structlog
from sqlalchemy import Engine, func, insert
from sqlalchemy.orm import Session

from src.database.compat import dialect_insert
from src.database.models import CardLegalityRow, LegalityHistoryRow
from src.domain.models import CardLegality, LegalityChange

log = structlog.get_logger()

CHUNK_SIZE = 500


def _chunks(seq: Sequence, n: int) -> Iterator[Sequence]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def bulk_upsert_legalities(
    engine: Engine,
    legalities: list[CardLegality],
    chunk_size: int = CHUNK_SIZE,
) -> int:
    """Multi-row upsert of card legalities, chunked.

    One INSERT ... ON CONFLICT (card_id, format) DO UPDATE statement per
    chunk. Duplicate (card_id, format) keys within a chunk are deduplicated
    (last wins), since PostgreSQL rejects duplicate keys in a single
    statement. An existing non-null effective_date is preserved when the
    incoming value is None.
    """
    if not legalities:
        return 0

    now = datetime.now()
    total = 0
    with Session(engine) as session:
        for chunk in _chunks(legalities, chunk_size):
            deduped: dict[tuple[int, str], CardLegality] = {}
            for leg in chunk:
                deduped[(leg.card_id, leg.format)] = leg
            rows = [
                {
                    "card_id": leg.card_id,
                    "format": leg.format,
                    "status": leg.status,
                    "effective_date": leg.effective_date,
                    "updated_at": now,
                }
                for leg in deduped.values()
            ]
            stmt = dialect_insert(engine, CardLegalityRow).values(rows)
            stmt = stmt.on_conflict_do_update(
                index_elements=["card_id", "format"],
                set_={
                    "status": stmt.excluded.status,
                    "effective_date": func.coalesce(
                        stmt.excluded.effective_date, CardLegalityRow.effective_date
                    ),
                    "updated_at": stmt.excluded.updated_at,
                },
            )
            session.execute(stmt)
            total += len(rows)
        session.commit()

    log.info("bulk_upsert_legalities", rows=total)
    return total


def bulk_insert_legality_changes(
    engine: Engine,
    changes: list[LegalityChange],
    chunk_size: int = CHUNK_SIZE,
) -> int:
    """Multi-row insert of legality change history rows, chunked."""
    if not changes:
        return 0

    total = 0
    with Session(engine) as session:
        for chunk in _chunks(changes, chunk_size):
            rows = [
                {
                    "card_id": c.card_id,
                    "format": c.format,
                    "old_status": c.old_status,
                    "new_status": c.new_status,
                    "changed_at": c.changed_at,
                    "source": c.source,
                }
                for c in chunk
            ]
            session.execute(insert(LegalityHistoryRow), rows)
            total += len(rows)
        session.commit()

    log.info("bulk_insert_legality_changes", rows=total)
    return total
