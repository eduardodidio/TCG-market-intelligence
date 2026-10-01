"""Pure Goldfish (solitaire) simulator for deck testing.

No DB imports, no FastAPI imports. Receives card data as input and
returns computed simulation results (opening hand quality, mana curve,
screw/flood rates).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass

# Regex to extract individual mana symbols from a mana_cost string like "{3}{U}{U}"
_MANA_SYMBOL_RE = re.compile(r"\{([^}]+)\}")

# Colors that count as 1 pip each
_COLOR_PIPS = {"W", "U", "B", "R", "G"}

# Opening hand quality by land count (index = number of lands)
_HAND_QUALITY_BY_LANDS = [0.0, 0.3, 0.9, 1.0, 0.7, 0.3, 0.1, 0.1]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class TurnData:
    """Per-turn simulation data."""

    turn: int
    lands_in_play: int
    spells_castable: int
    spells_cast: int
    cards_in_hand: int


@dataclass
class SingleGameResult:
    """Result of a single goldfish game."""

    opening_hand_quality: float
    opening_hand_lands: int
    opening_hand_names: list[str]
    turns: list[TurnData]


@dataclass
class SampleHand:
    """A representative opening hand from the simulations."""

    cards: list[str]  # card names
    quality: float
    land_count: int


@dataclass
class GoldfishResult:
    """Aggregated result across all goldfish simulations."""

    opening_hand_quality: float  # avg across all simulations
    avg_mana_by_turn: list[float]  # index 0 = turn 1
    mana_screw_rate: float  # 0.0-1.0
    mana_flood_rate: float  # 0.0-1.0
    avg_spells_cast_by_turn: list[float]  # index 0 = turn 1
    sample_hands: list[SampleHand]  # 3 representative hands
    total_simulations: int
    total_turns: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_land(type_line: str | None) -> bool:
    """Check if a card is a land based on its type_line.

    Returns True if type_line contains "Land" (case-insensitive).
    Handles None gracefully (returns False).
    """
    if not type_line:
        return False
    return bool(re.search(r"\bLand\b", type_line, re.IGNORECASE))


def _parse_cmc_simple(mana_cost: str | None) -> int:
    """Parse a mana cost string like ``{3}{U}{U}`` into converted mana cost.

    Rules:
    - ``{X}`` counts as 0
    - ``{N}`` (numeric) counts as N
    - Color pips ``{W}``, ``{U}``, ``{B}``, ``{R}``, ``{G}`` count as 1
    - Hybrid ``{W/U}`` counts as 1
    - Phyrexian ``{W/P}`` counts as 1
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
        # Color pip or colorless pip
        if sym_upper in _COLOR_PIPS or sym_upper == "C":
            total += 1
            continue
        # Unknown symbol -- treat as 1
        total += 1

    return total


def _evaluate_opening_hand(hand: list[dict]) -> float:
    """Evaluate opening hand quality on a 0.0 to 1.0 scale.

    Heuristic based on land count:
    - 0 lands = 0.0
    - 1 land  = 0.3
    - 2 lands = 0.9
    - 3 lands = 1.0
    - 4 lands = 0.7
    - 5 lands = 0.3
    - 6+ lands = 0.1

    Bonus: +0.1 if hand contains a non-land spell with CMC in 1-2
    (capped at 1.0).
    """
    land_count = sum(1 for card in hand if _is_land(card.get("type_line")))

    # Clamp to table size
    if land_count >= len(_HAND_QUALITY_BY_LANDS):
        quality = _HAND_QUALITY_BY_LANDS[-1]
    else:
        quality = _HAND_QUALITY_BY_LANDS[land_count]

    # Bonus for having a low-cost spell
    has_low_cmc = any(
        not _is_land(card.get("type_line")) and 1 <= _parse_cmc_simple(card.get("mana_cost")) <= 2
        for card in hand
    )
    if has_low_cmc:
        quality = min(quality + 0.1, 1.0)

    return quality


# ---------------------------------------------------------------------------
# Simulation
# ---------------------------------------------------------------------------


def _simulate_single_game(
    deck_list: list[dict],
    turns: int,
    rng: random.Random,
) -> SingleGameResult:
    """Simulate a single goldfish game.

    Shuffles a copy of the deck, draws 7 for the opening hand, then
    simulates ``turns`` turns of play (draw, play a land, count castable
    spells).
    """
    deck = list(deck_list)
    rng.shuffle(deck)

    hand_size = min(7, len(deck))
    hand = deck[:hand_size]
    library = deck[hand_size:]

    opening_quality = _evaluate_opening_hand(hand)
    opening_lands = sum(1 for c in hand if _is_land(c.get("type_line")))
    opening_names = [c.get("name_en", "Unknown") for c in hand]

    lands_in_play = 0
    turn_data: list[TurnData] = []

    for turn_num in range(1, turns + 1):
        # Draw a card (simplified: always draw, even turn 1)
        if library:
            drawn = library.pop(0)
            hand.append(drawn)

        # Play a land from hand if available
        for i, card in enumerate(hand):
            if _is_land(card.get("type_line")):
                hand.pop(i)
                lands_in_play += 1
                break

        # Count castable spells (CMC <= lands_in_play) among non-lands in hand
        spells_in_hand = [
            (idx, card) for idx, card in enumerate(hand) if not _is_land(card.get("type_line"))
        ]
        # Sort by CMC ascending to greedily cast cheapest first
        spells_in_hand.sort(key=lambda x: _parse_cmc_simple(x[1].get("mana_cost")))

        castable = sum(
            1
            for _, card in spells_in_hand
            if _parse_cmc_simple(card.get("mana_cost")) <= lands_in_play
        )

        # Simulate casting: greedily cast cheapest spells with available mana
        remaining_mana = lands_in_play
        cast_this_turn = 0
        indices_to_remove: list[int] = []
        for idx, card in spells_in_hand:
            cmc = _parse_cmc_simple(card.get("mana_cost"))
            if cmc <= remaining_mana:
                remaining_mana -= cmc
                cast_this_turn += 1
                indices_to_remove.append(idx)

        # Remove cast cards from hand (reverse order to preserve indices)
        for idx in sorted(indices_to_remove, reverse=True):
            hand.pop(idx)

        turn_data.append(
            TurnData(
                turn=turn_num,
                lands_in_play=lands_in_play,
                spells_castable=castable,
                spells_cast=cast_this_turn,
                cards_in_hand=len(hand),
            )
        )

    return SingleGameResult(
        opening_hand_quality=opening_quality,
        opening_hand_lands=opening_lands,
        opening_hand_names=opening_names,
        turns=turn_data,
    )


