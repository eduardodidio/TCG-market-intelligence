"""Deck suggestion engine — generates actionable feedback based on deck evaluation.

Compares a DeckEvaluation result against archetype template ratios and
known-good heuristics to produce human-readable suggestions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.models import DeckEvaluation

# Archetype composition templates with recommended ranges.
# Only commander (100-card singleton) templates for now.
# Standard/modern (60-card) can be added later with the same structure.
ARCHETYPE_TEMPLATES: dict[str, dict[str, dict]] = {
    "commander": {
        "aggro": {
            "land_range": (34, 38),
            "creature_range": (28, 35),
            "instant_range": (6, 12),
            "sorcery_range": (4, 8),
            "enchantment_range": (3, 8),
            "artifact_range": (8, 15),
            "removal_min": 8,
            "card_draw_min": 8,
            "ramp_min": 8,
            "avg_cmc_range": (2.0, 3.2),
        },
        "control": {
            "land_range": (36, 40),
            "creature_range": (8, 16),
            "instant_range": (12, 18),
            "sorcery_range": (6, 12),
            "enchantment_range": (5, 12),
            "artifact_range": (8, 15),
            "removal_min": 10,
            "card_draw_min": 10,
            "ramp_min": 8,
            "avg_cmc_range": (2.5, 3.8),
        },
        "midrange": {
            "land_range": (35, 39),
            "creature_range": (20, 28),
            "instant_range": (6, 12),
            "sorcery_range": (5, 10),
            "enchantment_range": (4, 10),
            "artifact_range": (8, 14),
            "removal_min": 8,
            "card_draw_min": 8,
            "ramp_min": 10,
            "avg_cmc_range": (2.5, 3.5),
        },
        "combo": {
            "land_range": (34, 38),
            "creature_range": (14, 22),
            "instant_range": (8, 14),
            "sorcery_range": (8, 14),
            "enchantment_range": (5, 12),
            "artifact_range": (10, 18),
            "removal_min": 6,
            "card_draw_min": 10,
            "ramp_min": 10,
            "avg_cmc_range": (2.0, 3.2),
        },
        "tempo": {
            "land_range": (34, 38),
            "creature_range": (20, 28),
            "instant_range": (10, 16),
            "sorcery_range": (4, 8),
            "enchantment_range": (3, 8),
            "artifact_range": (8, 14),
            "removal_min": 8,
            "card_draw_min": 8,
            "ramp_min": 8,
            "avg_cmc_range": (1.8, 2.8),
        },
    },
}

# Expected deck sizes per format (same as evaluator)
_FORMAT_DECK_SIZE: dict[str, int] = {
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

# Singleton formats
_SINGLETON_FORMATS = {"commander", "brawl", "duel", "oathbreaker"}

# Generic land ranges (when no archetype template is available)
_GENERIC_LAND_RANGE: dict[str, tuple[int, int]] = {
    "commander": (33, 40),
    "brawl": (20, 26),
    "oathbreaker": (20, 26),
    "standard": (20, 26),
    "modern": (20, 26),
    "legacy": (20, 26),
    "vintage": (20, 26),
    "pioneer": (20, 26),
    "pauper": (20, 26),
}

# Generic CMC thresholds (no archetype)
_GENERIC_CMC_HIGH = 3.5
_GENERIC_CMC_LOW = 1.5

# Minimum instants for interaction check
_MIN_INSTANTS = 4


def _in_range(value: float, range_tuple: tuple[float, float]) -> str | None:
    """Return 'low' if value is below range, 'high' if above, None if in range."""
    if value < range_tuple[0]:
        return "low"
    if value > range_tuple[1]:
        return "high"
    return None


def generate_suggestions(
    evaluation: DeckEvaluation,
    archetype: str | None = None,
    format_name: str | None = None,
) -> list[str]:
    """Generate actionable suggestions based on deck evaluation and archetype template.

    Args:
        evaluation: A DeckEvaluation result with computed stats.
        archetype: Optional archetype name (aggro, control, midrange, combo, tempo).
        format_name: Optional format name (commander, standard, modern, etc.).

    Returns:
        List of human-readable suggestion strings, sorted by severity
        (structural issues first, optimization suggestions last).
    """
    critical: list[str] = []  # Card count, legality, unlinked
    warnings: list[str] = []  # Land count, CMC, composition
    info: list[str] = []  # Color balance, interaction

    fmt = format_name.lower() if format_name else None

    # Get the archetype template if available
    template = None
    if fmt and archetype:
        arch_key = archetype.lower()
        format_templates = ARCHETYPE_TEMPLATES.get(fmt)
        if format_templates:
            template = format_templates.get(arch_key)

    # 1. Card count check
    if fmt:
        expected = _FORMAT_DECK_SIZE.get(fmt)
        if expected is not None and evaluation.total_cards != expected:
            critical.append(
                f"Deck has {evaluation.total_cards} cards, expected {expected} for {fmt}."
            )

    # 2. Banned / illegal cards
    if evaluation.legality_check:
        illegal = evaluation.legality_check.get("illegal_cards", [])
        if illegal:
            names = ", ".join(c["name_en"] for c in illegal[:5])
            suffix = f" (and {len(illegal) - 5} more)" if len(illegal) > 5 else ""
            critical.append(
                f"{len(illegal)} card(s) are not legal in "
                f"{evaluation.legality_check.get('format', fmt or 'this format')}: "
                f"{names}{suffix}."
            )

    # 3. Singleton violations
    if evaluation.legality_check:
        violations = evaluation.legality_check.get("singleton_violations", [])
        if violations:
            names = ", ".join(violations[:5])
            suffix = f" (and {len(violations) - 5} more)" if len(violations) > 5 else ""
            critical.append(
                f"Cards appearing more than once: {names}{suffix}. Commander decks are singleton."
            )

    # Note: unlinked_count is handled at the API endpoint level (decks.py),
    # not here, because the evaluator doesn't have access to the raw deck
    # card data needed to count unlinked entries.

    # 4. Land count checks
    if template:
        land_range = template["land_range"]
        land_status = _in_range(evaluation.land_count, land_range)
        if land_status == "low":
            deficit = land_range[0] - evaluation.land_count
            arch_label = archetype.lower() if archetype else "this"
            warnings.append(
                f"Consider adding {deficit} more lands. "
                f"{arch_label.capitalize()} decks in {fmt} typically run "
                f"{land_range[0]}-{land_range[1]} lands."
            )
        elif land_status == "high":
            surplus = evaluation.land_count - land_range[1]
            arch_label = archetype.lower() if archetype else "this"
            warnings.append(
                f"Consider cutting {surplus} lands. You have "
                f"{evaluation.land_count} but {arch_label} decks typically "
                f"run {land_range[0]}-{land_range[1]}."
            )
    elif fmt:
        # Generic land check
        generic_range = _GENERIC_LAND_RANGE.get(fmt)
        if generic_range:
            land_status = _in_range(evaluation.land_count, generic_range)
            if land_status == "low":
                deficit = generic_range[0] - evaluation.land_count
                warnings.append(
                    f"Consider adding {deficit} more lands. "
                    f"Decks in {fmt} typically run "
                    f"{generic_range[0]}-{generic_range[1]} lands."
                )
            elif land_status == "high":
                surplus = evaluation.land_count - generic_range[1]
                warnings.append(
                    f"Consider cutting {surplus} lands. You have "
                    f"{evaluation.land_count} but {fmt} decks typically "
                    f"run {generic_range[0]}-{generic_range[1]}."
                )

    # 6. Creature count check (only with template)
    if template:
        creature_range = template["creature_range"]
        creature_count = evaluation.type_distribution.get("Creature", 0)
        creature_status = _in_range(creature_count, creature_range)
        arch_label = archetype.lower() if archetype else "this"
        if creature_status == "low":
            deficit = creature_range[0] - creature_count
            warnings.append(
                f"Consider adding {deficit} more creatures. "
                f"{arch_label.capitalize()} decks typically run "
                f"{creature_range[0]}-{creature_range[1]}."
            )
        elif creature_status == "high":
            surplus = creature_count - creature_range[1]
            warnings.append(
                f"Consider cutting {surplus} creatures. You have "
                f"{creature_count} but {arch_label} decks typically "
                f"run {creature_range[0]}-{creature_range[1]}."
            )

    # 7. Average CMC check
    if evaluation.nonland_count > 0:
        if template:
            cmc_range = template["avg_cmc_range"]
            cmc_status = _in_range(evaluation.avg_cmc, cmc_range)
            arch_label = archetype.lower() if archetype else "this"
            if cmc_status == "high":
                warnings.append(
                    f"Average mana cost is {evaluation.avg_cmc:.1f}, which is "
                    f"high for {arch_label}. Consider adding more low-cost cards."
                )
            elif cmc_status == "low":
                warnings.append(
                    f"Average mana cost is {evaluation.avg_cmc:.1f}. For a "
                    f"{arch_label} deck, consider adding some higher-impact spells."
                )
        else:
            # Generic CMC check
            if evaluation.avg_cmc > _GENERIC_CMC_HIGH:
                warnings.append(
                    f"Average mana cost is {evaluation.avg_cmc:.1f}, which is "
                    f"high. Consider adding more low-cost spells."
                )

    # 8. Color balance (3+ colors, any color < 10% of total pips)
    color_pips = {
        k: v for k, v in evaluation.color_distribution.items() if k in {"W", "U", "B", "R", "G"}
    }
    if len(color_pips) >= 3:
        total_pips = sum(color_pips.values())
        if total_pips > 0:
            color_names = {
                "W": "White",
                "U": "Blue",
                "B": "Black",
                "R": "Red",
                "G": "Green",
            }
            for color, count in color_pips.items():
                pct = count / total_pips * 100
                if pct < 10:
                    name = color_names.get(color, color)
                    info.append(
                        f"Color {name} has very few cards ({count} pips, "
                        f"{pct:.0f}%). Consider adding more {name} cards "
                        f"or removing it from the color identity."
                    )

    # 9. Low instant count (interaction check)
    instant_count = evaluation.type_distribution.get("Instant", 0)
    if instant_count < _MIN_INSTANTS and evaluation.total_cards >= 20:
        info.append(
            "Very few instant-speed answers. Consider adding counterspells, "
            "removal, or combat tricks."
        )

    # Return sorted by severity: critical first, then warnings, then info
    return critical + warnings + info
