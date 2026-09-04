"""Tests for src/catalog/seeder.py — catalog seeder batch upsert."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.catalog.scryfall import CatalogCard
from src.catalog.seeder import SeedResult, _process_card_batch, seed_catalog
from src.database.models import Base, CardRow, SourceCardRow


def _make_catalog_card(
    name: str = "Lightning Bolt",
    set_code: str = "lea",
    collector_number: str = "161",
    rarity: str = "C",
    color_identity: str = "R",
    mana_cost: str = "{R}",
    type_line: str = "Instant",
    image_uri: str = "https://example.com/bolt.jpg",
    name_pt: str | None = None,
) -> CatalogCard:
    return CatalogCard(
        name_en=name,
        set_code=set_code,
        collector_number=collector_number,
        rarity=rarity,
        color_identity=color_identity,
        mana_cost=mana_cost,
        type_line=type_line,
        image_uri=image_uri,
        name_pt=name_pt,
    )


def _make_scryfall_json(cards: list[CatalogCard]) -> str:
    """Create a minimal Scryfall-style JSON array from CatalogCard objects."""
    raw_cards = []
    for c in cards:
        raw_cards.append(
            {
                "name": c.name_en,
                "set": c.set_code,
                "collector_number": c.collector_number,
                "rarity": {"C": "common", "U": "uncommon", "R": "rare", "M": "mythic"}.get(
                    c.rarity, "common"
                ),
                "color_identity": list(c.color_identity) if c.color_identity else [],
                "mana_cost": c.mana_cost,
                "type_line": c.type_line,
                "image_uris": {"normal": c.image_uri} if c.image_uri else {},
                "games": ["paper"],
                "lang": "en",
            }
        )
    return json.dumps(raw_cards)


@pytest.fixture()
def db_url(tmp_path: Path) -> str:
    url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return url


@pytest.fixture()
def sample_cards() -> list[CatalogCard]:
    return [
        _make_catalog_card("Lightning Bolt", "lea", "161"),
        _make_catalog_card("Sol Ring", "lea", "268", rarity="U", color_identity=""),
        _make_catalog_card("Dark Ritual", "lea", "95", color_identity="B"),
        _make_catalog_card("Counterspell", "lea", "54", color_identity="U"),
        _make_catalog_card("Swords to Plowshares", "lea", "241", color_identity="W"),
    ]


@pytest.fixture()
def bulk_json_path(tmp_path: Path, sample_cards: list[CatalogCard]) -> Path:
    path = tmp_path / "bulk.json"
    path.write_text(_make_scryfall_json(sample_cards))
    return path


class TestSeedResult:
    def test_default_values(self):
        r = SeedResult()
        assert r.cards_inserted == 0
        assert r.cards_updated == 0
        assert r.cards_skipped == 0
        assert r.source_cards_created == 0
        assert r.errors == []
        assert r.elapsed_seconds == 0.0

    def test_errors_not_shared(self):
        r1 = SeedResult()
        r2 = SeedResult()
        r1.errors.append("oops")
        assert r2.errors == []


class TestProcessCardBatch:
    def test_inserts_cards_and_source_cards(self, db_url: str, sample_cards: list[CatalogCard]):
        engine = create_engine(db_url)
        result = SeedResult()

        with Session(engine) as session:
            _process_card_batch(session, sample_cards, result)
            session.commit()

        assert result.cards_inserted == 5
        assert result.cards_skipped == 0
        assert result.source_cards_created == 5

        with Session(engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 5
            source_cards = session.execute(select(SourceCardRow)).scalars().all()
            assert len(source_cards) == 5

        engine.dispose()

    def test_idempotent_no_duplicates(self, db_url: str, sample_cards: list[CatalogCard]):
        engine = create_engine(db_url)

        # First insert
        result1 = SeedResult()
        with Session(engine) as session:
            _process_card_batch(session, sample_cards, result1)
            session.commit()

        # Second insert — same data
        result2 = SeedResult()
        with Session(engine) as session:
            _process_card_batch(session, sample_cards, result2)
            session.commit()

        assert result2.cards_inserted == 0
        assert result2.cards_skipped == 5
        assert result2.source_cards_created == 0

        # DB still has exactly 5 of each
        with Session(engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 5
            source_cards = session.execute(select(SourceCardRow)).scalars().all()
            assert len(source_cards) == 5

        engine.dispose()

    def test_source_card_fields(self, db_url: str):
        engine = create_engine(db_url)
        card = _make_catalog_card("Lightning Bolt", "lea", "161")
        result = SeedResult()

        with Session(engine) as session:
            _process_card_batch(session, [card], result)
            session.commit()

        with Session(engine) as session:
            sc = session.execute(select(SourceCardRow)).scalar_one()
            assert sc.source == "liga"
            assert sc.external_id == "liga_catalog_lea_161"
            assert "Lightning+Bolt" in sc.url
            assert sc.name_en == "Lightning Bolt"
            assert sc.set_code == "lea"
            assert sc.collector_number == "161"
            assert sc.card_id is not None

        engine.dispose()

    def test_card_fields_stored(self, db_url: str):
        engine = create_engine(db_url)
        card = _make_catalog_card(
            "Lightning Bolt",
            "lea",
            "161",
            rarity="C",
            color_identity="R",
            mana_cost="{R}",
            type_line="Instant",
            image_uri="https://example.com/bolt.jpg",
        )
        result = SeedResult()

        with Session(engine) as session:
            _process_card_batch(session, [card], result)
            session.commit()

        with Session(engine) as session:
            c = session.execute(select(CardRow)).scalar_one()
            assert c.game == "magic"
            assert c.name_en == "Lightning Bolt"
            assert c.set_code == "lea"
            assert c.collector_number == "161"
            assert c.rarity == "C"
            assert c.color_identity == "R"
            assert c.mana_cost == "{R}"
            assert c.type_line == "Instant"
            assert c.image_uri == "https://example.com/bolt.jpg"

        engine.dispose()


class TestSeedCatalog:
    def test_full_seed(self, db_url: str, bulk_json_path: Path):
        result = seed_catalog(db_url, bulk_json_path, batch_size=3)

        assert result.cards_inserted == 5
        assert result.cards_skipped == 0
        assert result.source_cards_created == 5
        assert result.errors == []
        assert result.elapsed_seconds > 0

        engine = create_engine(db_url)
        with Session(engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 5
            source_cards = session.execute(select(SourceCardRow)).scalars().all()
            assert len(source_cards) == 5
        engine.dispose()

    def test_idempotent_seed_twice(self, db_url: str, bulk_json_path: Path):
        result1 = seed_catalog(db_url, bulk_json_path, batch_size=10)
        result2 = seed_catalog(db_url, bulk_json_path, batch_size=10)

        assert result1.cards_inserted == 5
        assert result2.cards_inserted == 0
        assert result2.cards_skipped == 5
        assert result2.source_cards_created == 0

        engine = create_engine(db_url)
        with Session(engine) as session:
            cards = session.execute(select(CardRow)).scalars().all()
            assert len(cards) == 5
        engine.dispose()

    def test_batch_commit_not_per_card(self, db_url: str, bulk_json_path: Path):
        """Verify that commits happen per-batch, not per-card.

        With batch_size=3 and 5 cards, we expect exactly 2 batches
        (3 + 2), meaning 2 commits total.
        """
        commit_count = 0

        # We patch Session.commit to count calls
        original_commit = Session.commit

        def counting_commit(self):
            nonlocal commit_count
            commit_count += 1
            original_commit(self)

        with patch.object(Session, "commit", counting_commit):
            seed_catalog(db_url, bulk_json_path, batch_size=3)

        # 2 batches = 2 commits (batch of 3 + batch of 2)
        assert commit_count == 2

    def test_seed_result_counts(self, db_url: str, bulk_json_path: Path):
        result = seed_catalog(db_url, bulk_json_path, batch_size=500)

        assert isinstance(result, SeedResult)
        assert result.cards_inserted == 5
        assert result.cards_updated == 0
        assert result.cards_skipped == 0
        assert result.source_cards_created == 5
        assert result.errors == []
        assert isinstance(result.elapsed_seconds, float)
        assert result.elapsed_seconds >= 0

    def test_same_name_different_sets(self, db_url: str, tmp_path: Path):
        """Cards with the same name but different sets create separate entries."""
        cards = [
            _make_catalog_card("Lightning Bolt", "lea", "161"),
            _make_catalog_card("Lightning Bolt", "m10", "146"),
            _make_catalog_card("Lightning Bolt", "m11", "149"),
        ]
        path = tmp_path / "multi_set.json"
        path.write_text(_make_scryfall_json(cards))

        result = seed_catalog(db_url, path, batch_size=10)

        assert result.cards_inserted == 3
        assert result.source_cards_created == 3

        engine = create_engine(db_url)
        with Session(engine) as session:
            source_cards = session.execute(select(SourceCardRow)).scalars().all()
            ext_ids = {sc.external_id for sc in source_cards}
            assert ext_ids == {
                "liga_catalog_lea_161",
                "liga_catalog_m10_146",
                "liga_catalog_m11_149",
            }
            # All share the same URL (same card name)
            urls = {sc.url for sc in source_cards}
            assert len(urls) == 1  # same name -> same URL
        engine.dispose()

    def test_empty_bulk_file(self, db_url: str, tmp_path: Path):
        path = tmp_path / "empty.json"
        path.write_text("[]")

        result = seed_catalog(db_url, path, batch_size=10)

        assert result.cards_inserted == 0
        assert result.source_cards_created == 0
        assert result.errors == []

    def test_single_card(self, db_url: str, tmp_path: Path):
        cards = [_make_catalog_card("Sol Ring", "cmd", "190")]
        path = tmp_path / "single.json"
        path.write_text(_make_scryfall_json(cards))

        result = seed_catalog(db_url, path, batch_size=500)

        assert result.cards_inserted == 1
        assert result.source_cards_created == 1
