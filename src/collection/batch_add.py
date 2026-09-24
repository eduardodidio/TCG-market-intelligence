"""Batch add orchestrator: add multiple cards to user collection.

Links to existing CardRow when possible, creates minimal CardRow otherwise
(same pattern as CSV importer).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.currency.import_conversion import RateLookup, to_brl
from src.database.models import CardRow, UserCollectionRow

log = structlog.get_logger()


@dataclass
class BatchAddEntry:
    """A single card to add to the collection."""

    name_en: str
    set_code: str | None = None
    collector_number: str | None = None
    quantity: int = 1
    quality: str | None = None
    language: str | None = None
    extras: str | None = None
    line_number: int | None = None  # for error reporting
    acquisition_price: Decimal | None = None
    price_currency: str | None = None


@dataclass
class BatchAddError:
    """Error detail for a failed entry."""

    line: int
    text: str
    error: str


@dataclass
class BatchAddResult:
    """Summary of a batch add operation."""

    added: int = 0
    errors: list[BatchAddError] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def batch_add_entries(
    session: Session,
    user_id: str,
    entries: list[BatchAddEntry],
    rate_lookup: RateLookup | None = None,
    today: date | None = None,
) -> BatchAddResult:
    """Add multiple entries to the user's collection.

    For each entry:
    1. If set_code + collector_number → try to link to existing CardRow.
    2. If no match → create minimal CardRow (game="magic").
    3. Insert UserCollectionRow.

    Uses the provided session — caller is responsible for commit/rollback.
    """
    result = BatchAddResult()
    resolved_today = today or date.today()

    for entry in entries:
        savepoint = session.begin_nested()
        try:
            card_id = _resolve_card(session, entry)

            acquisition_price = None
            if entry.acquisition_price is not None:
                if rate_lookup is None:
                    result.warnings.append(
                        f"{entry.name_en}: no exchange rate available, price not stored"
                    )
                else:
                    conversion = to_brl(
                        entry.acquisition_price,
                        entry.price_currency or "BRL",
                        resolved_today,
                        rate_lookup,
                    )
                    acquisition_price = conversion.brl
                    if conversion.warning:
                        result.warnings.append(f"{entry.name_en}: {conversion.warning}")

            row = UserCollectionRow(
                user_id=user_id,
                card_id=card_id,
                set_code=entry.set_code or "",
                collector_number=entry.collector_number or "",
                name_en=entry.name_en,
                quantity=entry.quantity,
                quality=entry.quality,
                language=entry.language,
                extras=entry.extras,
                acquisition_price=acquisition_price,
            )
            session.add(row)
            session.flush()
            savepoint.commit()
            result.added += 1
        except Exception as exc:
            savepoint.rollback()
            line = entry.line_number or 0
            result.errors.append(
                BatchAddError(
                    line=line,
                    text=entry.name_en,
                    error=str(exc),
                )
            )
            log.warning(
                "batch_add_entry_failed",
                name=entry.name_en,
                error=str(exc),
            )

    return result


def _resolve_card(session: Session, entry: BatchAddEntry) -> int:
    """Find or create a CardRow for the given entry.

    Returns the card_id.
    """
    # Try to match existing card if we have set_code + collector_number
    if entry.set_code and entry.collector_number:
        card = session.execute(
            select(CardRow).where(
                CardRow.game == "magic",
                CardRow.set_code == entry.set_code.lower(),
                CardRow.collector_number == entry.collector_number,
            )
        ).scalar_one_or_none()

        if card:
            return card.id

    # Create minimal CardRow
    new_card = CardRow(
        game="magic",
        name_en=entry.name_en,
        set_code=entry.set_code.lower() if entry.set_code else None,
        collector_number=entry.collector_number,
    )
    session.add(new_card)
    session.flush()
    return new_card.id
