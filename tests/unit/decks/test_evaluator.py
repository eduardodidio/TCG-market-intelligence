"""Tests for deck evaluator service — pure functions, no DB."""

from __future__ import annotations

from decimal import Decimal

from src.decks.evaluator import (
    analyze_color_distribution,
    analyze_mana_curve,
    analyze_type_distribution,
    classify_card_type,
    evaluate_deck,
    parse_cmc,
)

# ---------------------------------------------------------------------------
# parse_cmc
# ---------------------------------------------------------------------------


class TestParseCmc:
    def test_simple_generic_plus_colors(self):
        assert parse_cmc("{3}{U}{U}") == 5

    def test_x_cost_counts_as_zero(self):
        assert parse_cmc("{X}{R}") == 1

    def test_hybrid_mana(self):
        assert parse_cmc("{W/U}{B}") == 2

    def test_phyrexian_mana(self):
        assert parse_cmc("{W/P}") == 1

    def test_none_returns_zero(self):
        assert parse_cmc(None) == 0

    def test_empty_string_returns_zero(self):
        assert parse_cmc("") == 0

    def test_zero_mana(self):
        assert parse_cmc("{0}") == 0

    def test_pure_colorless(self):
        assert parse_cmc("{5}") == 5

    def test_all_five_colors(self):
        assert parse_cmc("{W}{U}{B}{R}{G}") == 5

    def test_split_card_uses_front_face(self):
        # Front face is {3}{U}, back face is {1}{R}
        assert parse_cmc("{3}{U} // {1}{R}") == 4

    def test_hybrid_with_generic(self):
        # {2/W} should use the higher cost (2)
        assert parse_cmc("{2/W}") == 2

    def test_colorless_pip(self):
        assert parse_cmc("{C}{C}") == 2

    def test_double_x(self):
        assert parse_cmc("{X}{X}{R}") == 1

    def test_complex_mana_cost(self):
        # {1}{W}{W}{U}
        assert parse_cmc("{1}{W}{W}{U}") == 4


# ---------------------------------------------------------------------------
# classify_card_type
# ---------------------------------------------------------------------------


class TestClassifyCardType:
    def test_legendary_creature(self):
        assert classify_card_type("Legendary Creature \u2014 Dragon") == "Creature"

    def test_instant(self):
        assert classify_card_type("Instant") == "Instant"

    def test_artifact_land(self):
        # Land takes priority
        assert classify_card_type("Artifact Land") == "Land"

    def test_enchantment_creature(self):
        # Creature takes priority over Enchantment
        assert classify_card_type("Enchantment Creature \u2014 God") == "Creature"

    def test_none_returns_other(self):
        assert classify_card_type(None) == "Other"

    def test_empty_string_returns_other(self):
        assert classify_card_type("") == "Other"

    def test_double_faced_card(self):
        assert classify_card_type("Creature // Instant") == "Creature"

    def test_sorcery(self):
        assert classify_card_type("Sorcery") == "Sorcery"

    def test_planeswalker(self):
        assert classify_card_type("Legendary Planeswalker \u2014 Jace") == "Planeswalker"

    def test_artifact(self):
        assert classify_card_type("Artifact \u2014 Equipment") == "Artifact"

    def test_enchantment(self):
        assert classify_card_type("Enchantment \u2014 Aura") == "Enchantment"

    def test_basic_land(self):
        assert classify_card_type("Basic Land \u2014 Plains") == "Land"

    def test_double_dash_subtypes(self):
        assert classify_card_type("Creature -- Elf Warrior") == "Creature"


# ---------------------------------------------------------------------------
# analyze_mana_curve
# ---------------------------------------------------------------------------


