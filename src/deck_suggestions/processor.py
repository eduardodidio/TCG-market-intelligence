"""Deck-suggestion processor (F172).

Orchestrates the daily routine: claim pending requests, build the prompt
from the user's collection, call the Claude runner, parse the reply, resolve
card names against the catalog, enrich with owned quantities and BRL prices,
and persist ``done`` / ``failed`` / retry.

Collection rows without a ``card_id`` (not canonized) are still owned by
name, so they always count toward ``owned_quantity``. Their color identity
is unknown, though, so they are only listed in the prompt when the request
has 3+ colors (where an off-color card is least likely); otherwise they are
dropped from the prompt.

The prompt text is never logged (it contains the user's collection).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import Engine, func, or_, select
from sqlalchemy.orm import Session

from src.database.models import CardRow, UserCollectionRow
from src.database.repository import Repository
from src.deck_suggestions import repository as queue
from src.deck_suggestions.claude_runner import ClaudeRunner, ClaudeRunnerError
from src.deck_suggestions.models import DeckSuggestionRequestRow
from src.deck_suggestions.prompt import (
    OwnedCard,
    ParsedSuggestion,
    SuggestionInput,
    SuggestionParseError,
    build_prompt,
    expected_deck_size,
    filter_owned_for_request,
    is_basic_land,
    parse_response,
)

log = structlog.get_logger()

MAX_ATTEMPTS = 3
RESOLVE_CHUNK = 200
MAX_UNEXPECTED_ERROR_CHARS = 500
MIN_COLORS_FOR_UNLINKED = 3
_DFC_SEPARATOR = " // "


@dataclass
class ProcessSummary:
    total: int = 0
    done: int = 0
    failed: int = 0
    retried: int = 0


@dataclass
class OwnedCollection:
    """The user's collection, split by whether rows are linked to the catalog."""

    linked: list[OwnedCard] = field(default_factory=list)
    unlinked: list[OwnedCard] = field(default_factory=list)
    card_ids: set[int] = field(default_factory=set)

    @property
    def all_cards(self) -> list[OwnedCard]:
        return self.linked + self.unlinked

    def quantities_by_name(self) -> dict[str, int]:
        """Owned quantity keyed by lowercase EN name (and PT name when different)."""
        totals: dict[str, int] = {}
        for card in self.all_cards:
            keys = {card.name_en.strip().lower()}
            if card.name_pt:
                keys.add(card.name_pt.strip().lower())
            for key in keys:
                totals[key] = totals.get(key, 0) + card.quantity
        return totals

    def for_prompt(self, colors: list[str]) -> list[OwnedCard]:
        """Owned cards to list in the prompt (see module docstring for unlinked rows)."""
        real_colors = [c for c in colors if c.upper() in "WUBRG"]
        pool = list(self.linked)
        if len(real_colors) >= MIN_COLORS_FOR_UNLINKED:
            pool += self.unlinked
        return filter_owned_for_request(pool, colors)


def _to_price(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)


def _prices_for(repo: Repository, card_ids: set[int] | list[int]) -> dict[int, float | None]:
    ids = sorted(set(card_ids))
    if not ids:
        return {}
    batch = repo.get_latest_prices_batch(ids)
    return {
        cid: _to_price(obs.median_price) if obs is not None else None
        for cid, obs in batch.items()
    }


def load_owned_cards(repo: Repository, user_id: str) -> OwnedCollection:
    """Load the user's collection joined with the catalog, priced in BRL."""
    with Session(repo.engine) as session:
        rows = session.execute(
            select(
                UserCollectionRow.card_id,
                UserCollectionRow.name_en,
                UserCollectionRow.name_pt,
                UserCollectionRow.quantity,
                CardRow.name_en,
                CardRow.name_pt,
                CardRow.color_identity,
                CardRow.type_line,
            )
            .outerjoin(CardRow, CardRow.id == UserCollectionRow.card_id)
            .where(UserCollectionRow.user_id == user_id)
        ).all()

    linked_ids = {r[0] for r in rows if r[0] is not None and r[4] is not None}
    prices = _prices_for(repo, linked_ids)

    collection = OwnedCollection(card_ids=linked_ids)
    for card_id, coll_en, coll_pt, qty, card_en, card_pt, identity, type_line in rows:
        name_en = card_en or coll_en
        if not name_en or not qty or qty <= 0:
            continue
        linked = card_id is not None and card_en is not None
        card = OwnedCard(
            name_en=name_en,
            name_pt=card_pt or coll_pt,
            quantity=int(qty),
            color_identity=(identity or "") if linked else None,
            type_line=type_line if linked else None,
            unit_price=prices.get(card_id) if linked else None,
        )
        (collection.linked if linked else collection.unlinked).append(card)
    return collection


