"""Grouped ban list queries and sync status (F177-T04).

Ban list rows in ``card_legalities`` are stored per printing, so the same
banned/restricted card can appear multiple times (once per set/collector
number). These queries group by card name so the API returns one entry per
card, along with whether the requesting user owns any printing of it.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.database.models import CardLegalityRow, CardRow, LegalityHistoryRow, UserCollectionRow

_ALLOWED_STATUSES = {"banned", "restricted"}
_STATUS_SEVERITY = {"banned": 2, "restricted": 1}


def list_banlist_grouped(
    engine: Engine,
    format: str,
    status: str | None = None,
    search: str | None = None,
    user_id: str | None = None,
    owned_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Banned/restricted cards for ``format``, one entry per lower(name_en).

    Returns ``(entries, total)`` where ``total`` is the count of grouped
    entries (after grouping, before pagination).
    """
    if status is not None and status not in _ALLOWED_STATUSES:
        raise ValueError(f"Invalid status: {status!r}. Must be 'banned', 'restricted', or None.")

    if owned_only and user_id is None:
        return [], 0

    with Session(engine) as session:
        stmt = (
            select(
                CardLegalityRow.card_id,
                CardLegalityRow.status,
                CardLegalityRow.effective_date,
                CardRow.name_en,
                CardRow.name_pt,
                CardRow.set_code,
                CardRow.collector_number,
            )
            .join(CardRow, CardRow.id == CardLegalityRow.card_id)
            .where(CardLegalityRow.format == format)
        )
        if status is not None:
            stmt = stmt.where(CardLegalityRow.status == status)
        else:
            stmt = stmt.where(CardLegalityRow.status.in_(_ALLOWED_STATUSES))
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(CardRow.name_en.ilike(pattern) | CardRow.name_pt.ilike(pattern))

        rows = session.execute(stmt).all()

        owned_by_card_id: dict[int, int] = {}
        owned_by_name: dict[str, int] = {}
        if user_id is not None:
            owned_stmt = select(
                UserCollectionRow.card_id, UserCollectionRow.name_en, UserCollectionRow.quantity
            ).where(UserCollectionRow.user_id == user_id)
            for card_id, name_en, quantity in session.execute(owned_stmt).all():
                quantity = quantity or 0
                if card_id is not None:
                    owned_by_card_id[card_id] = owned_by_card_id.get(card_id, 0) + quantity
                else:
                    key = (name_en or "").strip().lower()
                    owned_by_name[key] = owned_by_name.get(key, 0) + quantity

        groups: dict[str, dict] = {}
        for r in rows:
            key = (r.name_en or "").strip().lower()
            group = groups.get(key)
            if group is None:
                group = {
                    "key": key,
                    "printings": [],
                    "name_en": r.name_en,
                    "name_pt": r.name_pt,
                }
                groups[key] = group
            group["printings"].append(r)

        entries: list[dict] = []
        for group in groups.values():
            printings = group["printings"]
            card_ids = {p.card_id for p in printings}

            representative = None
            if user_id is not None:
                for p in printings:
                    if p.card_id in owned_by_card_id:
                        representative = p
                        break
            if representative is None:
                representative = min(printings, key=lambda p: p.card_id)

            group_status = max(
                (p.status for p in printings), key=lambda s: _STATUS_SEVERITY.get(s, 0)
            )
            effective_dates = [p.effective_date for p in printings if p.effective_date is not None]
            effective_date = max(effective_dates) if effective_dates else None

            owned_quantity = sum(owned_by_card_id.get(cid, 0) for cid in card_ids)
            owned_quantity += owned_by_name.get(group["key"], 0)
            owned = owned_quantity > 0

            if owned_only and not owned:
                continue

            entries.append(
                {
                    "card_id": representative.card_id,
                    "name_en": group["name_en"],
                    "name_pt": group["name_pt"],
                    "set_code": representative.set_code,
                    "collector_number": representative.collector_number,
                    "format": format,
                    "status": group_status,
                    "effective_date": effective_date,
                    "printings": len(printings),
                    "owned": owned,
                    "owned_quantity": owned_quantity,
                }
            )

        entries.sort(
            key=lambda e: (-_STATUS_SEVERITY.get(e["status"], 0), (e["name_en"] or "").lower())
        )

        total = len(entries)
        page = entries[offset : offset + limit]
        return page, total


def get_banlist_status(engine: Engine) -> dict:
    """Sync freshness and counts for the ban list."""
    with Session(engine) as session:
        last_synced_at: datetime | None = session.execute(
            select(func.max(CardLegalityRow.updated_at))
        ).scalar_one_or_none()
        legalities_count = session.execute(
            select(func.count()).select_from(CardLegalityRow)
        ).scalar_one()
        banned_count = session.execute(
            select(func.count())
            .select_from(CardLegalityRow)
            .where(CardLegalityRow.status == "banned")
        ).scalar_one()
        restricted_count = session.execute(
            select(func.count())
            .select_from(CardLegalityRow)
            .where(CardLegalityRow.status == "restricted")
        ).scalar_one()
        history_count = session.execute(
            select(func.count()).select_from(LegalityHistoryRow)
        ).scalar_one()
        formats = session.execute(
            select(func.count(func.distinct(CardLegalityRow.format)))
        ).scalar_one()

        return {
            "last_synced_at": last_synced_at,
            "legalities_count": legalities_count,
            "banned_count": banned_count,
            "restricted_count": restricted_count,
            "history_count": history_count,
            "formats": formats,
        }
