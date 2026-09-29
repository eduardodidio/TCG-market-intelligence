"""Tests for the diagnose-prices CLI command."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.cli.main import cli
from src.database.models import (
    Base,
    CardRow,
    PriceObservationRow,
    SourceCardRow,
)


def _make_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def _seed_card(session: Session, card_id: int, name: str) -> CardRow:
    card = CardRow(
        id=card_id,
        game="mtg",
        name_en=name,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(card)
    session.flush()
    return card


def _seed_source_card(
    session: Session, card_id: int, external_id: str, source: str = "liga"
) -> SourceCardRow:
    sc = SourceCardRow(
        source=source,
        external_id=external_id,
        card_id=card_id,
        url=f"https://example.com/{external_id}",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    session.add(sc)
    session.flush()
    return sc


def _seed_price(
    session: Session,
    external_id: str,
    source: str,
    median_price: Decimal,
    observed_at: date | None = None,
) -> PriceObservationRow:
    obs = PriceObservationRow(
        source=source,
        external_id=external_id,
        observed_at=observed_at or date(2026, 9, 1),
        median_price=median_price,
        currency="BRL",
        created_at=datetime.now(),
    )
    session.add(obs)
    session.flush()
    return obs


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDiagnosePricesPenny:
    """Query 1: penny prices (median_price < 0.50)."""

    def test_penny_prices_found(self, monkeypatch):
        engine = _make_engine()
        with Session(engine) as s:
            _seed_card(s, 1, "Cheap Token")
            _seed_source_card(s, 1, "liga_100", "liga")
            _seed_price(s, "liga_100", "liga", Decimal("0.10"))
            s.commit()

        monkeypatch.setattr(
            "src.database.repository.Repository.__init__",
            lambda self, *a, **kw: setattr(self, "engine", engine),
        )
        result = CliRunner().invoke(cli, ["diagnose-prices", "--db", "sqlite:///:memory:"])
        assert result.exit_code == 0
        assert "Cheap Token" in result.output
        assert "0.10" in result.output
        assert "Penny Prices" in result.output

    def test_no_penny_prices(self, monkeypatch):
        engine = _make_engine()
        with Session(engine) as s:
            _seed_card(s, 1, "Normal Card")
            _seed_source_card(s, 1, "liga_200", "liga")
            _seed_price(s, "liga_200", "liga", Decimal("5.00"))
            s.commit()

        monkeypatch.setattr(
            "src.database.repository.Repository.__init__",
            lambda self, *a, **kw: setattr(self, "engine", engine),
        )
        result = CliRunner().invoke(cli, ["diagnose-prices", "--db", "sqlite:///:memory:"])
        assert result.exit_code == 0
        assert "No penny prices found" in result.output


class TestDiagnosePricesExtremeRatios:
    """Query 2: extreme ratios (max/min > 20x)."""

    def test_extreme_ratio_found(self, monkeypatch):
        engine = _make_engine()
        with Session(engine) as s:
            _seed_card(s, 1, "Volatile Card")
            _seed_source_card(s, 1, "liga_300", "liga")
            _seed_price(s, "liga_300", "liga", Decimal("0.50"), date(2026, 1, 1))
            _seed_price(s, "liga_300", "liga", Decimal("100.00"), date(2026, 2, 1))
            s.commit()

        monkeypatch.setattr(
            "src.database.repository.Repository.__init__",
            lambda self, *a, **kw: setattr(self, "engine", engine),
        )
        result = CliRunner().invoke(cli, ["diagnose-prices", "--db", "sqlite:///:memory:"])
        assert result.exit_code == 0
        assert "Volatile Card" in result.output
        assert "Extreme Price Ratios" in result.output
        assert "200.0x" in result.output

    def test_no_extreme_ratios(self, monkeypatch):
        engine = _make_engine()
        with Session(engine) as s:
            _seed_card(s, 1, "Stable Card")
            _seed_source_card(s, 1, "liga_400", "liga")
            _seed_price(s, "liga_400", "liga", Decimal("10.00"), date(2026, 1, 1))
            _seed_price(s, "liga_400", "liga", Decimal("12.00"), date(2026, 2, 1))
            s.commit()

        monkeypatch.setattr(
            "src.database.repository.Repository.__init__",
            lambda self, *a, **kw: setattr(self, "engine", engine),
        )
        result = CliRunner().invoke(cli, ["diagnose-prices", "--db", "sqlite:///:memory:"])
        assert result.exit_code == 0
        assert "No extreme ratios found" in result.output


class TestDiagnosePricesLimit:
    """--limit option restricts output."""

    def test_limit_respected(self, monkeypatch):
        engine = _make_engine()
        with Session(engine) as s:
            for i in range(1, 11):
                _seed_card(s, i, f"Penny Card {i}")
                _seed_source_card(s, i, f"liga_{500 + i}", "liga")
                _seed_price(
                    s,
                    f"liga_{500 + i}",
                    "liga",
                    Decimal("0.01") * i,
                    date(2026, 1, i),
                )
            s.commit()

        monkeypatch.setattr(
            "src.database.repository.Repository.__init__",
            lambda self, *a, **kw: setattr(self, "engine", engine),
        )
        result = CliRunner().invoke(
            cli, ["diagnose-prices", "--db", "sqlite:///:memory:", "--limit", "5"]
        )
        assert result.exit_code == 0
        assert "Total: 5 penny price(s)" in result.output


class TestDiagnosePricesReadOnly:
    """Command must not mutate the database."""

    def test_no_mutations(self, monkeypatch):
        engine = _make_engine()
        with Session(engine) as s:
            _seed_card(s, 1, "Test Card")
            _seed_source_card(s, 1, "liga_900", "liga")
            _seed_price(s, "liga_900", "liga", Decimal("0.25"))
            s.commit()

        with Session(engine) as s:
            count_before = s.query(PriceObservationRow).count()
            cards_before = s.query(CardRow).count()

        monkeypatch.setattr(
            "src.database.repository.Repository.__init__",
            lambda self, *a, **kw: setattr(self, "engine", engine),
        )
        result = CliRunner().invoke(cli, ["diagnose-prices", "--db", "sqlite:///:memory:"])
        assert result.exit_code == 0

        with Session(engine) as s:
            count_after = s.query(PriceObservationRow).count()
            cards_after = s.query(CardRow).count()

        assert count_before == count_after
        assert cards_before == cards_after


class TestDiagnosePricesCleanData:
    """With only clean data, both sections should report nothing."""

    def test_clean_data(self, monkeypatch):
        engine = _make_engine()
        with Session(engine) as s:
            _seed_card(s, 1, "Good Card")
            _seed_source_card(s, 1, "liga_700", "liga")
            _seed_price(s, "liga_700", "liga", Decimal("5.00"), date(2026, 1, 1))
            _seed_price(s, "liga_700", "liga", Decimal("6.00"), date(2026, 2, 1))
            s.commit()

        monkeypatch.setattr(
            "src.database.repository.Repository.__init__",
            lambda self, *a, **kw: setattr(self, "engine", engine),
        )
        result = CliRunner().invoke(cli, ["diagnose-prices", "--db", "sqlite:///:memory:"])
        assert result.exit_code == 0
        assert "No penny prices found" in result.output
        assert "No extreme ratios found" in result.output
