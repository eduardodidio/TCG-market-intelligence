"""Queue functions for ``deck_suggestion_requests`` (F172).

Plain functions over a SQLAlchemy ``Engine`` (pass ``repo.engine``). Every
public function ensures the table exists first. Returned rows are detached.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from sqlalchemy import Engine, and_, func, or_, select, update
from sqlalchemy.orm import Session

from src.deck_suggestions.models import DeckSuggestionRequestRow as Row

WUBRG = "WUBRG"
OPEN_STATUSES = ("pending", "processing")
MAX_ERROR_LENGTH = 1000

_ensured_engines: set[int] = set()


def ensure_table(engine: Engine) -> None:
    """Create the table if missing. Memoized per engine instance."""
    if id(engine) in _ensured_engines:
        return
    Row.__table__.create(engine, checkfirst=True)
    _ensured_engines.add(id(engine))


def _session(engine: Engine) -> Session:
    return Session(engine, expire_on_commit=False)


def colors_to_str(colors: list[str] | None) -> str | None:
    """Serialize colors to a WUBRG-ordered string ("C" for colorless)."""
    if not colors:
        return None
    letters = {c.strip().upper() for c in colors if c and c.strip()}
    if not letters:
        return None
    if letters == {"C"}:
        return "C"
    return "".join(c for c in WUBRG if c in letters) or None


def colors_from_str(value: str | None) -> list[str]:
    """Deserialize a stored colors string into a list of letters."""
    if not value:
        return []
    return list(value)


def create_request(
    engine: Engine,
    *,
    user_id: str,
    format_name: str,
    commander_card_id: int | None,
    commander_name: str | None,
    colors: str | None,
    archetype: str | None,
    notes: str | None,
) -> Row:
    """Insert a new pending request and return it."""
    ensure_table(engine)
    with _session(engine) as session:
        row = Row(
            user_id=user_id,
            format_name=format_name,
            commander_card_id=commander_card_id,
            commander_name=commander_name,
            colors=colors,
            archetype=archetype,
            notes=notes,
            status="pending",
            attempts=0,
        )
        session.add(row)
        session.commit()
        return row


def count_open_requests(engine: Engine, user_id: str) -> int:
    """Count the user's pending + processing requests."""
    ensure_table(engine)
    with _session(engine) as session:
        stmt = select(func.count(Row.id)).where(
            Row.user_id == user_id, Row.status.in_(OPEN_STATUSES)
        )
        return int(session.execute(stmt).scalar_one())


def list_requests(
    engine: Engine, user_id: str, *, status: str | None = None, limit: int = 20
) -> list[Row]:
    """Return the user's requests, newest first."""
    ensure_table(engine)
    with _session(engine) as session:
        stmt = select(Row).where(Row.user_id == user_id)
        if status is not None:
            stmt = stmt.where(Row.status == status)
        stmt = stmt.order_by(Row.created_at.desc(), Row.id.desc()).limit(limit)
        return list(session.execute(stmt).scalars().all())


def get_request(engine: Engine, request_id: int, user_id: str) -> Row | None:
    """Return the request if it exists and belongs to ``user_id``."""
    ensure_table(engine)
    with _session(engine) as session:
        stmt = select(Row).where(Row.id == request_id, Row.user_id == user_id)
        return session.execute(stmt).scalar_one_or_none()


def delete_pending_request(engine: Engine, request_id: int, user_id: str) -> bool:
    """Delete the user's request only while it is still pending."""
    ensure_table(engine)
    with _session(engine) as session:
        row = session.execute(
            select(Row).where(
                Row.id == request_id, Row.user_id == user_id, Row.status == "pending"
            )
        ).scalar_one_or_none()
        if row is None:
            return False
        session.delete(row)
        session.commit()
        return True


def _select_candidates(session: Session, limit: int, cutoff: datetime) -> list[tuple]:
    """Return ``(id, status, started_at)`` of claimable rows, oldest first."""
    stmt = (
        select(Row.id, Row.status, Row.started_at)
        .where(
            or_(
                Row.status == "pending",
                and_(Row.status == "processing", Row.started_at < cutoff),
            )
        )
        .order_by(Row.created_at.asc(), Row.id.asc())
        .limit(limit)
    )
    return [tuple(r) for r in session.execute(stmt).all()]


def claim_pending(
    engine: Engine,
    limit: int,
    *,
    stale_after: timedelta = timedelta(hours=2),
    now: datetime | None = None,
) -> list[Row]:
    """Atomically claim pending (or stale processing) requests.

    Each row is moved to ``processing`` with a conditional UPDATE guarded by
    its previous status (and ``started_at``), so concurrent runners never
    claim the same row twice.
    """
    ensure_table(engine)
    if limit <= 0:
        return []
    now = now or datetime.now()
    cutoff = now - stale_after
    claimed_ids: list[int] = []
    with _session(engine) as session:
        for row_id, old_status, old_started in _select_candidates(session, limit, cutoff):
            conditions = [Row.id == row_id, Row.status == old_status]
            if old_status == "processing":
                conditions.append(Row.started_at == old_started)
            result = session.execute(
                update(Row)
                .where(*conditions)
                .values(status="processing", started_at=now, attempts=Row.attempts + 1)
            )
            session.commit()
            if result.rowcount == 1:
                claimed_ids.append(row_id)
        if not claimed_ids:
            return []
        rows = session.execute(
            select(Row)
            .where(Row.id.in_(claimed_ids))
            .order_by(Row.created_at.asc(), Row.id.asc())
        ).scalars().all()
        return list(rows)


def _update(engine: Engine, request_id: int, **values) -> None:
    ensure_table(engine)
    with _session(engine) as session:
        session.execute(update(Row).where(Row.id == request_id).values(**values))
        session.commit()


def mark_done(engine: Engine, request_id: int, result: dict) -> None:
    """Store the result JSON (UTF-8, not ASCII-escaped) and mark done."""
    _update(
        engine,
        request_id,
        status="done",
        result_json=json.dumps(result, ensure_ascii=False),
        processed_at=datetime.now(),
        error_message=None,
    )


def mark_failed(engine: Engine, request_id: int, error: str) -> None:
    """Mark the request failed with a truncated error message."""
    _update(
        engine,
        request_id,
        status="failed",
        error_message=(error or "")[:MAX_ERROR_LENGTH],
        processed_at=datetime.now(),
    )


def release_for_retry(engine: Engine, request_id: int, error: str) -> None:
    """Return the request to ``pending`` after a transient failure (attempts kept)."""
    _update(
        engine,
        request_id,
        status="pending",
        error_message=(error or "")[:MAX_ERROR_LENGTH],
    )


def set_saved_deck(engine: Engine, request_id: int, deck_id: int) -> None:
    """Link the request to the deck created from its result."""
    _update(engine, request_id, saved_deck_id=deck_id)


def load_result(row: Row) -> dict | None:
    """Parse ``row.result_json``; return None when missing or corrupt."""
    if not row.result_json:
        return None
    try:
        data = json.loads(row.result_json)
    except (TypeError, ValueError):
        return None
    return data if isinstance(data, dict) else None
