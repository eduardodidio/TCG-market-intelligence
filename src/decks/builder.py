"""Deck builder service — generates decks from the card catalog.

Uses Repository for catalog queries. The builder is format-aware
(commander = 100 cards singleton, standard/modern = 60 cards with
4-of limit) and uses heuristic rules for card selection.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import case, select
from sqlalchemy.orm import Session

from src.database.models import CardLegalityRow, CardRow, UserCollectionRow
from src.domain.models import DeckBuildParams, GeneratedDeck

# Basic land names (exempt from singleton and always available)
_BASIC_LANDS = {
    "Plains": "W",
    "Island": "U",
    "Swamp": "B",
    "Mountain": "R",
    "Forest": "G",
}

# Commander staples to auto-include when possible
_COMMANDER_STAPLES = ["Command Tower", "Sol Ring", "Arcane Signet"]

# Singleton formats
_SINGLETON_FORMATS = {"commander", "brawl", "duel", "oathbreaker"}

# Card types to query for deck composition
_CARD_TYPES = [
    "Creature",
    "Instant",
    "Sorcery",
    "Enchantment",
    "Artifact",
    "Planeswalker",
]

# Archetype composition templates for 100-card commander decks
# (Lands are handled separately — these sum to non-land slots)
_ARCHETYPE_TEMPLATES_100: dict[str | None, dict[str, int]] = {
    "aggro": {
        "Land": 36,
        "Creature": 30,
        "Instant": 8,
        "Sorcery": 6,
        "Enchantment": 4,
        "Artifact": 10,
        "Planeswalker": 0,
    },
    "control": {
        "Land": 38,
        "Creature": 10,
        "Instant": 14,
        "Sorcery": 8,
        "Enchantment": 8,
        "Artifact": 10,
        "Planeswalker": 4,
    },
    "midrange": {
        "Land": 37,
        "Creature": 24,
        "Instant": 8,
        "Sorcery": 8,
        "Enchantment": 6,
        "Artifact": 10,
        "Planeswalker": 2,
    },
    "combo": {
        "Land": 36,
        "Creature": 16,
        "Instant": 10,
        "Sorcery": 12,
        "Enchantment": 8,
        "Artifact": 12,
        "Planeswalker": 0,
    },
    "tempo": {
        "Land": 36,
        "Creature": 22,
        "Instant": 14,
        "Sorcery": 6,
        "Enchantment": 4,
        "Artifact": 10,
        "Planeswalker": 2,
    },
    None: {
        "Land": 37,
        "Creature": 24,
        "Instant": 8,
        "Sorcery": 6,
        "Enchantment": 6,
        "Artifact": 10,
        "Planeswalker": 2,
    },
}


def _get_target_composition(
    format_name: str,
    archetype: str | None,
) -> dict[str, int]:
    """Return target card type counts for a given format and archetype.

    Commander (100 cards) uses the template directly.
    Other formats (60 cards) scale proportionally.
    """
    key = archetype.lower() if archetype else None
    template = _ARCHETYPE_TEMPLATES_100.get(key, _ARCHETYPE_TEMPLATES_100[None])

    if format_name.lower() in _SINGLETON_FORMATS:
        # Commander-like: use the 100-card template directly
        # Verify sum = 100 (should be by design)
        total = sum(template.values())
        # If template doesn't sum to target, adjust lands
        if total != 100:
            result = dict(template)
            result["Land"] += 100 - total
            return result
        return dict(template)

    # 60-card formats: scale from 100
    scale = 60 / 100
    scaled: dict[str, int] = {}
    running_total = 0

    for card_type in _CARD_TYPES:
        count = round(template.get(card_type, 0) * scale)
        scaled[card_type] = count
        running_total += count

    # Lands fill the remainder to reach 60
    scaled["Land"] = 60 - running_total

    return scaled


def _color_identity_matches(card_ci: str | None, allowed_colors: set[str]) -> bool:
    """Check if a card's color_identity is a subset of allowed colors.

    A colorless card (empty or "C") is always allowed.
    """
    if not card_ci or card_ci == "C":
        return True
    for char in card_ci:
        if char not in allowed_colors and char != "C":
            return False
    return True


def _query_candidates(
    session: Session,
    colors: set[str],
    format_name: str | None,
    card_type: str,
    limit: int = 200,
    exclude_ids: set[int] | None = None,
) -> list[CardRow]:
    """Query catalog cards matching color identity, format legality, and type.

    Returns CardRow objects ordered by rarity (mythic/rare first).
    """
    stmt = select(CardRow).where(
        CardRow.game == "magic",
        CardRow.type_line.isnot(None),
    )

    # Type filter: match cards whose type_line contains the target type
    stmt = stmt.where(CardRow.type_line.contains(card_type))

    # Exclude basic lands from non-land queries
    if card_type != "Land":
        for land_name in _BASIC_LANDS:
            stmt = stmt.where(CardRow.name_en != land_name)

    # Exclude specific IDs
    if exclude_ids:
        stmt = stmt.where(CardRow.id.notin_(exclude_ids))

    # Format legality: join with card_legalities
    if format_name:
        stmt = stmt.where(
            CardRow.id.in_(
                select(CardLegalityRow.card_id).where(
                    CardLegalityRow.format == format_name.lower(),
                    CardLegalityRow.status == "legal",
                )
            )
        )

    # Order by rarity (mythic > rare > uncommon > common)
    rarity_order = case(
        (CardRow.rarity == "mythic", 1),
        (CardRow.rarity == "rare", 2),
        (CardRow.rarity == "uncommon", 3),
        (CardRow.rarity == "common", 4),
        else_=5,
    )
    stmt = stmt.order_by(rarity_order, CardRow.name_en).limit(limit)

    rows = session.execute(stmt).scalars().all()

    # Post-filter by color identity (safer than SQL for parsed strings)
    return [r for r in rows if _color_identity_matches(r.color_identity, colors)]


def _select_cards(
    candidates: list[CardRow],
    target_count: int,
    singleton: bool,
    budget_remaining: Decimal | None,
    prices: dict[int, Decimal],
    owned_ids: set[int],
    prioritize_owned: bool,
) -> list[dict]:
    """Pick cards from candidates up to target_count.

    If singleton, pick 1 of each. If not, pick up to 4 of each.
    Owned cards are sorted first when prioritize_owned is True.
    Budget is respected when budget_remaining is provided.
    """
    if prioritize_owned:
        # Sort: owned first, then by price ascending
        candidates = sorted(
            candidates,
            key=lambda c: (
                0 if c.id in owned_ids else 1,
                prices.get(c.id, Decimal("999999")),
            ),
        )

    selected: list[dict] = []
    seen_names: set[str] = set()
    count = 0

    for card in candidates:
        if count >= target_count:
            break

        name = card.name_en
        if singleton and name in seen_names:
            continue

        # Budget check
        card_price = prices.get(card.id, Decimal("0"))
        if budget_remaining is not None and card_price > 0:
            if card_price > budget_remaining:
                continue

        copies = 1 if singleton else min(4, target_count - count)

        selected.append(
            {
                "card_id": card.id,
                "name_en": card.name_en,
                "set_code": card.set_code,
                "collector_number": card.collector_number,
                "quantity": copies,
                "mana_cost": card.mana_cost,
                "type_line": card.type_line,
                "rarity": card.rarity,
                "image_uri": card.image_uri,
                "price": float(card_price) if card_price else None,
                "is_owned": card.id in owned_ids,
            }
        )

        if budget_remaining is not None and card_price > 0:
            budget_remaining -= card_price * copies

        seen_names.add(name)
        count += copies

    return selected


def _add_basic_lands(
    colors: set[str],
    land_count: int,
    existing_land_count: int,
) -> list[dict]:
    """Add basic lands proportional to color distribution.

    Returns list of card dicts for basic lands.
    """
    needed = max(0, land_count - existing_land_count)
    if needed == 0 or not colors:
        return []

    # Filter to colors that have basic lands
    valid_colors = [c for c in colors if c in _BASIC_LANDS.values()]
    if not valid_colors:
        # Default to all five colors equally
        valid_colors = list(_BASIC_LANDS.values())

    # Map color -> land name
    color_to_land = {v: k for k, v in _BASIC_LANDS.items()}

    # Distribute lands proportionally among colors
    per_color = needed // len(valid_colors)
    remainder = needed % len(valid_colors)

    lands: list[dict] = []
    for i, color in enumerate(sorted(valid_colors)):
        land_name = color_to_land.get(color)
        if not land_name:
            continue
        qty = per_color + (1 if i < remainder else 0)
        if qty > 0:
            lands.append(
                {
                    "card_id": None,
                    "name_en": land_name,
                    "set_code": None,
                    "collector_number": None,
                    "quantity": qty,
                    "mana_cost": None,
                    "type_line": "Basic Land",
                    "rarity": "common",
                    "image_uri": None,
                    "price": None,
                    "is_owned": False,
                }
            )

    return lands


def get_commander_candidates(
    repo,
    colors: list[str] | None = None,
    search: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Find legendary creatures that can be commanders.

    Optionally filter by color identity and name search.
    """
    with Session(repo.engine) as session:
        stmt = select(CardRow).where(
            CardRow.game == "magic",
            CardRow.type_line.isnot(None),
            CardRow.type_line.contains("Legendary"),
            CardRow.type_line.contains("Creature"),
        )

        if search:
            stmt = stmt.where(CardRow.name_en.ilike(f"%{search}%"))

        # Check commander legality
        stmt = stmt.where(
            CardRow.id.in_(
                select(CardLegalityRow.card_id).where(
                    CardLegalityRow.format == "commander",
                    CardLegalityRow.status == "legal",
                )
            )
        )

        stmt = stmt.order_by(CardRow.name_en).limit(limit)
        rows = session.execute(stmt).scalars().all()

        # Post-filter by color identity if specified
        if colors:
            color_set = set(colors)
            rows = [r for r in rows if _color_identity_matches(r.color_identity, color_set)]

        return [
            {
                "card_id": r.id,
                "name_en": r.name_en,
                "set_code": r.set_code,
                "collector_number": r.collector_number,
                "color_identity": r.color_identity,
                "mana_cost": r.mana_cost,
                "type_line": r.type_line,
                "rarity": r.rarity,
                "image_uri": r.image_uri,
            }
            for r in rows
        ]