def simulate_goldfish(
    cards: list[dict],
    num_simulations: int = 100,
    turns: int = 7,
    rng: random.Random | None = None,
) -> GoldfishResult:
    """Run multiple goldfish simulations and aggregate results.

    Args:
        cards: list of dicts with keys: name_en, quantity, type_line, mana_cost
        num_simulations: number of independent games to simulate
        turns: number of turns per game
        rng: optional Random instance for reproducibility

    Returns:
        A GoldfishResult with aggregated statistics.
    """
    if rng is None:
        rng = random.Random()

    # Expand deck by quantities
    deck_list: list[dict] = []
    for card in cards:
        qty = card.get("quantity", 1)
        for _ in range(qty):
            deck_list.append(card)

    if not deck_list:
        return GoldfishResult(
            opening_hand_quality=0.0,
            avg_mana_by_turn=[0.0] * turns,
            mana_screw_rate=1.0,
            mana_flood_rate=0.0,
            avg_spells_cast_by_turn=[0.0] * turns,
            sample_hands=[],
            total_simulations=0,
            total_turns=turns,
        )

    results: list[SingleGameResult] = []
    for _ in range(num_simulations):
        game = _simulate_single_game(deck_list, turns, rng)
        results.append(game)

    # Aggregate: opening hand quality
    avg_quality = sum(r.opening_hand_quality for r in results) / len(results)

    # Aggregate: avg mana by turn and avg spells cast by turn
    mana_by_turn = [0.0] * turns
    spells_by_turn = [0.0] * turns
    for result in results:
        for td in result.turns:
            idx = td.turn - 1
            if idx < turns:
                mana_by_turn[idx] += td.lands_in_play
                spells_by_turn[idx] += td.spells_cast
    for i in range(turns):
        mana_by_turn[i] = round(mana_by_turn[i] / len(results), 2)
        spells_by_turn[i] = round(spells_by_turn[i] / len(results), 2)

    # Mana screw/flood rates
    screw_count = 0
    flood_count = 0
    deck_size = len(deck_list)

    for result in results:
        opening_lands = result.opening_hand_lands

        # Mana screw: opening hand <= 1 land OR by turn 4, lands_in_play <= 2
        is_screw = opening_lands <= 1
        if not is_screw:
            for td in result.turns:
                if td.turn == 4 and td.lands_in_play <= 2:
                    is_screw = True
                    break
        if is_screw:
            screw_count += 1

        # Mana flood: opening hand >= 5 lands OR by turn 7,
        # lands_in_play / total_cards_seen >= 0.70
        is_flood = opening_lands >= 5
        if not is_flood:
            hand_size = min(7, deck_size)
            check_turn = min(7, turns)
            total_cards_seen = hand_size + check_turn
            for td in result.turns:
                if td.turn == check_turn:
                    # lands_in_play represents played lands; but unplayed lands
                    # may still be in hand. For simplicity, use lands_in_play
                    # as a lower bound. In our simulation we always play a land
                    # when available, so lands_in_play is close to total lands
                    # drawn (minus at most the lands in hand on this turn).
                    if total_cards_seen > 0 and td.lands_in_play / total_cards_seen >= 0.70:
                        is_flood = True
                    break
        if is_flood:
            flood_count += 1

    screw_rate = round(screw_count / len(results), 4)
    flood_rate = round(flood_count / len(results), 4)

    # Sample hands: best, worst, median quality
    sample_hands: list[SampleHand] = []
    sorted_results = sorted(results, key=lambda r: r.opening_hand_quality)
    if sorted_results:
        worst = sorted_results[0]
        best = sorted_results[-1]
        median = sorted_results[len(sorted_results) // 2]

        for r in [worst, median, best]:
            sample_hands.append(
                SampleHand(
                    cards=r.opening_hand_names,
                    quality=r.opening_hand_quality,
                    land_count=r.opening_hand_lands,
                )
            )

    return GoldfishResult(
        opening_hand_quality=round(avg_quality, 4),
        avg_mana_by_turn=mana_by_turn,
        mana_screw_rate=screw_rate,
        mana_flood_rate=flood_rate,
        avg_spells_cast_by_turn=spells_by_turn,
        sample_hands=sample_hands,
        total_simulations=len(results),
        total_turns=turns,
    )
