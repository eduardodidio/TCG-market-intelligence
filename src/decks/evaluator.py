"""Pure deck evaluation service — no DB imports.

Receives pre-fetched card data and returns computed analysis results
(mana curve, color distribution, type distribution, legality check,
budget breakdown).
"""

from __future__ import annotations

import re
from collections import defaultdict
from decimal import Decimal

from src.domain.models import DeckEvaluation

# Regex to extract individual mana symbols from a mana_cost string like "{3}{U}{U}"
_MANA_SYMBOL_RE = re.compile(r"\{([^}]+)\}")

# Colors that count as 1 pip each
_COLOR_PIPS = {"W", "U", "B", "R", "G"}

# Known card supertypes in priority order
_TYPE_PRIORITY = [
    "Land",
    "Creature",
    "Planeswalker",
    "Instant",
    "Sorcery",
    "Enchantment",
    "Artifact",
]

# Singleton formats (max 1 copy of each non-basic-land card)
_SINGLETON_FORMATS = {"commander", "brawl", "duel", "oathbreaker"}

# Expected deck sizes per format
_FORMAT_DECK_SIZE: dict[str, int | None] = {
    "commander": 100,
    "brawl": 60,
    "oathbreaker": 60,
    "standard": 60,
    "modern": 60,
    "legacy": 60,
    "vintage": 60,
    "pioneer": 60,
    "pauper": 60,
}

# Basic land names (exempt from singleton rules)
_BASIC_LANDS = {
    "Plains",
    "Island",
    "Swamp",
    "Mountain",
    "Forest",
    "Wastes",
    "Snow-Covered Plains",
    "Snow-Covered Island",
    "Snow-Covered Swamp",
    "Snow-Covered Mountain",
    "Snow-Covered Forest",
}


def parse_cmc(mana_cost: str | None) -> int:
    """Parse a mana_cost string like ``{3}{U}{U}`` into converted mana cost.

    Rules:
    - ``{X}`` counts as 0
    - ``{N}`` (numeric) counts as N
    - Color pips ``{W}``, ``{U}``, ``{B}``, ``{R}``, ``{G}`` count as 1
    - Hybrid ``{W/U}`` counts as 1
    - Phyrexian ``{W/P}`` counts as 1
    - Split cards (``//``) use front face only
    - Returns 0 for None or empty string
    """
    if not mana_cost:
        return 0

    # For split/DFC cards, use front face only
    if " // " in mana_cost:
        mana_cost = mana_cost.split(" // ")[0]

    symbols = _MANA_SYMBOL_RE.findall(mana_cost)
    total = 0
    for sym in symbols:
        sym_upper = sym.upper()
        if sym_upper == "X":
            continue
        # Hybrid or phyrexian: {W/U}, {W/P}, {2/W}, etc.
        if "/" in sym_upper:
            parts = sym_upper.split("/")
            # If one part is numeric (e.g. {2/W}), use the higher cost
            numeric_parts = [int(p) for p in parts if p.isdigit()]
            if numeric_parts:
                total += max(numeric_parts)
            else:
                total += 1
            continue
        # Pure numeric
        if sym_upper.isdigit():
            total += int(sym_upper)
            continue
        # Color pip
        if sym_upper in _COLOR_PIPS or sym_upper == "C":
            total += 1
            continue
        # Unknown symbol — treat as 1
        total += 1

    return total


def _extract_color_pips(mana_cost: str | None) -> dict[str, int]:
    """Extract color pip counts from a mana cost string.

    Returns a dict mapping color letter to count of pips.
    Colorless mana symbols (numeric, {C}) are mapped to "C".
    """
    result: dict[str, int] = defaultdict(int)
    if not mana_cost:
        return dict(result)

    # For split/DFC cards, use front face only
    if " // " in mana_cost:
        mana_cost = mana_cost.split(" // ")[0]

    symbols = _MANA_SYMBOL_RE.findall(mana_cost)
    for sym in symbols:
        sym_upper = sym.upper()
        if sym_upper == "X":
            continue
        if "/" in sym_upper:
            # Hybrid: count each color pip present
            parts = sym_upper.split("/")
            for part in parts:
                if part in _COLOR_PIPS:
                    result[part] += 1
                    break  # Count hybrid as 1 pip of first color
            continue
        if sym_upper in _COLOR_PIPS:
            result[sym_upper] += 1
            continue
        if sym_upper.isdigit() or sym_upper == "C":
            result["C"] += 1

    return dict(result)


