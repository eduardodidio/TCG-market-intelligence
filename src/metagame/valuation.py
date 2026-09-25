"""Pure valuation of metagame decks in BRL — no DB imports."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_BASIC_NAMES = ("Plains", "Island", "Swamp", "Mountain", "Forest", "Wastes")
BASIC_LANDS: frozenset[str] = frozenset(
    {*_BASIC_NAMES} | {f"Snow-Covered {name}" for name in _BASIC_NAMES}
)

MAIN_BOARDS: frozenset[str] = frozenset({"main", "commander"})
SIDEBOARDS: frozenset[str] = frozenset({"side", "sideboard"})

_BRL_STEP = Decimal("0.01")
_PCT_STEP = Decimal("0.1")
_HUNDRED = Decimal("100")


@dataclass(frozen=True)
class MetaDeckValuation:
    total_value_brl: Decimal | None
    priced_pct: Decimal
    owned_pct: Decimal | None
    missing_value_brl: Decimal | None
    total_copies: int


def _pct(part: int, total: int) -> Decimal:
    if total == 0:
        return Decimal("0").quantize(_PCT_STEP)
    return (Decimal(part) * _HUNDRED / Decimal(total)).quantize(_PCT_STEP, ROUND_HALF_UP)


def _is_basic_land(card: object) -> bool:
    name = getattr(card, "card_name", None) or getattr(card, "name", None)
    return isinstance(name, str) and name.strip() in BASIC_LANDS


def value_meta_deck(
    cards: Iterable,
    prices: dict[int, Decimal | None],
    owned: dict[int, int] | None,
    include_sideboard: bool = False,
) -> MetaDeckValuation:
    """Value a metagame deck in BRL and measure how much of it the user owns.

    ``cards`` items expose ``card_id``, ``quantity``, ``board`` (default "main")
    and ``card_name`` (or ``name``). Basic lands count as priced at R$0 and owned.
    ``owned=None`` means an anonymous user: ``owned_pct``/``missing_value_brl`` are None.
    """
    boards = MAIN_BOARDS | SIDEBOARDS if include_sideboard else MAIN_BOARDS

    total = Decimal("0")
    missing = Decimal("0")
    total_copies = 0
    nonbasic_copies = 0
    priced_copies = 0
    owned_copies = 0
    has_nonbasic_price = False

    for card in cards:
        board = (getattr(card, "board", None) or "main").lower()
        if board not in boards:
            continue
        qty = getattr(card, "quantity", 1)
        if qty is None or qty <= 0:
            continue
        total_copies += qty

        if _is_basic_land(card):
            priced_copies += qty
            owned_copies += qty
            continue

        nonbasic_copies += qty
        card_id = getattr(card, "card_id", None)
        if card_id is None:
            continue

        have = min(qty, max(owned.get(card_id, 0), 0)) if owned is not None else 0
        owned_copies += have

        price = prices.get(card_id)
        if price is None:
            continue
        has_nonbasic_price = True
        priced_copies += qty
        total += price * qty
        missing += price * (qty - have)

    # A deck made only of basics is fully priced at R$0.
    has_value = has_nonbasic_price or (total_copies > 0 and nonbasic_copies == 0)

    return MetaDeckValuation(
        total_value_brl=total.quantize(_BRL_STEP, ROUND_HALF_UP) if has_value else None,
        priced_pct=_pct(priced_copies, total_copies),
        owned_pct=_pct(owned_copies, total_copies) if owned is not None else None,
        missing_value_brl=(
            missing.quantize(_BRL_STEP, ROUND_HALF_UP)
            if owned is not None and has_value
            else None
        ),
        total_copies=total_copies,
    )