def _card_info(row: CardRow) -> dict:
    return {
        "card_id": row.id,
        "name_en": row.name_en,
        "set_code": row.set_code,
        "collector_number": row.collector_number,
        "image_uri": row.image_uri,
    }


def _pick_printing(rows: list[CardRow], owned_card_ids: set[int]) -> CardRow:
    """Owned printing first, then one with an image, then the newest id."""
    return max(rows, key=lambda r: (r.id in owned_card_ids, r.image_uri is not None, r.id))


def _chunks(items: list[str], size: int = RESOLVE_CHUNK):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _match_exact(session: Session, column, keys: list[str]) -> dict[str, list[CardRow]]:
    found: dict[str, list[CardRow]] = {}
    for chunk in _chunks(keys):
        rows = session.execute(
            select(CardRow).where(CardRow.game == "magic", func.lower(column).in_(chunk))
        ).scalars().all()
        for row in rows:
            value = getattr(row, column.key)
            if value:
                found.setdefault(value.lower(), []).append(row)
    return found


def _match_front_face(session: Session, keys: list[str]) -> dict[str, list[CardRow]]:
    found: dict[str, list[CardRow]] = {}
    for chunk in _chunks(keys):
        patterns = [
            func.lower(CardRow.name_en).like(f"{_escape_like(k)}{_DFC_SEPARATOR}%", escape="\\")
            for k in chunk
        ]
        rows = session.execute(
            select(CardRow).where(CardRow.game == "magic", or_(*patterns))
        ).scalars().all()
        for row in rows:
            front = row.name_en.split(_DFC_SEPARATOR)[0].strip().lower()
            if front in chunk:
                found.setdefault(front, []).append(row)
    return found


def resolve_cards(
    engine: Engine, names: list[str], owned_card_ids: set[int] | None = None
) -> dict[str, dict]:
    """Resolve card names to catalog printings, keyed by ``name.lower()``.

    Order: exact ``name_en`` → exact ``name_pt`` → DFC front face (a
    ``"Front // Back"`` catalog name, or the front half of a name Claude sent
    as ``"Front // Back"``). Among printings, an owned ``card_id`` wins.
    Unresolved names are absent from the result.
    """
    owned_ids = owned_card_ids or set()
    pending = sorted({n.strip().lower() for n in names if n and n.strip()})
    resolved: dict[str, dict] = {}
    if not pending:
        return resolved

    with Session(engine) as session:
        for column in (CardRow.name_en, CardRow.name_pt):
            matches = _match_exact(session, column, pending)
            for key, rows in matches.items():
                if key in pending and key not in resolved:
                    resolved[key] = _card_info(_pick_printing(rows, owned_ids))
            pending = [k for k in pending if k not in resolved]
            if not pending:
                return resolved

        # Front-face lookup: "delver of secrets" → "Delver of Secrets // Insectile Aberration",
        # and "a // b" sent by Claude → catalog row named just "A".
        front_of = {k: k.split(_DFC_SEPARATOR)[0].strip() for k in pending}
        like_matches = _match_front_face(session, pending)
        exact_fronts = _match_exact(
            session, CardRow.name_en, sorted({f for k, f in front_of.items() if f != k})
        )
        for key in pending:
            rows = like_matches.get(key) or exact_fronts.get(front_of[key])
            if rows:
                resolved[key] = _card_info(_pick_printing(rows, owned_ids))
    return resolved


