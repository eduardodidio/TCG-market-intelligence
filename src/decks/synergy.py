"""Pure synergy scoring engine for deck generation.

No DB imports, no framework imports. Only stdlib ``re`` and ``dataclasses``.

Three public functions:
  - ``extract_commander_keywords`` — analyse a commander's oracle text and
    type line to derive tribal types, mechanic keywords, and referenced
    card types.
  - ``classify_card_role`` — classify a card's oracle text into one or more
    mechanical roles (draw, ramp, removal, etc.).
  - ``score_synergy`` — score how well a candidate card synergises with the
    commander keywords (0.0 – 1.0).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Supertypes and card types to strip when extracting creature subtypes
_SUPERTYPES = {
    "Legendary",
    "Basic",
    "Snow",
    "World",
    "Ongoing",
    "Elite",
    "Host",
}

_CARD_TYPES = {
    "Creature",
    "Artifact",
    "Enchantment",
    "Instant",
    "Sorcery",
    "Land",
    "Planeswalker",
    "Battle",
    "Kindred",  # replacement for Tribal (card type)
    "Tribal",
}

# ---------------------------------------------------------------------------
# Mechanic keyword patterns (case-insensitive)
# ---------------------------------------------------------------------------

_MECHANIC_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "draw": [
        re.compile(r"draws?\s+(?:a\s+)?cards?", re.IGNORECASE),
        re.compile(r"draws?\s+\w+\s+cards?", re.IGNORECASE),
    ],
    "ramp": [
        re.compile(r"add\s*\{", re.IGNORECASE),
        re.compile(r"search your library for a?.?(?:basic )?land", re.IGNORECASE),
        re.compile(r"add \w+ mana", re.IGNORECASE),
    ],
    "removal": [
        re.compile(r"destroy target", re.IGNORECASE),
        re.compile(r"exile target", re.IGNORECASE),
        re.compile(r"deals?\s+\d+\s+damage", re.IGNORECASE),
        re.compile(r"-\d+/-\d+", re.IGNORECASE),
        re.compile(r"destroy all", re.IGNORECASE),
    ],
    "token": [
        re.compile(r"creates?\s+(?:a\s+)?[\w/]+.*?token", re.IGNORECASE),
        re.compile(r"populate", re.IGNORECASE),
    ],
    "counter": [
        re.compile(r"\+1/\+1 counter", re.IGNORECASE),
        re.compile(r"counters? on", re.IGNORECASE),
    ],
    "sacrifice": [
        re.compile(r"sacrifice a", re.IGNORECASE),
        re.compile(r"when\s+.{1,30}\s+dies", re.IGNORECASE),
        re.compile(r"whenever\s+.{1,30}\s+dies", re.IGNORECASE),
    ],
    "flicker": [
        re.compile(r"exile\s+.{1,40}\s+return", re.IGNORECASE),
        re.compile(r"blink", re.IGNORECASE),
        re.compile(r"flicker", re.IGNORECASE),
    ],
    "lifegain": [
        re.compile(r"gains?\s+\d+\s+life", re.IGNORECASE),
        re.compile(r"you gain life", re.IGNORECASE),
        re.compile(r"lifelink", re.IGNORECASE),
    ],
    "graveyard": [
        re.compile(r"from your graveyard", re.IGNORECASE),
        re.compile(r"return .{1,30} from .{0,10}graveyard", re.IGNORECASE),
        re.compile(r"mill", re.IGNORECASE),
    ],
    "protection": [
        re.compile(r"hexproof", re.IGNORECASE),
        re.compile(r"indestructible", re.IGNORECASE),
        re.compile(r"protection from", re.IGNORECASE),
        re.compile(r"shroud", re.IGNORECASE),
        re.compile(r"ward", re.IGNORECASE),
    ],
    "equipment": [
        re.compile(r"equip", re.IGNORECASE),
        re.compile(r"equipped creature", re.IGNORECASE),
        re.compile(r"attach", re.IGNORECASE),
    ],
    "enchantress": [
        re.compile(r"whenever .{0,20} enchantment", re.IGNORECASE),
        re.compile(r"constellation", re.IGNORECASE),
        re.compile(r"enchant ", re.IGNORECASE),
    ],
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommanderKeywords:
    """Extracted keyword information from a commander card."""

    tribal_types: list[str]  # creature subtypes from type_line
    mechanic_keywords: list[str]  # mechanical themes from oracle_text
    referenced_types: list[str]  # card types referenced in oracle_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def extract_subtypes(type_line: str) -> list[str]:
    """Extract creature subtypes from a type line.

    Splits on em-dash (``\\u2014``), strips supertypes and card types from
    the left side, and returns the remaining words from the right side as
    creature subtypes.
    """
    if not type_line:
        return []

    # For DFC, use front face only
    if " // " in type_line:
        type_line = type_line.split(" // ")[0]

    # Split on em-dash
    if " \u2014 " in type_line:
        parts = type_line.split(" \u2014 ")
        if len(parts) >= 2:
            subtype_part = parts[1].strip()
            return [w for w in subtype_part.split() if w]

    # No em-dash: all words except supertypes and card types
    words = type_line.split()
    subtypes = [w for w in words if w not in _SUPERTYPES and w not in _CARD_TYPES]
    return subtypes


def _extract_mechanics(oracle_text: str) -> list[str]:
    """Return sorted list of mechanic keywords found in oracle_text."""
    if not oracle_text:
        return []
    found: list[str] = []
    for keyword, patterns in _MECHANIC_PATTERNS.items():
        for pat in patterns:
            if pat.search(oracle_text):
                found.append(keyword)
                break
    return sorted(found)


def _extract_referenced_types(oracle_text: str) -> list[str]:
    """Extract card types referenced in oracle text."""
    if not oracle_text:
        return []
    referenced: list[str] = []
    lower = oracle_text.lower()
    for card_type in _CARD_TYPES:
        if card_type.lower() in lower:
            referenced.append(card_type)
    return sorted(referenced)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_commander_keywords(
    oracle_text: str,
    type_line: str,
) -> CommanderKeywords:
    """Analyse a commander card to extract keyword information.

    Args:
        oracle_text: The commander's oracle (rules) text.
        type_line: The commander's full type line.

    Returns:
        A :class:`CommanderKeywords` instance.
    """
    tribal_types = extract_subtypes(type_line)
    mechanic_keywords = _extract_mechanics(oracle_text)
    referenced_types = _extract_referenced_types(oracle_text)

    return CommanderKeywords(
        tribal_types=tribal_types,
        mechanic_keywords=mechanic_keywords,
        referenced_types=referenced_types,
    )


def classify_card_role(oracle_text: str) -> list[str]:
    """Classify a card's oracle text into mechanical roles.

    Returns a sorted list of matched role names.  If nothing matches,
    returns ``["utility"]``.
    """
    roles = _extract_mechanics(oracle_text)
    return roles if roles else ["utility"]


def score_synergy(
    card_oracle_text: str,
    card_type_line: str,
    commander_keywords: CommanderKeywords,
) -> float:
    """Score how well a candidate card synergises with the commander.

    Returns a float between 0.0 and 1.0:
      - Tribal match: +0.3 per shared creature subtype (max 0.6).
      - Mechanic match: +0.2 per shared mechanic keyword (max 0.6).
      - Capped at 1.0.
    """
    score = 0.0

    # Tribal matching
    card_subtypes = extract_subtypes(card_type_line) if card_type_line else []
    card_subtypes_lower = {s.lower() for s in card_subtypes}
    commander_tribals_lower = {t.lower() for t in commander_keywords.tribal_types}

    tribal_matches = len(card_subtypes_lower & commander_tribals_lower)
    score += min(tribal_matches * 0.3, 0.6)

    # Mechanic matching
    card_mechanics = set(_extract_mechanics(card_oracle_text))
    commander_mechanics = set(commander_keywords.mechanic_keywords)

    mechanic_matches = len(card_mechanics & commander_mechanics)
    score += min(mechanic_matches * 0.2, 0.6)

    return min(score, 1.0)