class TestAnalyzeManaCurve:
    def test_basic_curve(self):
        cards = [
            {"mana_cost": "{1}", "type_line": "Creature", "quantity": 2},
            {"mana_cost": "{3}{U}{U}", "type_line": "Instant", "quantity": 1},
            {"mana_cost": "{0}", "type_line": "Artifact", "quantity": 1},
        ]
        curve = analyze_mana_curve(cards)
        assert curve.get(0, 0) == 1  # {0} artifact
        assert curve.get(1, 0) == 2  # {1} creature x2
        assert curve.get(5, 0) == 1  # {3}{U}{U} = CMC 5

    def test_lands_excluded(self):
        cards = [
            {"mana_cost": None, "type_line": "Basic Land", "quantity": 4},
            {"mana_cost": "{R}", "type_line": "Creature", "quantity": 1},
        ]
        curve = analyze_mana_curve(cards)
        assert sum(curve.values()) == 1

    def test_high_cmc_bucketed_at_7(self):
        cards = [
            {"mana_cost": "{8}{G}{G}", "type_line": "Creature", "quantity": 1},
        ]
        curve = analyze_mana_curve(cards)
        assert curve.get(7, 0) == 1

    def test_empty_deck(self):
        assert analyze_mana_curve([]) == {}


# ---------------------------------------------------------------------------
# analyze_color_distribution
# ---------------------------------------------------------------------------


class TestAnalyzeColorDistribution:
    def test_basic_colors(self):
        cards = [
            {"mana_cost": "{W}{W}{U}", "type_line": "Creature", "quantity": 1},
            {"mana_cost": "{B}", "type_line": "Instant", "quantity": 2},
        ]
        dist = analyze_color_distribution(cards)
        assert dist["W"] == 2
        assert dist["U"] == 1
        assert dist["B"] == 2

    def test_lands_excluded(self):
        cards = [
            {"mana_cost": None, "type_line": "Land", "quantity": 10},
            {"mana_cost": "{R}", "type_line": "Creature", "quantity": 1},
        ]
        dist = analyze_color_distribution(cards)
        assert dist.get("R", 0) == 1
        assert sum(dist.values()) == 1

    def test_colorless_counted_as_c(self):
        cards = [
            {"mana_cost": "{3}{C}", "type_line": "Creature", "quantity": 1},
        ]
        dist = analyze_color_distribution(cards)
        assert dist.get("C", 0) >= 1

    def test_empty_deck(self):
        assert analyze_color_distribution([]) == {}


# ---------------------------------------------------------------------------
# analyze_type_distribution
# ---------------------------------------------------------------------------


class TestAnalyzeTypeDistribution:
    def test_basic_types(self):
        cards = [
            {"type_line": "Creature \u2014 Human", "quantity": 3},
            {"type_line": "Instant", "quantity": 2},
            {"type_line": "Basic Land \u2014 Plains", "quantity": 10},
        ]
        dist = analyze_type_distribution(cards)
        assert dist["Creature"] == 3
        assert dist["Instant"] == 2
        assert dist["Land"] == 10

    def test_empty_deck(self):
        assert analyze_type_distribution([]) == {}


# ---------------------------------------------------------------------------
# evaluate_deck — integration of all sub-functions
# ---------------------------------------------------------------------------