def _cost(unit_price: float | None, missing: int) -> float | None:
    return None if unit_price is None else round(unit_price * missing, 2)


def _entry(
    name: str,
    quantity: int,
    info: dict | None,
    owned_qty: dict[str, int],
    prices: dict[int, float | None],
) -> dict:
    """Common owned/missing/price fields for a suggested card (or commander)."""
    name_en = info["name_en"] if info else name
    card_id = info["card_id"] if info else None
    if is_basic_land(name_en):
        owned, missing, unit_price = quantity, 0, 0.0
    else:
        owned = owned_qty.get(name_en.lower(), 0) or owned_qty.get(name.lower(), 0)
        missing = max(0, quantity - owned)
        unit_price = prices.get(card_id) if card_id is not None else None
    return {
        "name_en": name_en,
        "quantity": quantity,
        "card_id": card_id,
        "set_code": info["set_code"] if info else None,
        "collector_number": info["collector_number"] if info else None,
        "image_uri": info["image_uri"] if info else None,
        "is_owned": missing == 0,
        "owned_quantity": owned,
        "missing_quantity": missing,
        "unit_price": unit_price,
        "missing_cost": 0.0 if missing == 0 else _cost(unit_price, missing),
    }


def enrich(
    parsed: ParsedSuggestion,
    request: DeckSuggestionRequestRow,
    owned_qty: dict[str, int],
    resolved: dict[str, dict],
    prices: dict[int, float | None],
    *,
    provider: str = "",
    model: str = "",
    commander_info: dict | None = None,
) -> dict:
    """Build the ``SuggestionResult`` dict (pure: no DB, no network).

    ``owned_qty`` maps lowercase names to owned quantities, ``resolved`` maps
    lowercase suggested names to catalog info (see ``resolve_cards``) and
    ``prices`` maps ``card_id`` to the BRL unit price.
    """
    fmt = request.format_name.strip().lower()
    warnings = list(parsed.warnings)
    commander_name = (request.commander_name or "").strip()

    commander: dict | None = None
    if commander_name:
        info = commander_info or resolved.get(commander_name.lower())
        commander = _entry(commander_name, 1, info, owned_qty, prices)
        if info is None and request.commander_card_id is not None:
            commander["card_id"] = request.commander_card_id

    cards: list[dict] = []
    unresolved: list[str] = []
    for card in parsed.cards:
        if commander_name and card.name.lower() == commander_name.lower():
            warnings.append(f"Comandante {commander_name} removido da lista de cartas")
            continue
        info = resolved.get(card.name.lower())
        if info is None and not is_basic_land(card.name):
            unresolved.append(card.name)
        entry = _entry(card.name, card.quantity, info, owned_qty, prices)
        entry["category"] = card.category
        entry["reason"] = card.reason
        cards.append(entry)

    counted = cards + ([commander] if commander else [])
    total_cards = sum(c["quantity"] for c in counted)
    missing_cards = sum(c["missing_quantity"] for c in counted)
    priced = [
        c["missing_cost"]
        for c in counted
        if c["missing_cost"] is not None and not is_basic_land(c["name_en"])
    ]
    missing_cost_brl = round(sum(priced), 2) if priced else None

    if unresolved:
        warnings.append(f"{len(unresolved)} carta(s) não encontradas no catálogo")
    if missing_cost_brl is None and missing_cards > 0:
        warnings.append("Nenhum preço disponível para as cartas faltantes")
    expected = expected_deck_size(fmt)
    if total_cards != expected:
        warnings.append(f"Deck com {total_cards} cartas (esperado: {expected})")

    return {
        "deck_name": parsed.deck_name,
        "strategy": parsed.strategy,
        "format_name": fmt,
        "commander": commander,
        "cards": cards,
        "summary": {
            "total_cards": total_cards,
            "owned_cards": total_cards - missing_cards,
            "missing_cards": missing_cards,
            "missing_cost_brl": missing_cost_brl,
            "unresolved_count": len(unresolved),
        },
        "unresolved": unresolved,
        "warnings": warnings,
        "provider": provider,
        "model": model,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
    }


