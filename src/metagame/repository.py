"""Persistence for metagame snapshots (``meta_decks`` / ``meta_deck_cards``)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import date
from typing import TYPE_CHECKING, Any

from sqlalchemy import delete, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow, UserCollectionRow
from src.decks.importer import _find_card_id
from src.metagame.models import MetaDeckCardRow, MetaDeckRow

if TYPE_CHECKING:
    from src.database.repository import Repository

_SPLIT_SEP = " // "

CardResolver = Callable[[Any], "int | None"]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class MetagameRepository:
    """Read/write metagame snapshots on SQLite or Neon PostgreSQL."""

    def __init__(self, engine: Engine):
        self.engine = engine
        Base.metadata.create_all(engine, tables=[MetaDeckRow.__table__, MetaDeckCardRow.__table__])

    @classmethod
    def from_repo(cls, repo: Repository) -> MetagameRepository:
        return cls(repo.engine)

    # ── Writes ──────────────────────────────────────────────────────────

    def replace_snapshot(
        self,
        fmt: str,
        source: str,
        snapshot_date: date,
        decks: Sequence[Any],
        card_ids: Mapping[tuple[str, str], int | None] | None = None,
        *,
        resolver: CardResolver | None = None,
    ) -> int:
        """Replace the ``(fmt, source, snapshot_date)`` snapshot atomically.

        ``decks`` are objects shaped like ``MetaDeckEntry`` (attributes
        ``external_id``, ``archetype``, ``rank``, ``cards`` …) whose ``cards``
        are shaped like ``MetaCardEntry`` (``name``, ``quantity``, ``board``,
        ``set_code``, ``collector_number``).

        Card id resolution, in priority order:
        1. ``card_ids[(deck.external_id, card.name)]`` when the key is present;
        2. ``resolver(card)`` when given;
        3. ``self.resolve_card_id`` memoised per call by
           ``(name.lower(), set_code, collector_number)``.

        Cards of the old snapshot are deleted explicitly (SQLite may not
        enforce ``ON DELETE CASCADE``). Returns the number of decks stored.
        """
        cache: dict[tuple[str, str | None, str | None], int | None] = {}

        def _default_resolver(card: Any) -> int | None:
            set_code = getattr(card, "set_code", None)
            number = getattr(card, "collector_number", None)
            key = (card.name.lower(), set_code, number)
            if key not in cache:
                cache[key] = self.resolve_card_id(card.name, set_code, number)
            return cache[key]

        resolve = resolver or _default_resolver

        # Resolve before opening the write transaction: the resolver opens its
        # own sessions, which must not interleave with the pending writes.
        resolved: list[list[int | None]] = []
        for deck in decks:
            ids: list[int | None] = []
            for card in deck.cards:
                key = (deck.external_id, card.name)
                if card_ids is not None and key in card_ids:
                    ids.append(card_ids[key])
                else:
                    ids.append(resolve(card))
            resolved.append(ids)

        with Session(self.engine) as s, s.begin():
            old_ids = select(MetaDeckRow.id).where(
                MetaDeckRow.format == fmt,
                MetaDeckRow.source == source,
                MetaDeckRow.snapshot_date == snapshot_date,
            )
            s.execute(delete(MetaDeckCardRow).where(MetaDeckCardRow.meta_deck_id.in_(old_ids)))
            s.execute(
                delete(MetaDeckRow).where(
                    MetaDeckRow.format == fmt,
                    MetaDeckRow.source == source,
                    MetaDeckRow.snapshot_date == snapshot_date,
                )
            )

            for deck, deck_card_ids in zip(decks, resolved, strict=True):
                row = MetaDeckRow(
                    format=fmt,
                    source=source,
                    external_id=deck.external_id,
                    archetype=deck.archetype,
                    commander_name=getattr(deck, "commander_name", None),
                    colors=getattr(deck, "colors", None),
                    rank=deck.rank,
                    meta_share_pct=getattr(deck, "meta_share_pct", None),
                    deck_count=getattr(deck, "deck_count", None),
                    source_url=deck.source_url,
                    event_date=getattr(deck, "event_date", None),
                    snapshot_date=snapshot_date,
                )
                s.add(row)
                s.flush()
                for card, card_id in zip(deck.cards, deck_card_ids, strict=True):
                    s.add(
                        MetaDeckCardRow(
                            meta_deck_id=row.id,
                            card_name=card.name,
                            quantity=card.quantity,
                            board=getattr(card, "board", "main") or "main",
                            card_id=card_id,
                        )
                    )
        return len(decks)

    # ── Reads ───────────────────────────────────────────────────────────

    def latest_snapshot_date(self, fmt: str) -> date | None:
        with Session(self.engine) as s:
            return s.execute(
                select(func.max(MetaDeckRow.snapshot_date)).where(MetaDeckRow.format == fmt)
            ).scalar()

    def list_decks(
        self,
        fmt: str,
        *,
        snapshot_date: date | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[MetaDeckRow], int]:
        """Decks of one snapshot ordered by rank; defaults to the latest one."""
        snap = snapshot_date or self.latest_snapshot_date(fmt)
        if snap is None:
            return [], 0
        where = (MetaDeckRow.format == fmt, MetaDeckRow.snapshot_date == snap)
        with Session(self.engine, expire_on_commit=False) as s:
            total = s.execute(select(func.count(MetaDeckRow.id)).where(*where)).scalar() or 0
            rows = list(
                s.execute(
                    select(MetaDeckRow)
                    .where(*where)
                    .order_by(MetaDeckRow.rank, MetaDeckRow.id)
                    .limit(limit)
                    .offset(offset)
                ).scalars()
            )
        return rows, total

    def get_deck(self, deck_id: int) -> MetaDeckRow | None:
        with Session(self.engine, expire_on_commit=False) as s:
            return s.get(MetaDeckRow, deck_id)

    def get_deck_cards(self, deck_ids: list[int]) -> dict[int, list[MetaDeckCardRow]]:
        """Cards of several decks in a single ``IN`` query (no N+1 on Neon)."""
        result: dict[int, list[MetaDeckCardRow]] = {deck_id: [] for deck_id in deck_ids}
        if not deck_ids:
            return result
        with Session(self.engine, expire_on_commit=False) as s:
            rows = s.execute(
                select(MetaDeckCardRow)
                .where(MetaDeckCardRow.meta_deck_id.in_(deck_ids))
                .order_by(MetaDeckCardRow.meta_deck_id, MetaDeckCardRow.id)
            ).scalars()
            for row in rows:
                result[row.meta_deck_id].append(row)
        return result

    def list_formats(self) -> list[dict]:
        """``[{format, latest_snapshot_date, deck_count}]`` — count is for the latest snapshot."""
        with Session(self.engine) as s:
            latest = (
                select(
                    MetaDeckRow.format.label("fmt"),
                    func.max(MetaDeckRow.snapshot_date).label("snap"),
                )
                .group_by(MetaDeckRow.format)
                .subquery()
            )
            rows = s.execute(
                select(latest.c.fmt, latest.c.snap, func.count(MetaDeckRow.id))
                .join(
                    MetaDeckRow,
                    (MetaDeckRow.format == latest.c.fmt)
                    & (MetaDeckRow.snapshot_date == latest.c.snap),
                )
                .group_by(latest.c.fmt, latest.c.snap)
                .order_by(latest.c.fmt)
            ).all()
        return [
            {"format": fmt, "latest_snapshot_date": snap, "deck_count": count}
            for fmt, snap, count in rows
        ]

    # ── Card resolution / collection ────────────────────────────────────

    def resolve_card_id(
        self,
        name: str,
        set_code: str | None = None,
        collector_number: str | None = None,
    ) -> int | None:
        """Resolve a card name to ``cards.id``.

        Uses ``_find_card_id`` (exact set+number, then unique name). Fallbacks
        for double-faced/split cards: ``"A // B"`` → try face ``"A"``; plain
        ``"A"`` → unique ``name_en LIKE 'A // %'``.
        """
        with Session(self.engine) as s:
            card_id = _find_card_id(s, name, set_code, collector_number)
            if card_id is not None:
                return card_id
            if _SPLIT_SEP in name:
                front = name.split(_SPLIT_SEP, 1)[0].strip()
                return _find_card_id(s, front, None, None) if front else None
            ids = list(
                s.execute(
                    select(CardRow.id)
                    .where(
                        func.lower(CardRow.name_en).like(
                            _escape_like(name.lower()) + _SPLIT_SEP + "%", escape="\\"
                        )
                    )
                    .limit(2)
                ).scalars()
            )
            return ids[0] if len(ids) == 1 else None

    def owned_quantities(self, user_id: str, card_ids: list[int]) -> dict[int, int]:
        """``{card_id: total quantity}`` owned by ``user_id`` (single query)."""
        if not card_ids:
            return {}
        with Session(self.engine) as s:
            rows = s.execute(
                select(UserCollectionRow.card_id, func.sum(UserCollectionRow.quantity))
                .where(
                    UserCollectionRow.user_id == user_id,
                    UserCollectionRow.card_id.in_(set(card_ids)),
                )
                .group_by(UserCollectionRow.card_id)
            ).all()
        return {card_id: int(qty or 0) for card_id, qty in rows}