class TestEvaluateDeck:
    def _sample_deck(self) -> list[dict]:
        """10-card sample deck for testing."""
        return [
            {
                "card_id": 1,
                "name_en": "Lightning Bolt",
                "mana_cost": "{R}",
                "type_line": "Instant",
                "color_identity": "R",
                "rarity": "common",
                "quantity": 4,
            },
            {
                "card_id": 2,
                "name_en": "Counterspell",
                "mana_cost": "{U}{U}",
                "type_line": "Instant",
                "color_identity": "U",
                "rarity": "uncommon",
                "quantity": 2,
            },
            {
                "card_id": 3,
                "name_en": "Tarmogoyf",
                "mana_cost": "{1}{G}",
                "type_line": "Creature \u2014 Lhurgoyf",
                "color_identity": "G",
                "rarity": "mythic",
                "quantity": 2,
            },
            {
                "card_id": 4,
                "name_en": "Plains",
                "mana_cost": None,
                "type_line": "Basic Land \u2014 Plains",
                "color_identity": "",
                "rarity": "common",
                "quantity": 10,
            },
            {
                "card_id": 5,
                "name_en": "Sol Ring",
                "mana_cost": "{1}",
                "type_line": "Artifact",
                "color_identity": "",
                "rarity": "uncommon",
                "quantity": 1,
            },
        ]

    def test_total_cards(self):
        result = evaluate_deck(self._sample_deck())
        assert result.total_cards == 19  # 4+2+2+10+1

    def test_land_count(self):
        result = evaluate_deck(self._sample_deck())
        assert result.land_count == 10

    def test_nonland_count(self):
        result = evaluate_deck(self._sample_deck())
        assert result.nonland_count == 9

    def test_avg_cmc(self):
        result = evaluate_deck(self._sample_deck())
        # Non-land: Bolt(1)*4 + Counterspell(2)*2 + Tarmogoyf(2)*2 + Sol Ring(1)*1
        # = 4 + 4 + 4 + 1 = 13, count = 9, avg = 13/9 = 1.44
        assert result.avg_cmc == round(13 / 9, 2)

    def test_mana_curve_excludes_lands(self):
        result = evaluate_deck(self._sample_deck())
        total_in_curve = sum(result.mana_curve.values())
        assert total_in_curve == 9  # All non-land cards

    def test_type_distribution_sums_correctly(self):
        result = evaluate_deck(self._sample_deck())
        total = sum(result.type_distribution.values())
        assert total == result.total_cards

    def test_color_identity_union(self):
        result = evaluate_deck(self._sample_deck())
        assert result.color_identity == {"R", "U", "G"}

    def test_no_legality_check_without_format(self):
        result = evaluate_deck(self._sample_deck())
        assert result.legality_check is None

    def test_no_budget_without_prices(self):
        result = evaluate_deck(self._sample_deck())
        assert result.budget is None

    def test_empty_deck(self):
        result = evaluate_deck([])
        assert result.total_cards == 0
        assert result.land_count == 0
        assert result.nonland_count == 0
        assert result.avg_cmc == 0.0
        assert result.mana_curve == {}
        assert result.color_distribution == {}
        assert result.type_distribution == {}
        assert result.color_identity == set()


# ---------------------------------------------------------------------------
# Legality checks
# ---------------------------------------------------------------------------


class TestLegalityCheck:
    def _deck_with_banned(self) -> tuple[list[dict], dict, dict]:
        cards = [
            {
                "card_id": 1,
                "name_en": "Legal Card",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 1,
            },
            {
                "card_id": 2,
                "name_en": "Banned Card",
                "mana_cost": "{B}",
                "type_line": "Instant",
                "color_identity": "B",
                "quantity": 1,
            },
        ]
        legalities = {
            1: [{"format": "commander", "status": "legal"}],
            2: [{"format": "commander", "status": "banned"}],
        }
        return cards, legalities, "commander"

    def test_banned_card_makes_deck_illegal(self):
        cards, legalities, fmt = self._deck_with_banned()
        result = evaluate_deck(cards, legalities=legalities, format_name=fmt)
        assert result.legality_check is not None
        assert result.legality_check["is_legal"] is False
        assert len(result.legality_check["illegal_cards"]) == 1
        assert result.legality_check["illegal_cards"][0]["name_en"] == "Banned Card"

    def test_all_legal_cards(self):
        cards = [
            {
                "card_id": 1,
                "name_en": "Good Card",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 1,
            },
        ]
        legalities = {1: [{"format": "modern", "status": "legal"}]}
        result = evaluate_deck(cards, legalities=legalities, format_name="modern")
        assert result.legality_check["is_legal"] is True
        assert result.legality_check["illegal_cards"] == []

    def test_singleton_violations(self):
        cards = [
            {
                "card_id": 1,
                "name_en": "Duplicate Card",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 2,
            },
        ]
        legalities = {1: [{"format": "commander", "status": "legal"}]}
        result = evaluate_deck(cards, legalities=legalities, format_name="commander")
        assert result.legality_check is not None
        assert "Duplicate Card" in result.legality_check["singleton_violations"]
        assert result.legality_check["is_legal"] is False

    def test_basic_lands_exempt_from_singleton(self):
        cards = [
            {
                "card_id": 1,
                "name_en": "Plains",
                "mana_cost": None,
                "type_line": "Basic Land",
                "color_identity": "",
                "quantity": 10,
            },
        ]
        legalities = {1: [{"format": "commander", "status": "legal"}]}
        result = evaluate_deck(cards, legalities=legalities, format_name="commander")
        assert result.legality_check["singleton_violations"] == []

    def test_card_count_valid(self):
        # A 2-card deck should fail the 60-card standard check
        cards = [
            {
                "card_id": 1,
                "name_en": "Card",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 2,
            },
        ]
        legalities = {1: [{"format": "standard", "status": "legal"}]}
        result = evaluate_deck(cards, legalities=legalities, format_name="standard")
        assert result.legality_check["card_count_valid"] is False