def _commander_info(engine: Engine, card_id: int | None) -> dict | None:
    if card_id is None:
        return None
    with Session(engine) as session:
        row = session.get(CardRow, card_id)
        return _card_info(row) if row is not None else None


def _process_one(repo: Repository, runner: ClaudeRunner, row: DeckSuggestionRequestRow) -> dict:
    engine = repo.engine
    colors = queue.colors_from_str(row.colors)
    collection = load_owned_cards(repo, row.user_id)
    prompt = build_prompt(
        SuggestionInput(
            format_name=row.format_name,
            commander_name=row.commander_name,
            colors=colors,
            archetype=row.archetype,
            notes=row.notes,
        ),
        collection.for_prompt(colors),
    )
    text = runner.run(prompt)
    parsed = parse_response(text, row.format_name)

    commander_info = _commander_info(engine, row.commander_card_id)
    names = [c.name for c in parsed.cards]
    if row.commander_name and commander_info is None:
        names.append(row.commander_name)
    resolved = resolve_cards(engine, names, collection.card_ids)

    card_ids = {info["card_id"] for info in resolved.values()}
    if commander_info:
        card_ids.add(commander_info["card_id"])
    return enrich(
        parsed,
        row,
        collection.quantities_by_name(),
        resolved,
        _prices_for(repo, card_ids),
        provider=getattr(runner, "provider", ""),
        model=getattr(runner, "model", ""),
        commander_info=commander_info,
    )


def _count_claimable(engine: Engine) -> int:
    queue.ensure_table(engine)
    with Session(engine) as session:
        return int(
            session.execute(
                select(func.count(DeckSuggestionRequestRow.id)).where(
                    DeckSuggestionRequestRow.status == "pending"
                )
            ).scalar_one()
        )


def process_pending_suggestions(
    repo: Repository, runner: ClaudeRunner, *, limit: int = 5, dry_run: bool = False
) -> ProcessSummary:
    """Process up to ``limit`` pending requests. One failure never aborts the batch.

    ``dry_run`` only counts pending requests (capped at ``limit``); nothing is
    claimed, called or written.
    """
    summary = ProcessSummary()
    if dry_run:
        summary.total = min(_count_claimable(repo.engine), max(limit, 0))
        return summary

    for row in queue.claim_pending(repo.engine, limit):
        summary.total += 1
        try:
            result = _process_one(repo, runner, row)
            queue.mark_done(repo.engine, row.id, result)
        except ClaudeRunnerError as exc:
            if exc.transient and row.attempts < MAX_ATTEMPTS:
                queue.release_for_retry(repo.engine, row.id, exc.message)
                summary.retried += 1
                log.warning(
                    "deck_suggestion_retry", request_id=row.id, attempts=row.attempts
                )
            else:
                queue.mark_failed(repo.engine, row.id, exc.message)
                summary.failed += 1
                log.warning(
                    "deck_suggestion_failed",
                    request_id=row.id,
                    attempts=row.attempts,
                    reason="runner",
                    transient=exc.transient,
                )
            continue
        except SuggestionParseError as exc:
            queue.mark_failed(repo.engine, row.id, f"Resposta inválida do Claude: {exc}")
            summary.failed += 1
            log.warning("deck_suggestion_failed", request_id=row.id, reason="parse")
            continue
        except Exception as exc:  # noqa: BLE001 — isolate each request
            log.exception("deck_suggestion_failed", request_id=row.id, reason="unexpected")
            queue.mark_failed(
                repo.engine, row.id, (str(exc) or type(exc).__name__)[:MAX_UNEXPECTED_ERROR_CHARS]
            )
            summary.failed += 1
            continue

        summary.done += 1
        log.info(
            "deck_suggestion_done",
            request_id=row.id,
            cards=result["summary"]["total_cards"],
            missing=result["summary"]["missing_cards"],
            unresolved=result["summary"]["unresolved_count"],
        )
    return summary