def generate_deck(repo, params: DeckBuildParams) -> GeneratedDeck:
    """Generate a deck from the catalog based on the given parameters.

    Args:
        repo: Repository instance for DB queries
        params: DeckBuildParams with format, colors, archetype, etc.

    Returns a GeneratedDeck dataclass.
    """
    warnings: list[str] = []
    format_name = params.format_name.lower()
    is_singleton = format_name in _SINGLETON_FORMATS

    # Determine target deck size
    if format_name in _SINGLETON_FORMATS:
        target_size = 100
    else:
        target_size = 60

    # Determine colors
    colors: set[str] = set()
    commander_card: CardRow | None = None

    if params.commander_card_id is not None:
        commander_card = repo.get_card_by_id(params.commander_card_id)
        if commander_card:
            ci = commander_card.color_identity or ""
            colors = {c for c in ci if c in {"W", "U", "B", "R", "G"}}
            if not colors:
                colors = {"C"}
        else:
            warnings.append("Commander card not found in catalog")

    if not colors and params.colors:
        colors = set(params.colors)

    if not colors:
        warnings.append("No colors specified; using all five colors")
        colors = {"W", "U", "B", "R", "G"}

    # Get target composition
    composition = _get_target_composition(format_name, params.archetype)
    target_land_count = composition.pop("Land", 37)

    # Get owned card IDs for prioritization
    owned_ids: set[int] = set()
    if params.prioritize_owned and params.user_id:
        with Session(repo.engine) as session:
            rows = (
                session.execute(
                    select(UserCollectionRow.card_id).where(
                        UserCollectionRow.user_id == params.user_id,
                        UserCollectionRow.card_id.isnot(None),
                    )
                )
                .scalars()
                .all()
            )
            owned_ids = set(rows)

    # Get prices for budget enforcement
    prices: dict[int, Decimal] = {}
    budget_remaining = params.budget_limit

    # Build the deck
    all_cards: list[dict] = []
    exclude_ids = set(params.exclude_card_ids)
    selected_names: set[str] = set()

    # If commander format, add the commander first
    if commander_card and format_name in _SINGLETON_FORMATS:
        all_cards.append(
            {
                "card_id": commander_card.id,
                "name_en": commander_card.name_en,
                "set_code": commander_card.set_code,
                "collector_number": commander_card.collector_number,
                "quantity": 1,
                "mana_cost": commander_card.mana_cost,
                "type_line": commander_card.type_line,
                "rarity": commander_card.rarity,
                "image_uri": commander_card.image_uri,
                "price": None,
                "is_owned": commander_card.id in owned_ids,
            }
        )
        exclude_ids.add(commander_card.id)
        selected_names.add(commander_card.name_en)
        # Reduce target by 1 (commander is slot 1)
        # The land count stays the same; reduce from largest non-land category
        max_type = max(composition, key=lambda k: composition[k])
        composition[max_type] -= 1

    # Add commander staples for commander format
    if format_name in _SINGLETON_FORMATS:
        with Session(repo.engine) as session:
            for staple_name in _COMMANDER_STAPLES:
                if staple_name in selected_names:
                    continue
                staple = session.execute(
                    select(CardRow)
                    .where(
                        CardRow.game == "magic",
                        CardRow.name_en == staple_name,
                    )
                    .limit(1)
                ).scalar_one_or_none()
                if staple and staple.id not in exclude_ids:
                    # Determine which category this staple belongs to
                    from src.decks.evaluator import classify_card_type

                    staple_type = classify_card_type(staple.type_line)
                    if staple_type in composition and composition[staple_type] > 0:
                        composition[staple_type] -= 1
                    elif staple_type == "Land":
                        target_land_count -= 1

                    all_cards.append(
                        {
                            "card_id": staple.id,
                            "name_en": staple.name_en,
                            "set_code": staple.set_code,
                            "collector_number": staple.collector_number,
                            "quantity": 1,
                            "mana_cost": staple.mana_cost,
                            "type_line": staple.type_line,
                            "rarity": staple.rarity,
                            "image_uri": staple.image_uri,
                            "price": None,
                            "is_owned": staple.id in owned_ids,
                        }
                    )
                    exclude_ids.add(staple.id)
                    selected_names.add(staple.name_en)

    # Query and select cards for each type
    with Session(repo.engine) as session:
        for card_type, target_count in composition.items():
            if target_count <= 0:
                continue

            candidates = _query_candidates(
                session,
                colors,
                format_name if format_name != "casual" else None,
                card_type,
                limit=max(target_count * 4, 200),
                exclude_ids=exclude_ids,
            )

            # Filter out already-selected names for singleton
            if is_singleton:
                candidates = [c for c in candidates if c.name_en not in selected_names]

            selected = _select_cards(
                candidates,
                target_count,
                is_singleton,
                budget_remaining,
                prices,
                owned_ids,
                params.prioritize_owned,
            )

            for card_dict in selected:
                all_cards.append(card_dict)
                exclude_ids.add(card_dict["card_id"])
                selected_names.add(card_dict["name_en"])
                if budget_remaining is not None:
                    price = card_dict.get("price") or 0
                    budget_remaining -= Decimal(str(price)) * card_dict["quantity"]

            if len(selected) < target_count:
                deficit = target_count - sum(c["quantity"] for c in selected)
                if deficit > 0:
                    warnings.append(
                        f"Could only find {target_count - deficit} of "
                        f"{target_count} target {card_type} cards"
                    )

    # Add basic lands to fill the land slots
    existing_lands = sum(
        c["quantity"] for c in all_cards if c.get("type_line") and "Land" in c["type_line"]
    )
    basic_lands = _add_basic_lands(colors, target_land_count, existing_lands)
    all_cards.extend(basic_lands)

    # Calculate totals
    total_cards = sum(c["quantity"] for c in all_cards)
    final_land_count = sum(
        c["quantity"] for c in all_cards if c.get("type_line") and "Land" in c["type_line"]
    )
    final_nonland_count = total_cards - final_land_count

    # Total value
    total_value = Decimal("0")
    has_prices = False
    for c in all_cards:
        if c.get("price"):
            total_value += Decimal(str(c["price"])) * c["quantity"]
            has_prices = True

    if total_cards < target_size:
        warnings.append(f"Generated {total_cards} cards, target was {target_size}")

    if params.budget_limit and has_prices and total_value > params.budget_limit:
        warnings.append(
            f"Total value R${total_value:.2f} exceeds budget R${params.budget_limit:.2f}"
        )

    return GeneratedDeck(
        cards=all_cards,
        format_name=format_name,
        archetype=params.archetype,
        colors=sorted(colors),
        total_value=total_value if has_prices else None,
        land_count=final_land_count,
        nonland_count=final_nonland_count,
        warnings=warnings,
    )
