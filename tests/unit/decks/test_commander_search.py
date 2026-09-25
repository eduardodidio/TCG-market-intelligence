"""Tests for commander search + soft legality filter (F172-T02).

Uses a real in-memory SQLite Repository so the SQL (ilike/escape,
soft legality subquery, over-fetch cap) is exercised end-to-end.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import update
from sqlalchemy.orm import Session

from src.database.models import CardLegalityRow, CardRow, PriceObservationRow
from src.database.repository import Repository
from src.decks.builder import (
    _escape_like,
    generate_deck,
    get_commander_candidates,
    is_commander_eligible,
)
from src.domain.models import DeckBuildParams

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo() -> Repository:
    return Repository("sqlite:///:memory:")


_counter = {"n": 0}


def _card(
    name_en: str,
    *,
    name_pt: str | None = None,
    type_line: str | None = "Legendary Creature — Human",
    color_identity: str | None = "",
    image_uri: str | None = "https://img/x.jpg",
    set_code: str | None = None,
    rarity: str = "rare",
) -> CardRow:
    _counter["n"] += 1
    return CardRow(
        game="magic",
        name_en=name_en,
        name_pt=name_pt,
        set_code=set_code or f"s{_counter['n']}",
        collector_number=str(_counter["n"]),
        type_line=type_line,
        color_identity=color_identity,
        image_uri=image_uri,
        rarity=rarity,
        mana_cost="{1}",
    )


def _add(repo: Repository, *rows) -> list[int]:
    with Session(repo.engine) as session:
        session.add_all(rows)
        session.commit()
        return [r.id for r in rows if isinstance(r, CardRow)]


def _legality(card_id: int, status: str, fmt: str = "commander") -> CardLegalityRow:
    return CardLegalityRow(card_id=card_id, format=fmt, status=status)


def _fake_commander_rows() -> list[CardRow]:
    return [
        _card(
            "Atraxa, Praetors' Voice",
            name_pt="Atraxa, Voz dos Pretores",
            color_identity="WUBG",
        ),
        _card("Atraxa, Grand Unifier", type_line="Legendary Creature — Phyrexian Angel"),
        _card("Krenko, Mob Boss", color_identity="R"),
        _card("Delver of Secrets // Insectile Aberration", type_line="Creature — Human"),
        _card(
            "Esika, Queen of the Wild // The Prismatic Bridge",
            type_line="Legendary Creature — Human // Legendary Enchantment",
            color_identity="G",
        ),
        _card("Mystery Commander", type_line=None),
    ]


# ---------------------------------------------------------------------------
# is_commander_eligible
# ---------------------------------------------------------------------------


class TestIsCommanderEligible:
    @pytest.mark.parametrize(
        "type_line",
        [
            "Legendary Creature — Human",
            "Legendary Artifact Creature — Golem",
            "Legendary Creature — Human // Legendary Enchantment",
        ],
    )
    def test_eligible(self, type_line):
        assert is_commander_eligible(type_line) is True

    @pytest.mark.parametrize(
        "type_line",
        [None, "", "Creature — Elf", "Legendary Enchantment", "Legendary Planeswalker — Jace"],
    )
    def test_not_eligible(self, type_line):
        assert is_commander_eligible(type_line) is False


class TestEscapeLike:
    def test_escapes_wildcards_and_backslash(self):
        assert _escape_like("50%_a\\b") == "50\\%\\_a\\\\b"


# ---------------------------------------------------------------------------
# get_commander_candidates
# ---------------------------------------------------------------------------


class TestCommanderSearch:
    def test_no_legality_rows_still_finds_atraxa(self, repo):
        _add(repo, *_fake_commander_rows())
        names = [c["name_en"] for c in get_commander_candidates(repo, search="atraxa")]
        assert "Atraxa, Praetors' Voice" in names

    def test_en_partial(self, repo):
        _add(repo, *_fake_commander_rows())
        names = [c["name_en"] for c in get_commander_candidates(repo, search="atra")]
        assert set(names) == {"Atraxa, Praetors' Voice", "Atraxa, Grand Unifier"}

    def test_pt_partial_matches_name_pt(self, repo):
        _add(repo, *_fake_commander_rows())
        result = get_commander_candidates(repo, search="voz dos")
        assert len(result) == 1
        assert result[0]["name_en"] == "Atraxa, Praetors' Voice"
        assert result[0]["name_pt"] == "Atraxa, Voz dos Pretores"

    def test_search_is_stripped(self, repo):
        _add(repo, *_fake_commander_rows())
        assert len(get_commander_candidates(repo, search="  krenko  ")) == 1

    def test_exact_match_sorted_first(self, repo):
        _add(
            repo,
            _card("Aaa Krenko Fan"),
            _card("Krenko Junior"),
            _card("Krenko"),
        )
        names = [c["name_en"] for c in get_commander_candidates(repo, search="krenko")]
        assert names == ["Krenko", "Krenko Junior", "Aaa Krenko Fan"]

    def test_exact_pt_match_sorted_first(self, repo):
        _add(repo, _card("Aaa Other Guardian"), _card("Zzz Guard", name_pt="Guardiao"))
        names = [c["name_en"] for c in get_commander_candidates(repo, search="guardiao")]
        assert names[0] == "Zzz Guard"

    def test_banned_and_not_legal_excluded_legal_included(self, repo):
        banned, not_legal, legal, _norow = _add(
            repo,
            _card("Golos, Tireless Pilgrim"),
            _card("Golos Not Legal"),
            _card("Golos Legal"),
            _card("Golos No Row"),
        )
        _add(
            repo,
            _legality(banned, "banned"),
            _legality(not_legal, "not_legal"),
            _legality(legal, "legal"),
        )
        names = {c["name_en"] for c in get_commander_candidates(repo, search="golos")}
        assert names == {"Golos Legal", "Golos No Row"}

    def test_other_format_ban_does_not_exclude(self, repo):
        (cid,) = _add(repo, _card("Krenko, Mob Boss"))
        _add(repo, _legality(cid, "banned", fmt="modern"))
        assert len(get_commander_candidates(repo, search="krenko")) == 1

    def test_duplicate_printings_deduped_prefers_image(self, repo):
        ids = _add(
            repo,
            _card("Krenko, Mob Boss", image_uri=None),
            _card("Krenko, Mob Boss", image_uri="https://img/a.jpg"),
            _card("Krenko, Mob Boss", image_uri=None),
            _card("krenko, mob boss", image_uri=None),
            _card("Krenko, Mob Boss", image_uri=None),
        )
        result = get_commander_candidates(repo, search="krenko")
        assert len(result) == 1
        assert result[0]["card_id"] == ids[1]

    def test_dedupe_prefers_higher_id_when_all_have_images(self, repo):
        ids = _add(repo, _card("Krenko, Mob Boss"), _card("Krenko, Mob Boss"))
        result = get_commander_candidates(repo, search="krenko")
        assert [c["card_id"] for c in result] == [max(ids)]

    def test_null_type_line_excluded_dfc_included(self, repo):
        _add(repo, *_fake_commander_rows())
        names = {c["name_en"] for c in get_commander_candidates(repo)}
        assert "Mystery Commander" not in names
        assert "Delver of Secrets // Insectile Aberration" not in names
        assert "Esika, Queen of the Wild // The Prismatic Bridge" in names

    @pytest.mark.parametrize("search", ["%%", "__", "%_"])
    def test_wildcards_are_escaped(self, repo, search):
        _add(repo, *_fake_commander_rows())
        assert get_commander_candidates(repo, search=search) == []

    def test_literal_percent_matches(self, repo):
        _add(repo, _card("100% Commander"), _card("Other Commander"))
        names = [c["name_en"] for c in get_commander_candidates(repo, search="0%")]
        assert names == ["100% Commander"]

    @pytest.mark.parametrize("search", ["a", " a ", "%", "_"])
    def test_one_char_search_returns_empty(self, repo, search):
        _add(repo, *_fake_commander_rows())
        assert get_commander_candidates(repo, search=search) == []

    def test_empty_search_returns_all_eligible(self, repo):
        _add(repo, *_fake_commander_rows())
        assert len(get_commander_candidates(repo, search="   ")) == 4

    def test_limit_one(self, repo):
        _add(repo, *_fake_commander_rows())
        assert len(get_commander_candidates(repo, limit=1)) == 1

    def test_color_filter_applied_before_limit(self, repo):
        _add(
            repo,
            _card("Aaa Red One", color_identity="R"),
            _card("Aab Red Two", color_identity="R"),
            _card("Bbb Azorius", color_identity="WU"),
            _card("Ccc White", color_identity="W"),
            _card("Ddd Blue", color_identity="U"),
        )
        result = get_commander_candidates(repo, colors=["W", "U"], limit=2)
        assert [c["name_en"] for c in result] == ["Bbb Azorius", "Ccc White"]

    @pytest.mark.parametrize("ci", ["", None, "C"])
    def test_colorless_commander_matches_color_filter(self, repo, ci):
        _add(repo, _card("Karn Commander", color_identity=ci))
        result = get_commander_candidates(repo, colors=["G"], search="karn")
        assert len(result) == 1

    def test_fetch_cap_500(self, repo):
        _add(repo, *[_card(f"Commander {i:04d}") for i in range(600)])
        # 50 * 10 = 500 fetched; all distinct → sliced to limit
        assert len(get_commander_candidates(repo, limit=50)) == 50

    def test_fetch_cap_limits_color_matches(self, repo):
        # 500 red commanders sort first; the blue one is beyond the 500-row cap
        _add(repo, *[_card(f"Aaa Red {i:04d}", color_identity="R") for i in range(500)])
        _add(repo, _card("Zzz Blue", color_identity="U"))
        assert get_commander_candidates(repo, colors=["U"], limit=50) == []
        assert len(get_commander_candidates(repo, colors=["U"], limit=50, search="zzz")) == 1

    def test_result_shape(self, repo):
        _add(repo, *_fake_commander_rows())
        result = get_commander_candidates(repo, search="krenko")
        assert set(result[0]) == {
            "card_id",
            "name_en",
            "name_pt",
            "set_code",
            "collector_number",
            "color_identity",
            "mana_cost",
            "type_line",
            "rarity",
            "image_uri",
        }


# ---------------------------------------------------------------------------
# generate_deck — soft legality + real prices
# ---------------------------------------------------------------------------


def _seed_pool(repo: Repository, n: int = 40) -> list[int]:
    rows = []
    for i in range(n):
        rows.append(
            _card(f"White Creature {i:03d}", type_line="Creature — Soldier", color_identity="W")
        )
        rows.append(_card(f"White Instant {i:03d}", type_line="Instant", color_identity="W"))
    return _add(repo, *rows)


def _price(repo: Repository, card_ids: list[int], value: str) -> None:
    _add(
        repo,
        *[
            PriceObservationRow(
                source="liga",
                external_id=f"liga_{cid}",
                observed_at=date(2026, 9, 1),
                median_price=Decimal(value),
            )
            for cid in card_ids
        ],
    )


class TestGenerateDeckSoftLegality:
    def test_non_land_cards_without_legality_rows(self, repo):
        _seed_pool(repo)
        deck = generate_deck(repo, DeckBuildParams(format_name="modern", colors=["W"]))
        assert deck.nonland_count > 0

    def test_banned_card_excluded(self, repo):
        ids = _seed_pool(repo, n=5)
        _add(repo, _legality(ids[0], "banned", fmt="modern"))
        deck = generate_deck(repo, DeckBuildParams(format_name="modern", colors=["W"]))
        assert ids[0] not in {c["card_id"] for c in deck.cards}
        assert deck.nonland_count > 0

    def test_prices_fill_total_value(self, repo):
        ids = _seed_pool(repo, n=10)
        _price(repo, ids, "2.50")
        deck = generate_deck(repo, DeckBuildParams(format_name="modern", colors=["W"]))
        assert deck.total_value is not None and deck.total_value > 0
        priced = [c for c in deck.cards if c["card_id"] in set(ids)]
        assert priced and all(c["price"] == 2.5 for c in priced)

    def test_no_prices_total_value_none(self, repo):
        _seed_pool(repo, n=5)
        deck = generate_deck(repo, DeckBuildParams(format_name="modern", colors=["W"]))
        assert deck.total_value is None

    def test_tiny_budget_only_unpriced_cards(self, repo):
        ids = _seed_pool(repo, n=10)
        priced_ids = set(ids[::2])
        _price(repo, list(priced_ids), "5.00")
        deck = generate_deck(
            repo,
            DeckBuildParams(format_name="modern", colors=["W"], budget_limit=Decimal("0.01")),
        )
        chosen = {c["card_id"] for c in deck.cards if c["card_id"] is not None}
        assert chosen and not (chosen & priced_ids)
        assert deck.warnings

    def test_commander_price_filled(self, repo):
        (cmd_id,) = _add(repo, _card("Cmd Leader", color_identity="W"))
        _seed_pool(repo, n=5)
        _price(repo, [cmd_id], "10.00")
        deck = generate_deck(
            repo, DeckBuildParams(format_name="commander", commander_card_id=cmd_id)
        )
        assert deck.cards[0]["card_id"] == cmd_id
        assert deck.cards[0]["price"] == 10.0
        assert deck.total_value is not None and deck.total_value >= Decimal("10")


# ---------------------------------------------------------------------------
# F171: Bare cards created by price collector (NULL metadata)
# ---------------------------------------------------------------------------


class TestCommanderSearchBareCards:
    """Reproduce F171: cards created by price collector have NULL type_line.

    The price collector's ``upsert_card`` creates CardRow with only
    game/name_en/set_code/collector_number. All metadata fields
    (type_line, rarity, color_identity, mana_cost, image_uri) are NULL.
    Commander search requires type_line to contain "Legendary" and "Creature",
    so these bare cards are correctly excluded.
    """

    def test_bare_card_not_found_by_commander_search(self, repo):
        """A card with type_line=NULL is correctly excluded from commander search."""
        _add(
            repo,
            CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="cmm",
                collector_number="999",
                # No type_line, rarity, color_identity -- simulates upsert_card
            ),
        )
        result = get_commander_candidates(repo, search="atraxa")
        assert result == []

    def test_enriched_card_found_by_commander_search(self, repo):
        """After enrichment (simulating catalog seed fix), the card appears."""
        with Session(repo.engine) as session:
            card = CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="cmm",
                collector_number="999",
            )
            session.add(card)
            session.commit()
            card_id = card.id

            # Simulate enrichment (what T01 fix does via on_conflict_do_update)
            session.execute(
                update(CardRow)
                .where(CardRow.id == card_id)
                .values(
                    type_line="Legendary Creature — Phyrexian Angel Horror",
                    color_identity="WUBG",
                    rarity="mythic",
                )
            )
            session.commit()

        result = get_commander_candidates(repo, search="atraxa")
        assert len(result) == 1
        assert result[0]["name_en"] == "Atraxa, Praetors' Voice"
        assert result[0]["type_line"] == "Legendary Creature — Phyrexian Angel Horror"

    def test_full_pipeline_bare_card_to_commander_search(self, repo):
        """End-to-end: price collect -> catalog seed enrichment -> search works.

        1. Insert bare card (simulating price collector)
        2. Insert same card with full metadata (simulating catalog seed with fix)
        3. Commander search finds the card
        """
        # Step 1: price collector creates bare card
        _add(
            repo,
            CardRow(
                game="magic",
                name_en="Krenko, Mob Boss",
                set_code="jmp",
                collector_number="339",
            ),
        )
        # Verify it is NOT found
        assert get_commander_candidates(repo, search="krenko") == []

        # Step 2: simulate catalog seed enrichment (UPDATE in place)
        with Session(repo.engine) as session:
            session.execute(
                update(CardRow)
                .where(
                    CardRow.game == "magic",
                    CardRow.set_code == "jmp",
                    CardRow.collector_number == "339",
                )
                .values(
                    type_line="Legendary Creature — Goblin Warrior",
                    color_identity="R",
                    rarity="rare",
                    mana_cost="{2}{R}{R}",
                    image_uri="https://cards.scryfall.io/large/jmp/339.jpg",
                )
            )
            session.commit()

        # Step 3: commander search now finds it
        result = get_commander_candidates(repo, search="krenko")
        assert len(result) == 1
        assert result[0]["name_en"] == "Krenko, Mob Boss"
        assert result[0]["color_identity"] == "R"

    def test_mixed_bare_and_enriched_cards(self, repo):
        """Only enriched cards appear; bare siblings are excluded."""
        _add(
            repo,
            # Bare card (price collector)
            CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="2xm",
                collector_number="190",
            ),
            # Enriched card (catalog seed)
            CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="cmm",
                collector_number="1",
                type_line="Legendary Creature — Phyrexian Angel Horror",
                color_identity="WUBG",
                rarity="mythic",
                mana_cost="{G}{W}{U}{B}",
                image_uri="https://img/cmm/1.jpg",
            ),
        )

        result = get_commander_candidates(repo, search="atraxa")
        # Deduped by name — only one result, from the enriched printing
        assert len(result) == 1
        assert result[0]["name_en"] == "Atraxa, Praetors' Voice"
        assert result[0]["set_code"] == "cmm"

    def test_bare_card_with_partial_metadata_still_excluded(self, repo):
        """A card with rarity set but type_line=NULL is still excluded."""
        _add(
            repo,
            CardRow(
                game="magic",
                name_en="Atraxa, Praetors' Voice",
                set_code="cmm",
                collector_number="999",
                rarity="mythic",
                color_identity="WUBG",
                # type_line is still NULL
            ),
        )
        result = get_commander_candidates(repo, search="atraxa")
        assert result == []
