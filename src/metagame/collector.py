"""Metagame collection service (F173-T09).

Composes already-built :class:`MetaSource` adapters with
:class:`MetagameRepository`: for each requested format it fetches the top
decks, resolves every card name to ``cards.id`` and stores a dated snapshot.
Concrete adapters are never imported here — callers pass the
``format → source`` map (see ``src.metagame.sources.get_sources``).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

import structlog

from src.metagame.repository import MetagameRepository
from src.metagame.sources.base import MetaCardEntry, MetaSource

log = structlog.get_logger()

CardResolver = Callable[[MetaCardEntry], "int | None"]


@dataclass
class CollectStats:
    formats: int = 0
    decks: int = 0
    cards: int = 0
    unresolved_cards: int = 0
    errors: list[str] = field(default_factory=list)


def _cached_resolver(repo: MetagameRepository, resolver: CardResolver | None) -> CardResolver:
    """Wrap ``resolver`` (default ``repo.resolve_card_id``) in a per-collection cache."""
    cache: dict[tuple[str, str | None, str | None], int | None] = {}

    def resolve(card: MetaCardEntry) -> int | None:
        key = (card.name.lower(), card.set_code, card.collector_number)
        if key not in cache:
            if resolver is not None:
                cache[key] = resolver(card)
            else:
                cache[key] = repo.resolve_card_id(card.name, card.set_code, card.collector_number)
        return cache[key]

    return resolve


def collect_metagame(
    repo: MetagameRepository,
    sources: Mapping[str, MetaSource],
    formats: Sequence[str],
    *,
    limit: int = 20,
    snapshot_date: date | None = None,
    dry_run: bool = False,
    resolver: CardResolver | None = None,
) -> CollectStats:
    """Collect and store the top ``limit`` decks of each format.

    A failing format is logged and recorded in ``stats.errors``; the others
    still run. ``dry_run`` fetches and resolves but writes nothing. Running
    twice on the same day replaces that ``(format, source, day)`` snapshot.
    """
    stats = CollectStats()
    snap = snapshot_date or date.today()
    resolve = _cached_resolver(repo, resolver)

    for fmt in dict.fromkeys(formats):
        source = sources.get(fmt)
        if source is None:
            stats.errors.append(f"no source for {fmt}")
            log.error("metagame.collect.no_source", format=fmt)
            continue
        try:
            decks = source.fetch_top_decks(fmt, limit=limit)[:limit]
            # Resolve before replace_snapshot opens its write transaction.
            card_ids: dict[tuple[str, str], int | None] = {}
            n_cards = n_unresolved = 0
            for deck in decks:
                for card in deck.cards:
                    card_id = resolve(card)
                    card_ids[(deck.external_id, card.name)] = card_id
                    n_cards += 1
                    n_unresolved += card_id is None
            if not dry_run:
                repo.replace_snapshot(fmt, source.name, snap, decks, card_ids)
        except Exception as e:  # noqa: BLE001 — one format must not abort the rest
            stats.errors.append(f"{fmt}: {e}")
            log.error(
                "metagame.collect.format_failed",
                format=fmt,
                source=getattr(source, "name", None),
                error=str(e),
            )
            continue

        stats.formats += 1
        stats.decks += len(decks)
        stats.cards += n_cards
        stats.unresolved_cards += n_unresolved
        log.info(
            "metagame.collect.format_done",
            format=fmt,
            source=source.name,
            decks=len(decks),
            cards=n_cards,
            unresolved=n_unresolved,
            dry_run=dry_run,
        )

    return stats