def classify_card_type(type_line: str | None) -> str:
    """Return the primary card type from a type_line string.

    Priority order: Land, Creature, Planeswalker, Instant, Sorcery,
    Enchantment, Artifact, Other.

    Handles double-faced cards (split on " // ") — uses front face.
    Handles subtypes separated by " -- " or " \u2014 ".
    """
    if not type_line:
        return "Other"

    # For double-faced / split cards, use front face
    if " // " in type_line:
        type_line = type_line.split(" // ")[0]

    # Strip subtypes (after em-dash or double-dash)
    for sep in (" \u2014 ", " -- "):
        if sep in type_line:
            type_line = type_line.split(sep)[0]

    # Check each type in priority order
    for card_type in _TYPE_PRIORITY:
        if card_type in type_line:
            return card_type

    return "Other"


def _is_land(type_line: str | None) -> bool:
    """Check if a card is a land based on its type_line."""
    return classify_card_type(type_line) == "Land"


def analyze_mana_curve(cards: list[dict]) -> dict[int, int]:
    """Build a histogram of CMC distribution. Lands are excluded.

    Keys are CMC values (0 through 7+), values are quantity-weighted counts.
    CMC >= 7 is bucketed into 7.
    """
    curve: dict[int, int] = defaultdict(int)
    for card in cards:
        if _is_land(card.get("type_line")):
            continue
        cmc = parse_cmc(card.get("mana_cost"))
        bucket = min(cmc, 7)
        qty = card.get("quantity", 1)
        curve[bucket] += qty
    return dict(curve)


def analyze_color_distribution(cards: list[dict]) -> dict[str, int]:
    """Count color pips across all non-land cards.

    Returns dict mapping color letter (W, U, B, R, G, C) to pip count.
    """
    dist: dict[str, int] = defaultdict(int)
    for card in cards:
        if _is_land(card.get("type_line")):
            continue
        pips = _extract_color_pips(card.get("mana_cost"))
        qty = card.get("quantity", 1)
        for color, count in pips.items():
            dist[color] += count * qty
    return dict(dist)


def analyze_type_distribution(cards: list[dict]) -> dict[str, int]:
    """Count cards by primary type (quantity-weighted)."""
    dist: dict[str, int] = defaultdict(int)
    for card in cards:
        card_type = classify_card_type(card.get("type_line"))
        qty = card.get("quantity", 1)
        dist[card_type] += qty
    return dict(dist)


def _check_legality(
    cards: list[dict],
    legalities: dict[int, list[dict]],
    format_name: str,
) -> dict:
    """Check format legality for all cards in a deck.

    Args:
        cards: list of card dicts with card_id, name_en, quantity
        legalities: dict mapping card_id -> list of {format, status} dicts
        format_name: target format to check

    Returns dict with format, is_legal, illegal_cards,
    singleton_violations, card_count_valid.
    """
    illegal_cards: list[dict] = []
    singleton_violations: list[str] = []
    is_singleton = format_name.lower() in _SINGLETON_FORMATS

    # Track card name counts for singleton check
    name_counts: dict[str, int] = defaultdict(int)

    for card in cards:
        card_id = card.get("card_id")
        name = card.get("name_en", "Unknown")
        qty = card.get("quantity", 1)

        # Singleton check (except basic lands)
        if is_singleton and name not in _BASIC_LANDS:
            name_counts[name] += qty

        # Legality check
        if card_id is None:
            # Card not linked — cannot verify legality
            continue

        card_legs = legalities.get(card_id, [])
        format_entry = None
        for leg in card_legs:
            if leg.get("format", "").lower() == format_name.lower():
                format_entry = leg
                break

        if format_entry is None:
            # No legality data for this format — treat as not_legal
            illegal_cards.append({"name_en": name, "status": "not_legal"})
        elif format_entry.get("status") != "legal":
            illegal_cards.append(
                {
                    "name_en": name,
                    "status": format_entry.get("status", "not_legal"),
                }
            )

    # Collect singleton violations
    for name, count in name_counts.items():
        if count > 1:
            singleton_violations.append(name)

    # Card count validation
    total_cards = sum(c.get("quantity", 1) for c in cards)
    expected_size = _FORMAT_DECK_SIZE.get(format_name.lower())
    card_count_valid = True
    if expected_size is not None:
        card_count_valid = total_cards >= expected_size

    is_legal = len(illegal_cards) == 0 and len(singleton_violations) == 0

    return {
        "format": format_name,
        "is_legal": is_legal,
        "illegal_cards": illegal_cards,
        "singleton_violations": singleton_violations,
        "card_count_valid": card_count_valid,
    }


