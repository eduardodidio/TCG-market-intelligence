"""Tests for ExchangeRateRow model (T01)."""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.database.models import Base, ExchangeRateRow


class TestExchangeRateRow:
    def setup_method(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def test_table_creation(self):
        """exchange_rates table exists after metadata create_all."""
        inspector = self.engine.dialect.get_columns(self.engine.connect(), "exchange_rates")
        assert len(inspector) > 0

    def test_instantiation(self):
        """Can create an ExchangeRateRow with all fields."""
        row = ExchangeRateRow(
            rate_date=date(2026, 8, 20),
            from_currency="USD",
            to_currency="BRL",
            rate=Decimal("5.123456"),
            source="bcb_ptax",
        )
        assert row.rate_date == date(2026, 8, 20)
        assert row.from_currency == "USD"
        assert row.to_currency == "BRL"
        assert row.rate == Decimal("5.123456")
        assert row.source == "bcb_ptax"

    def test_insert_and_query(self):
        """Can insert and query an exchange rate row."""
        with Session(self.engine) as session:
            row = ExchangeRateRow(
                rate_date=date(2026, 8, 20),
                from_currency="USD",
                to_currency="BRL",
                rate=Decimal("5.250000"),
                source="bcb_ptax",
            )
            session.add(row)
            session.commit()

            fetched = session.query(ExchangeRateRow).first()
            assert fetched is not None
            assert fetched.rate_date == date(2026, 8, 20)
            assert fetched.rate == Decimal("5.250000")
            assert fetched.id is not None

    def test_unique_rate_date_constraint(self):
        """Duplicate rate_date raises IntegrityError."""
        import pytest
        from sqlalchemy.exc import IntegrityError

        with Session(self.engine) as session:
            row1 = ExchangeRateRow(
                rate_date=date(2026, 8, 20),
                rate=Decimal("5.25"),
            )
            session.add(row1)
            session.commit()

        with pytest.raises(IntegrityError):
            with Session(self.engine) as session:
                row2 = ExchangeRateRow(
                    rate_date=date(2026, 8, 20),
                    rate=Decimal("5.30"),
                )
                session.add(row2)
                session.commit()

    def test_defaults_after_insert(self):
        """Default values for from_currency, to_currency, source are applied on INSERT."""
        with Session(self.engine) as session:
            row = ExchangeRateRow(
                rate_date=date(2026, 8, 20),
                rate=Decimal("5.25"),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            assert row.from_currency == "USD"
            assert row.to_currency == "BRL"
            assert row.source == "bcb_ptax"

    def test_created_at_default(self):
        """created_at gets a default datetime."""
        with Session(self.engine) as session:
            row = ExchangeRateRow(
                rate_date=date(2026, 8, 20),
                rate=Decimal("5.25"),
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            assert row.created_at is not None
            assert isinstance(row.created_at, datetime)