# ---------------------------------------------------------------------------
# Budget analysis
# ---------------------------------------------------------------------------


class TestBudgetAnalysis:
    def test_budget_total(self):
        cards = [
            {
                "card_id": 1,
                "name_en": "Cheap Card",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 4,
            },
            {
                "card_id": 2,
                "name_en": "Expensive Card",
                "mana_cost": "{3}",
                "type_line": "Creature",
                "color_identity": "U",
                "quantity": 1,
            },
        ]
        prices = {1: Decimal("2.50"), 2: Decimal("100.00")}
        result = evaluate_deck(cards, prices=prices)
        assert result.budget is not None
        assert result.budget["total_value"] == Decimal("110.00")

    def test_most_expensive_top5(self):
        cards = [
            {
                "card_id": i,
                "name_en": f"Card {i}",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 1,
            }
            for i in range(1, 8)
        ]
        prices = {i: Decimal(str(i * 10)) for i in range(1, 8)}
        result = evaluate_deck(cards, prices=prices)
        assert result.budget is not None
        assert len(result.budget["most_expensive"]) == 5
        # Most expensive should be card 7 (70), 6 (60), 5 (50), 4 (40), 3 (30)
        top_names = [c["name_en"] for c in result.budget["most_expensive"]]
        assert top_names[0] == "Card 7"

    def test_price_tiers(self):
        cards = [
            {
                "card_id": 1,
                "name_en": "Budget",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 1,
            },
            {
                "card_id": 2,
                "name_en": "Mid",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 1,
            },
            {
                "card_id": 3,
                "name_en": "Premium",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 1,
            },
            {
                "card_id": 4,
                "name_en": "Chase",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 1,
            },
        ]
        prices = {
            1: Decimal("3.00"),  # budget (<5)
            2: Decimal("15.00"),  # mid (5-20)
            3: Decimal("30.00"),  # premium (20-50)
            4: Decimal("80.00"),  # chase (>50)
        }
        result = evaluate_deck(cards, prices=prices)
        tiers = result.budget["price_tiers"]
        assert tiers["budget"] == 1
        assert tiers["mid"] == 1
        assert tiers["premium"] == 1
        assert tiers["chase"] == 1

    def test_tier_counts_sum_to_priced_cards(self):
        cards = [
            {
                "card_id": 1,
                "name_en": "A",
                "mana_cost": "{1}",
                "type_line": "Creature",
                "color_identity": "W",
                "quantity": 3,
            },
        ]
        prices = {1: Decimal("2.00")}
        result = evaluate_deck(cards, prices=prices)
        tiers = result.budget["price_tiers"]
        assert sum(tiers.values()) == 3  # quantity-weighted