def _analyze_budget(
    cards: list[dict],
    prices: dict[int, Decimal],
) -> dict:
    """Analyze deck budget from card prices.

    Args:
        cards: list of card dicts with card_id, name_en, quantity
        prices: dict mapping card_id -> price (Decimal)

    Returns dict with total_value, most_expensive (top 5),
    and price_tiers.
    """
    total_value = Decimal("0")
    card_costs: list[dict] = []
    tiers = {"budget": 0, "mid": 0, "premium": 0, "chase": 0}

    for card in cards:
        card_id = card.get("card_id")
        if card_id is None:
            continue
        price = prices.get(card_id)
        if price is None:
            continue

        name = card.get("name_en", "Unknown")
        qty = card.get("quantity", 1)
        total_value += price * qty
        card_costs.append(
            {
                "name_en": name,
                "price": price,
                "quantity": qty,
            }
        )

        # Classify price tier (per-card, not per-quantity)
        for _ in range(qty):
            if price < 5:
                tiers["budget"] += 1
            elif price < 20:
                tiers["mid"] += 1
            elif price < 50:
                tiers["premium"] += 1
            else:
                tiers["chase"] += 1

    # Sort by unit price descending, take top 5
    card_costs.sort(key=lambda c: c["price"], reverse=True)
    most_expensive = card_costs[:5]

    return {
        "total_value": total_value,
        "most_expensive": most_expensive,
        "price_tiers": tiers,
    }


def evaluate_deck(
    cards: list[dict],
    prices: dict[int, Decimal] | None = None,
    legalities: dict[int, list[dict]] | None = None,
    format_name: str | None = None,
    archetype: str | None = None,
) -> DeckEvaluation:
    """Evaluate a deck and return a comprehensive analysis.

    Args:
        cards: list of card dicts, each with keys: card_id, quantity,
            name_en, mana_cost, type_line, color_identity, rarity
        prices: optional dict mapping card_id -> Decimal price
        legalities: optional dict mapping card_id -> list of
            {format, status} dicts
        format_name: optional target format for legality check
        archetype: optional archetype for suggestion template matching

    Returns a DeckEvaluation dataclass.
    """
    mana_curve = analyze_mana_curve(cards)
    color_dist = analyze_color_distribution(cards)
    type_dist = analyze_type_distribution(cards)

    # Count lands and non-lands (quantity-weighted)
    land_count = 0
    nonland_count = 0
    total_cards = 0
    for card in cards:
        qty = card.get("quantity", 1)
        total_cards += qty
        if _is_land(card.get("type_line")):
            land_count += qty
        else:
            nonland_count += qty

    # Average CMC (non-land cards, quantity-weighted)
    cmc_sum = 0
    cmc_count = 0
    for card in cards:
        if _is_land(card.get("type_line")):
            continue
        cmc = parse_cmc(card.get("mana_cost"))
        qty = card.get("quantity", 1)
        cmc_sum += cmc * qty
        cmc_count += qty

    avg_cmc = round(cmc_sum / cmc_count, 2) if cmc_count > 0 else 0.0

    # Collect color identity (union of all cards' color_identity)
    identity: set[str] = set()
    for card in cards:
        ci = card.get("color_identity") or ""
        for char in ci:
            if char in _COLOR_PIPS or char == "C":
                identity.add(char)

    # Legality check
    legality_check = None
    if format_name and legalities is not None:
        legality_check = _check_legality(cards, legalities, format_name)

    # Budget analysis
    budget = None
    if prices:
        budget = _analyze_budget(cards, prices)

    evaluation = DeckEvaluation(
        mana_curve=mana_curve,
        color_distribution=color_dist,
        type_distribution=type_dist,
        land_count=land_count,
        nonland_count=nonland_count,
        total_cards=total_cards,
        avg_cmc=avg_cmc,
        color_identity=identity,
        legality_check=legality_check,
        budget=budget,
    )

    # Generate suggestions based on evaluation and archetype template
    from src.decks.suggestions import generate_suggestions

    evaluation.suggestions = generate_suggestions(
        evaluation,
        archetype=archetype,
        format_name=format_name,
    )

    return evaluation
