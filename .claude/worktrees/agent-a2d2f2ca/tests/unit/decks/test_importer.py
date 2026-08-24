"""Tests for deck import orchestrator."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base, CardRow
from src.decks.importer import import_deck, import_deck_from_csv, import_deck_from_text


@pytest.fixture
def engine(tmp_path):
    db_path = tmp_path / "test.db"
    eng = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(eng)
    return eng


def _seed_cards(engine):
    """Add some canonical cards for linking tests."""
    with Session(engine) as session:
        cards = [
            CardRow(game="magic", name_en="Lightning Bolt", set_code="lea", collector_number="161"),
            CardRow(game="magic", name_en="Counterspell", set_code="2ed", collector_number="55"),
        ]
        session.add_all(cards)
        session.commit()


class TestImportDeck:
    def test_basic_import(self, engine):
        result = import_deck(
            engine,
            user_id="user1",
            name="My Deck",
            cards=[
                {"name_en": "Lightning Bolt", "quantity": 4},
                {"name_en": "Mountain", "quantity": 20},
            ],
        )
        assert result["deck_id"] is not None
        assert result["name"] == "My Deck"
        assert result["cards_imported"] == 2
        assert result["cards_linked"] == 0

    def test_import_with_linking(self, engine):
        _seed_cards(engine)
        result = import_deck(
            engine,
            user_id="user1",
            name="Linked Deck",
            cards=[
                {
                    "name_en": "Lightning Bolt",
                    "set_code": "lea",
                    "collector_number": "161",
                    "quantity": 4,
                },
                {"name_en": "Unknown Card", "quantity": 1},
            ],
        )
        assert result["cards_linked"] == 1

    def test_import_with_name_linking(self, engine):
        _seed_cards(engine)
        result = import_deck(
            engine,
            user_id="user1",
            name="Name Link",
            cards=[{"name_en": "Counterspell", "quantity": 2}],
        )
        assert result["cards_linked"] == 1

    def test_import_empty(self, engine):
        result = import_deck(engine, user_id="user1", name="Empty", cards=[])
        assert result["cards_imported"] == 0
        assert result["cards_linked"] == 0

    def test_import_with_description(self, engine):
        result = import_deck(
            engine,
            user_id="user1",
            name="Burn",
            cards=[{"name_en": "Bolt", "quantity": 4}],
            description="Fast red deck",
        )
        assert result["name"] == "Burn"


class TestImportDeckFromText:
    def test_basic(self, engine):
        content = "4 Lightning Bolt\n20 Mountain"
        result = import_deck_from_text(engine, "user1", "Text Deck", content)
        assert result["cards_imported"] == 2

    def test_with_set_codes(self, engine):
        _seed_cards(engine)
        content = "4 Lightning Bolt [LEA:161]"
        result = import_deck_from_text(engine, "user1", "Set Deck", content)
        assert result["cards_imported"] == 1
        assert result["cards_linked"] == 1

    def test_with_comments(self, engine):
        content = "# Main\n4 Bolt\n// Side\n2 Island"
        result = import_deck_from_text(engine, "user1", "Comments", content)
        assert result["cards_imported"] == 2


class TestImportDeckFromCsv:
    def test_basic_csv(self, engine):
        csv_content = (
            "Card (EN),Edicao (Sigla),Card #,Quantidade\n"
            "Lightning Bolt,lea,161,4\n"
            "Mountain,lea,262,20\n"
        )
        result = import_deck_from_csv(engine, "user1", "CSV Deck", csv_content)
        assert result["cards_imported"] == 2

    def test_csv_linking(self, engine):
        _seed_cards(engine)
        csv_content = "Card (EN),Edicao (Sigla),Card #,Quantidade\n" "Lightning Bolt,lea,161,4\n"
        result = import_deck_from_csv(engine, "user1", "Linked CSV", csv_content)
        assert result["cards_linked"] == 1

    def test_csv_skip_empty_name(self, engine):
        csv_content = (
            "Card (EN),Edicao (Sigla),Card #,Quantidade\n"
            ",lea,161,4\n"
            "Lightning Bolt,lea,161,4\n"
        )
        result = import_deck_from_csv(engine, "user1", "Skip Empty", csv_content)
        assert result["cards_imported"] == 1

    def test_csv_default_quantity(self, engine):
        csv_content = "Card (EN),Edicao (Sigla),Card #,Quantidade\n" "Lightning Bolt,lea,161,\n"
        result = import_deck_from_csv(engine, "user1", "Default Qty", csv_content)
        assert result["cards_imported"] == 1
